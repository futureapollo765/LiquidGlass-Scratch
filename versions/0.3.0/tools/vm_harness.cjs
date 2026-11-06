#!/usr/bin/env node
/** Real TurboWarp VM harness. Reads the already-installed signed app bundle;
 * it never controls the desktop app and never replaces actual visual QA.
 * Only the webpack entry is replaced to expose bundled library exports. */
const fs = require('node:fs');
const path = require('node:path');
const nodeVM = require('node:vm');
let bundled;

function readAsarFile(archive, entry) {
  const fd = fs.openSync(archive, 'r');
  try {
    const header = Buffer.alloc(16);
    fs.readSync(fd, header, 0, 16, 0);
    const offset = 8 + header.readUInt32LE(4);
    const json = Buffer.alloc(header.readUInt32LE(12));
    fs.readSync(fd, json, 0, json.length, 16);
    let info = JSON.parse(json.toString());
    for (const part of entry.split('/')) info = info.files[part];
    if (info.unpacked) return fs.readFileSync(archive + '.unpacked/' + entry);
    const result = Buffer.alloc(info.size);
    fs.readSync(fd, result, 0, result.length, offset + Number(info.offset));
    return result;
  } finally { fs.closeSync(fd); }
}

function libraries() {
  if (bundled) return bundled;
  const archive = process.env.TURBOWARP_ASAR || '/Applications/TurboWarp.app/Contents/Resources/app.asar';
  const standalone = readAsarFile(archive, 'src-renderer/packager/standalone.html').toString();
  const match = standalone.match(/<script type="p4-standalone-asset" data-name="scaffolding\/scaffolding-full.js">([\s\S]*?)<\/script>/);
  if (!match) throw new Error('Installed TurboWarp does not include expected standalone scaffold.');
  let source = match[1];
  const entry = 'r(r.s=303)';
  if (!source.includes(entry)) throw new Error('TurboWarp webpack layout changed; inspect before updating harness.');
  source = source.replace(entry, 'globalThis.__liquidGlassTwRequire=r');
  global.window = global;
  global.self = global;
  if (!global.navigator) global.navigator = {userAgent: 'Node', platform: 'MacIntel'};
  global.document = global.document || {};
  nodeVM.runInThisContext(source, {filename: 'installed-turbowarp-libraries.js'});
  const req = global.__liquidGlassTwRequire;
  bundled = {VM: req(55), Storage: req(91), JSZip: req(23), require: req};
  return bundled;
}

async function loadProject(filename, {compiler = false} = {}) {
  const {VM, Storage} = libraries();
  const vm = new VM();
  vm.attachStorage(new Storage());
  vm.setCompilerOptions({enabled: compiler});
  // No renderer or audio device is attached: native VM executes only the logic.
  await vm.loadProject(fs.readFileSync(filename));
  return vm;
}

function snapshot(vm) {
  return vm.runtime.targets.filter(t => t.isOriginal).map(target => ({
    name: target.getName(),
    variables: Object.fromEntries(Object.values(target.variables).filter(v => v.type !== 'list').map(v => [v.name, v.value])),
    lists: Object.fromEntries(Object.values(target.variables).filter(v => v.type === 'list').map(v => [v.name, v.value])),
  }));
}

function getVariable(vm, spriteName, variableName) {
  const target = vm.runtime.targets.find(t => t.isOriginal && t.getName() === spriteName);
  if (!target) throw new Error(`Missing sprite: ${spriteName}`);
  const variable = Object.values(target.variables).find(v => v.name === variableName);
  if (!variable) throw new Error(`Missing variable: ${spriteName}/${variableName}`);
  return variable;
}

function stepFrames(vm, count, {maxMilliseconds = 10000} = {}) {
  const start = Date.now();
  for (let i = 0; i < count; i++) {
    if (Date.now() - start > maxMilliseconds) throw new Error(`VM exceeded ${maxMilliseconds}ms at frame ${i}`);
    vm.runtime._step();
  }
  return snapshot(vm);
}

let invocationId = 0;
function invoke(vm, spriteName, proccode, args = [], {maxMilliseconds = 10000} = {}) {
  vm.stopAll();
  const target = vm.runtime.targets.find(t => t.isOriginal && t.getName() === spriteName);
  if (!target) throw new Error(`Missing sprite: ${spriteName}`);
  const proto = Object.values(target.blocks._blocks).find(b => b.opcode === 'procedures_prototype' && b.mutation.proccode === proccode);
  if (!proto) throw new Error(`Missing procedure: ${spriteName}/${proccode}`);
  const argIds = JSON.parse(proto.mutation.argumentids);
  if (args.length !== argIds.length) throw new Error(`Expected ${argIds.length} procedure args, got ${args.length}`);
  const ident = `harness-call-${++invocationId}`;
  const inputs = {};
  const created = [];
  for (let i = 0; i < args.length; i++) {
    const inputId = `${ident}-arg-${i}`;
    target.blocks.createBlock({id: inputId, opcode: 'text', next: null, parent: ident, inputs: {}, fields: {TEXT: {name: 'TEXT', value: String(args[i])}}, shadow: true, topLevel: false});
    inputs[argIds[i]] = {name: argIds[i], block: inputId, shadow: inputId};
    created.push(inputId);
  }
  const mutation = {...proto.mutation};
  delete mutation.argumentnames;
  delete mutation.argumentdefaults;
  target.blocks.createBlock({id: ident, opcode: 'procedures_call', next: null, parent: null, inputs, fields: {}, mutation, shadow: false, topLevel: true});
  const thread = vm.runtime._pushThread(ident, target, {stackClick: true});
  const start = Date.now();
  let frames = 0;
  while (vm.runtime.threads.includes(thread) && thread.status !== 4) {
    if (Date.now() - start > maxMilliseconds) {
      vm.stopAll();
      throw new Error(`Procedure ${proccode} exceeded ${maxMilliseconds}ms after ${frames} steps`);
    }
    vm.runtime._step();
    frames++;
  }
  target.blocks.deleteBlock(ident);
  for (const id of created) target.blocks.deleteBlock(id);
  return {frames, elapsedMs: Date.now() - start};
}

module.exports = {libraries, loadProject, snapshot, getVariable, stepFrames, invoke};

if (require.main === module) {
  (async () => {
    const filename = process.argv[2];
    if (!filename) throw new Error('Usage: node tools/vm_harness.cjs project.sb3 [frames]');
    const vm = await loadProject(filename);
    const known = vm.runtime._primitives;
    const unknown = [];
    for (const target of vm.runtime.targets) {
      for (const b of Object.values(target.blocks._blocks)) {
        if (!known[b.opcode] && !vm.runtime._hats[b.opcode] && !['procedures_prototype','text','math_number','math_integer','math_whole_number','math_positive_number','math_angle','colour_picker','event_broadcast_menu','sensing_keyoptions','looks_costume','looks_backdrops','motion_goto_menu','motion_glideto_menu','motion_pointtowards_menu','control_create_clone_of_menu','pen_menu_colorParam','sensing_touchingobjectmenu','sensing_distancetomenu','sensing_of_object_menu','sound_sounds_menu','sensing_currentmenu'].includes(b.opcode)) unknown.push(`${target.getName()}: ${b.opcode}`);
      }
    }
    const frames = Number(process.argv[3] || 0);
    if (frames) { vm.greenFlag(); stepFrames(vm, frames, {maxMilliseconds: 30000}); }
    const state = snapshot(vm).map(t => ({...t, lists: Object.fromEntries(Object.entries(t.lists).map(([k,v]) => [k, {length:v.length, first:v.slice(0,5)}]))}));
    console.log(JSON.stringify({project: path.resolve(filename), loaded: true, frames, unknownOpcodes:[...new Set(unknown)], state}, null, 2));
    vm.stopAll();
    process.exit(unknown.length ? 1 : 0);
  })().catch(error => { console.error(String(error)); process.exit(1); });
}
