#!/usr/bin/env node
/** Exercise Liquid Glass controls through the real VM mouse device and green-flag loop. */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const H = require('./vm_harness.cjs');
const {logicalGrid} = require('./test_grid_pixels.cjs');

const [projectFile, reportFile, componentFile] = process.argv.slice(2);
const importOnly = process.argv.includes('--import-only');
if (!projectFile || !reportFile) {
    throw new Error('Usage: node test_ui_components.cjs Studio.sb3 report.json [Component.sprite3] [--import-only]');
}
const digest = filename => crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
const report = {project: path.resolve(projectFile), sha256: digest(projectFile), checks: [], observations: {}};
const spriteName = 'Liquid Glass';

function closeTo(actual, expected, tolerance = 1e-6) {
    assert.ok(Number.isFinite(Number(actual)) && Math.abs(actual - expected) <= tolerance,
        `Expected ${actual} to be within ${tolerance} of ${expected}`);
}

function check(name, callback) {
    callback();
    report.checks.push({name, passed: true});
}

async function startScene(compiler, existingVM) {
    const vm = existingVM || await H.loadProject(projectFile, {compiler});
    vm.setCompilerOptions({enabled: compiler});
    const sprite = vm.runtime.targets.find(target => target.getName() === spriteName);
    assert.ok(sprite, 'Renderer sprite missing');
    const errors = [];
    vm.on('COMPILE_ERROR', (...args) => errors.push(args.map(String)));
    const clock = vm.runtime.ioDevices.clock._projectTimer;
    let milliseconds = 0;
    clock.nowObj = {now: () => milliseconds};
    clock.startTime = 0;
    function tick(count = 1) {
        for (let i = 0; i < count; i++) {
            milliseconds += 1000 / 30;
            vm.runtime._step();
        }
    }
    function mouse(x, y, isDown) {
        vm.postIOData('mouse', {x: x + 240, y: 180 - y,
            canvasWidth: 480, canvasHeight: 360, isDown});
    }
    function click(x, y) {
        mouse(x, y, true);
        tick(1);
        mouse(x, y, false);
        tick(2);
    }
    function value(name) { return H.getVariable(vm, spriteName, name).value; }
    function slot(name, id) { return value(name)[id - 1]; }
    function set(name, newValue) { H.getVariable(vm, spriteName, name).value = newValue; }
    function key(name) {
        vm.postIOData('keyboard', {key: name, isDown: true});
        vm.postIOData('keyboard', {key: name, isDown: false});
        tick(2);
    }
    function call(code, ...args) { return H.invoke(vm, spriteName, code, args, {maxMilliseconds: 90000}); }
    return {vm, sprite, errors, tick, mouse, click, value, slot, set, key, call};
}

function assertBackgroundSamples(scene) {
    const {value, set, call} = scene;
    for (const [mode, list] of [[1, 'Original RGB'], [2, 'Grid RGB']]) {
        set('Background', mode);
        const colors = list === 'Grid RGB' ? logicalGrid(value(list), () => value('LG grid rows'), () => value('LG grid pixels')) : value(list);
        assert.equal(colors.length, 480 * 360);
        for (const [x, y] of [[-400, 400], [400, -400], [16, 24], [-17, -11]]) {
            call('LG background %s %s', x, y);
            const sx = Math.min(239, Math.max(-240, x));
            const sy = Math.min(179, Math.max(-180, y));
            assert.equal(Number(value('color')), Number(colors[(179 - sy) * 480 + sx + 240]));
        }
    }
}

function renderedSize(scene, id) {
    return [scene.slot('w', id) * scene.slot('scaleX', id),
        scene.slot('h', id) * scene.slot('scaleY', id)];
}

function rowsFor(scene, menuId) {
    const ids = scene.value('UI row id');
    return ids.flatMap((id, i) => Number(id) === menuId ? [{
        index: Number(scene.value('UI row index')[i]),
        label: String(scene.value('UI row label')[i]),
        path: String(scene.value('UI row path')[i]),
        role: String(scene.value('UI row role')[i]),
    }] : []);
}

function menuPoint(scene, index) {
    const privatePanel = currentChild(scene);
    if (privatePanel) return [privatePanel.x, privatePanel.y+privatePanel.h/2-(index+.5)*privatePanel.pitch];
    const rowHeight = Number(scene.slot('UI row height',3))*Number(scene.slot('h',3))/Number(scene.slot('UI expanded height',3));
    const centerX = Number(scene.slot('x', 3));
    const localY = scene.slot('h', 3) / 2 - rowHeight * (index + .5);
    return [centerX, scene.slot('y', 3) + localY * scene.slot('scaleY', 3)];
}

function currentChild(scene) {
    if (!Object.values(scene.sprite.variables).some(value => value.name === 'UI layer owner')) return null;
    const page = String(scene.slot('UI page',3));
    if (!page) return null;
    const i = scene.value('UI layer owner').findIndex((id,i) => Number(id)===3 && scene.value('UI layer path')[i]===page);
    if (i<0) return null;
    const v = name => Number(scene.value('UI layer '+name)[i]);
    return {x:v('x'),y:v('y'),h:v('h'),pitch:v('h')/(v('rows')+1),p:v('p')};
}

function rowByPath(scene, path) {
    const rows = rowsFor(scene, 3);
    const row = rows.find(item => item.path === path);
    assert.ok(row, `Missing menu row ${path}: ${JSON.stringify(rows)}`);
    return row;
}

function tickUntil(scene, predicate, description, maxTicks = 300) {
    const start = Date.now();
    for (let i = 0; i < maxTicks; i++) {
        if (predicate()) return;
        if (Date.now() - start > 90000) break;
        scene.tick();
    }
    assert.ok(predicate(), `Timed out waiting for ${description}`);
}

async function testStudioControls() {
    const scene = await startScene(true);
    const {vm, tick, mouse, click, value, slot} = scene;
    const actions = () => Number(value('UI event number'));
    mouse(214, -153, false);
    vm.greenFlag();
    tick(4);
    check('The default Studio scene creates a sidebar, fixed button and compact menu', () => {
        assert.deepEqual(value('active').slice(0, 3).map(Number), [1, 1, 1]);
        for (const [id, x, y, w, h] of [[1,-169,0,112,286], [2,67,-96,158,42], [3,60,102,34,34]]) {
            closeTo(slot('x', id), x); closeTo(slot('y', id), y);
            closeTo(slot('w', id), w); closeTo(slot('h', id), h);
        }
        assert.equal(Number(slot('UI open', 3)), 0);
    });

    check('The sidebar stays fixed and produces no hover, press, drag, or action', () => {
        const before = actions();
        mouse(-169, 0, false); tick(2);
        assert.notEqual(Number(value('UI hover id')), 1);
        mouse(-169, 0, true); tick(2);
        assert.notEqual(Number(value('UI pressed id')), 1);
        mouse(-131, 27, true); tick(3);
        mouse(-131, 27, false); tick(2);
        assert.equal(actions(), before);
        closeTo(slot('x', 1), -169); closeTo(slot('y', 1), 0);
        closeTo(slot('scaleX', 1), 1); closeTo(slot('scaleY', 1), 1);
    });

    check('Button hover expands around its anchor, a horizontal pull deforms it, and releasing the drag cancels activation', () => {
        const before = actions();
        const baseWidth = renderedSize(scene, 2)[0];
        mouse(67, -96, false); tick(8);
        assert.equal(Number(value('UI hover id')), 2);
        assert.ok(renderedSize(scene, 2)[0] > baseWidth, 'Expected a larger rendered hover contour');
        mouse(67, -96, true); tick(2);
        assert.equal(Number(value('UI pressed id')), 2);
        mouse(100, -96, true); tick(8);
        assert.ok(slot('x', 2) > 67 && slot('x', 2) < 100, 'Button should follow only a bounded part of the pull'); closeTo(slot('y', 2), -96);
        assert.ok(slot('scaleX', 2) > 1.01);
        assert.ok(slot('scaleY', 2) < 1);
        assert.equal(actions(), before);
        mouse(100, -96, false); tick(3);
        assert.equal(actions(), before, 'A dragged button activated on release');
        mouse(215, -150, false); tick(55);
        closeTo(slot('scaleX', 2), 1, .01); closeTo(slot('scaleY', 2), 1, .01);
        closeTo(slot('x', 2), 67); closeTo(slot('y', 2), -96);
    });

    check('Each complete button click fires once and switches between both optical backgrounds', () => {
        const before = actions(), bg = Number(value('Background'));
        mouse(67, -96, true); tick(7);
        assert.equal(actions(), before, 'Mouse-down repeated an activation');
        mouse(67, -96, false); tick(2);
        assert.equal(actions(), before + 1);
        assert.equal(Number(value('UI source')), 2);
        assert.equal(value('UI action'), 'Switch background');
        assert.equal(Number(value('Background')), 3 - bg);
        click(67, -96);
        assert.equal(actions(), before + 2);
        assert.equal(Number(value('Background')), bg);
    });

    check('The launcher animates into a vertical list with two separate hit rows', () => {
        click(60, 102);
        assert.equal(Number(slot('UI open', 3)), 1);
        const earlyHeight = Number(slot('h', 3));
        assert.ok(earlyHeight < 102, `Expected an intermediate height, received ${earlyHeight}`);
        tick(60);
        closeTo(slot('w', 3), 188, .1);
        const first = rowByPath(scene, 'Background');
        const second = rowByPath(scene, 'Detail');
        assert.equal(second.index, first.index + 1);
        const a = menuPoint(scene, first.index), b = menuPoint(scene, second.index);
        closeTo(a[0], b[0]); closeTo(a[1] - b[1], 34, .1);
        for (const [row, point] of [[first, a], [second, b]]) {
            mouse(...point, false); tick(2);
            assert.equal(Number(value('UI hover id')), 3);
            assert.equal(Number(value('UI hover row')), row.index);
        }
        report.observations.openMenu = {earlyHeight, settledHeight: slot('h', 3), rows: [first, second]};
    });

    check('A nested leaf changes the background and emits its full path once', () => {
        const before = actions();
        click(...menuPoint(scene, rowByPath(scene, 'Background').index)); tick(45);
        assert.equal(Number(slot('UI open', 3)), 1);
        const leaf = rowByPath(scene, 'Background>Grid');
        assert.equal(leaf.label, 'Grid');
        click(...menuPoint(scene, leaf.index)); tick(4);
        assert.equal(actions(), before + 1);
        assert.equal(Number(value('UI source')), 3);
        assert.equal(value('UI path'), 'Background>Grid');
        assert.equal(Number(value('Background')), 2);
        assert.equal(Number(slot('UI open', 3)), 0);
    });

    check('An outside press dismisses the reopened menu without choosing another action', () => {
        tick(45); click(60, 102); tick(45);
        assert.equal(Number(slot('UI open', 3)), 1);
        const before = actions();
        click(215, -150);
        assert.equal(Number(slot('UI open', 3)), 0);
        assert.equal(actions(), before);
    });

    if (Object.values(scene.sprite.variables).some(variable => variable.name === 'Menu finish')) {
        check('The Menu finish submenu changes the material actually registered on the same menu slot', () => {
            const output=[];
            for (const [name,color,transparency,brightness,blur] of [
                ['Smoked','#292A32',46,-12,12], ['Clear','#FFFFFF',100,0,0], ['Frosted','#414B59',66,4,6],
            ]) {
                tick(40); click(60,102); tick(40);
                click(...menuPoint(scene,rowByPath(scene,'Menu finish').index)); tick(40);
                const before=actions(), path='Menu finish>'+name;
                click(...menuPoint(scene,rowByPath(scene,path).index)); tick(4);
                assert.equal(actions(),before+1); assert.equal(value('UI path'),path);
                assert.equal(value('Menu finish'),name); assert.equal(value('Menu color'),color);
                assert.equal(slot('matToken',3),'@'+color);
                closeTo(slot('matAlpha',3),1-transparency/100);
                closeTo(slot('matBrightness',3),brightness/100); closeTo(slot('matBlur',3),blur);
                output.push({name,color,transparency,brightness,blur});
            }
            report.observations.menuFinishes=output;
        });
    }

    check('Dragging the launcher follows the pointer and returns to its configured anchor without selecting', () => {
        tick(50);
        const before = actions(), anchor = [60,102];
        mouse(...anchor, true); tick(2);
        mouse(92,87,true); tick(10);
        const pulled = [slot('x',3),slot('y',3)];
        assert.ok(pulled[0]>60 && pulled[0]<92 && pulled[1]<102 && pulled[1]>87);
        mouse(92,87,false); tick(45);
        assert.equal(actions(), before); assert.equal(Number(slot('UI open',3)),0);
        closeTo(slot('x',3),anchor[0]); closeTo(slot('y',3),anchor[1]);
        click(...anchor); tick(45);
        assert.equal(Number(slot('UI open',3)),1);
        closeTo(slot('x',3),anchor[0],.2);
        closeTo(slot('y',3)+slot('h',3)/2,anchor[1]+Number(slot('UI resting height',3))/2,.2);
        report.observations.menuAnchor = {anchor,pulled};
    });

    check('Both optical backgrounds use their stored pixels at interior and clipped edge samples',
        () => assertBackgroundSamples(scene));
    assert.deepEqual(scene.errors, []);
    vm.stopAll();
}

async function testBusyFrameClick() {
    // Instrument the native interpreter's presentation itself. Deliver both
    // mouse events inside a strip stamp, before the next UI polling turn.
    const scene = await startScene(false);
    const {vm, sprite, tick, mouse, value, slot} = scene;
    const runtime = vm.runtime;
    const trace = new Map();
    let ordinal = 0, sent = false, clicksBefore = 0, stageClickHats = 0;
    const startHats = runtime.startHats.bind(runtime);
    runtime.startHats = (...args) => {
        if (args[0] === 'event_whenstageclicked') stageClickHats++;
        return startHats(...args);
    };
    function frame() {
        const number = Number(value('Frames'));
        if (!trace.has(number)) trace.set(number, {lastStroke: 0, lastBackground: 0, firstLabel: null, labels: []});
        return trace.get(number);
    }
    const penDown = runtime._primitives.pen_penDown;
    runtime._primitives.pen_penDown = (args, util) => {
        const name = sprite.sprite.costumes[sprite.currentCostume]?.name || '';
        if (name.startsWith('LG strip ')) frame().lastStroke = ++ordinal;
        return penDown(args, util);
    };
    const stamp = runtime._primitives.pen_stamp;
    runtime._primitives.pen_stamp = (args, util) => {
        const result = stamp(args, util);
        const costume = sprite.sprite.costumes[sprite.currentCostume]?.name || '';
        const group = frame();
        ordinal++;
        if (costume.startsWith('LG strip ')) {
            group.lastBackground = ordinal;
            if (!sent) {
                sent = true;
                clicksBefore = Number(value('UI event number'));
                const x = Number(slot('x', 2)), y = Number(slot('y', 2));
                mouse(x, y, true);
                mouse(x, y, false);
                assert.equal(runtime.ioDevices.mouse.getIsDown(), false);
                report.observations.busyClick = {frame: Number(value('Frames')), costume, x, y};
            }
        } else if (costume.startsWith('UI glyph ') || costume.startsWith('UI icon ')) {
            if (group.firstLabel === null) group.firstLabel = ordinal;
            group.labels.push({costume, x: sprite.x, y: sprite.y});
        }
        return result;
    };
    mouse(215, -152, false);
    vm.greenFlag();
    tick();
    tickUntil(scene, () => sent && Number(value('UI event number')) > clicksBefore,
        'a short click delivered during native Pen presentation', 800);
    check('A stage mouse-down and release wholly inside a native strip stamp activates the button once', () => {
        assert.equal(stageClickHats, 1);
        assert.equal(Number(value('UI event number')), clicksBefore + 1);
        assert.equal(Number(value('UI source')), 2);
        assert.equal(value('UI action'), 'Switch background');
        assert.equal(runtime.ioDevices.mouse.getIsDown(), false);
    });
    tickUntil(scene, () => Array.from(trace.values()).some(group => group.firstLabel !== null),
        'the native UI glyph/icon overlay', 800);
    check('Native labels and icons stamp above the glass strokes and restored backdrop', () => {
        const groups = Array.from(trace.values()).filter(group => group.firstLabel !== null);
        assert.ok(groups.length);
        for (const group of groups) {
            assert.ok(group.firstLabel > group.lastStroke, 'A glass stroke covered a label');
            assert.ok(group.firstLabel > group.lastBackground, 'A background strip covered a label');
        }
        const labels = groups.flatMap(group => group.labels);
        assert.ok(labels.some(item => item.costume.startsWith('UI glyph ')));
        assert.ok(labels.some(item => item.costume.startsWith('UI icon ')));
        report.observations.foregroundStamps = labels.length;
    });
    assert.deepEqual(scene.errors, []);
    vm.stopAll();
}

function configure(scene, title, overrides) {
    const proto = Object.values(scene.sprite.blocks._blocks).find(block =>
        block.opcode === 'procedures_prototype' && block.mutation.proccode.startsWith(title + ' %s '));
    assert.ok(proto, `Public ${title} definition missing`);
    const names = JSON.parse(proto.mutation.argumentnames);
    const values = JSON.parse(proto.mutation.argumentdefaults);
    for (const key of Object.keys(overrides)) assert.ok(names.includes(key), `Unknown ${title} input ${key}`);
    scene.call(proto.mutation.proccode, ...names.map((name, i) => overrides[name] ?? values[i]));
}

async function testPublicControls() {
    const scene = await startScene(false);
    const {vm, sprite, call, slot, set} = scene;
    call('LG initialize');
    set('UI view', 1);
    call('UI begin');
    check('Public Button inputs independently configure a circle, capsule, and rounded rectangle', () => {
        configure(scene, 'Button', {id: 1, x: -64, y: 0, label: '+', shape: 'auto', width: 0, height: 30,
            radius: 7, join: 0, quality: 4});
        configure(scene, 'Button', {id: 2, x: 0, y: 0, label: 'Play', shape: 'auto', width: 54, height: 24,
            radius: 7, join: 0, quality: 4});
        configure(scene, 'Button', {id: 3, x: 70, y: 0, label: 'MiXeD Case label with overflow', shape: 'auto',
            width: 68, height: 28, radius: 7, join: 0, quality: 4});
        for (const [id,w,h,r] of [[1,30,30,15], [2,54,24,12], [3,68,28,7]]) {
            closeTo(slot('w', id), w); closeTo(slot('h', id), h); closeTo(slot('r', id), r);
        }
        call('LG advance');
        call('UI settle');
    });

    const stamps = [];
    const original = vm.runtime._primitives.pen_stamp;
    vm.runtime._primitives.pen_stamp = (args, util) => {
        stamps.push({costume: sprite.sprite.costumes[sprite.currentCostume].name, x: sprite.x, y: sprite.y});
        return original(args, util);
    };
    check('A clipped custom label preserves letter case and stays inside its own button', () => {
        call('LG render');
        const third = stamps.filter(s => s.costume.startsWith('UI glyph ') && s.x >= 36);
        const letters = third.map(s => s.costume.slice('UI glyph ['.length, -1)).join('');
        assert.ok(letters.startsWith('MiX'), `Mixed-case glyph sequence was ${letters}`);
        assert.ok(letters.endsWith('…'), `Overflowing label lacked an ellipsis: ${letters}`);
        assert.ok(third.every(s => s.x >= 36 && s.x < 104 && Math.abs(s.y) < .001));
        report.observations.clippedLabel = letters;
    });
    check('An identical prepared frame retains the existing UI art without stamping again', () => {
        const count = stamps.length;
        call('LG render');
        assert.equal(stamps.length, count);
    });
    assert.deepEqual(scene.errors, []);
    vm.stopAll();
}

function actionObserver(costume, broadcastId) {
    const observer = {name: 'Action observer', isStage: false, variables: {}, lists: {}, broadcasts: {},
        blocks: {}, comments: {}, costumes: [costume], sounds: [], currentCostume: 0, layerOrder: 1,
        visible: false, x: 0, y: 0, size: 100, direction: 90, draggable: false, rotationStyle: 'all around'};
    const blocks = observer.blocks;
    function block(opcode, parent, next, inputs = {}, fields = {}) {
        return {opcode, parent, next, inputs, fields, topLevel: false, shadow: false};
    }
    observer.variables.received = ['received', 0];
    blocks.receiptHat = {...block('event_whenbroadcastreceived', null, 'count', {},
        {BROADCAST_OPTION: ['UI activated', broadcastId]}), topLevel: true, x: 40, y: 40};
    blocks.count = block('data_changevariableby', 'receiptHat', 'read0',
        {VALUE: [1, [4, '1']]}, {VARIABLE: ['received', 'received']});
    const fields = ['UI action', 'UI path', 'UI source'];
    for (const [i, name] of fields.entries()) {
        const id = `seen${i}`;
        observer.variables[id] = [name, ''];
        blocks[`read${i}`] = block('data_setvariableto', i ? `read${i-1}` : 'count',
            i + 1 < fields.length ? `read${i+1}` : null,
            {VALUE: [2, `sense${i}`]}, {VARIABLE: [name, id]});
        blocks[`sense${i}`] = block('sensing_of', `read${i}`, null,
            {OBJECT: [1, `object${i}`]}, {PROPERTY: [name, null]});
        blocks[`object${i}`] = {...block('sensing_of_object_menu', `sense${i}`, null, {},
            {OBJECT: [spriteName, null]}), shadow: true};
    }
    return observer;
}

async function testSpriteImport(compiler) {
    const {VM, Storage, JSZip} = H.libraries();
    const zip = await JSZip.loadAsync(fs.readFileSync(projectFile));
    const project = JSON.parse(await zip.file('project.json').async('string'));
    const stage = project.targets.find(target => target.isStage);
    const receiverId = 'hostUIActivationReceiver';
    Object.assign(stage, {blocks: {}, comments: {}, variables: {}, lists: {},
        broadcasts: {[receiverId]: 'UI activated'}});
    project.targets = [stage, actionObserver(stage.costumes[0], receiverId)];
    project.monitors = [];
    const host = new JSZip();
    host.file('project.json', JSON.stringify(project));
    for (const asset of [...stage.costumes, ...stage.sounds]) {
        host.file(asset.md5ext, await zip.file(asset.md5ext).async('nodebuffer'));
    }
    const vm = new VM();
    vm.attachStorage(new Storage());
    await vm.loadProject(await host.generateAsync({type: 'nodebuffer'}));
    report.componentSHA256 = digest(componentFile);
    await vm.addSprite(fs.readFileSync(componentFile));
    const scene = await startScene(compiler, vm);
    const received = name => H.getVariable(vm, 'Action observer', name).value;
    const mode = compiler ? 'compiler' : 'interpreter';
    function heldClick(x, y, targetId) {
        scene.mouse(x, y, true);
        tickUntil(scene, () => Number(scene.value('UI pressed id')) === targetId, 'pressed component');
        scene.tick(2);
        scene.mouse(x, y, false);
        tickUntil(scene, () => Number(scene.value('UI pressed id')) === 0, 'released component');
    }
    scene.mouse(215, -151, false);
    vm.greenFlag(); scene.tick();
    tickUntil(scene, () => Number(scene.value('Frames')) >= 1, 'first complete host frame');
    check(`A native sprite import delivers Button and nested Menu broadcasts to another sprite (${mode})`, () => {
        assert.deepEqual(scene.value('UI kind').slice(0, 3), ['Background', 'Button', 'Menu']);
        const before = Number(scene.value('UI event number'));
        heldClick(67, -96, 2);
        assert.equal(Number(scene.value('UI event number')), before + 1);
        assert.equal(scene.value('UI action'), 'Switch background');
        tickUntil(scene, () => Number(received('received')) === 1, 'first actual broadcast handler');
        assert.equal(received('UI action'), 'Switch background');
        assert.equal(received('UI path'), '');
        assert.equal(Number(received('UI source')), 2);
        heldClick(60, 102, 3);
        tickUntil(scene, () => rowsFor(scene, 3).some(row => row.path === 'Detail') && scene.slot('h', 3) > 96,
            'visible expanded root rows');
        heldClick(...menuPoint(scene, rowByPath(scene, 'Detail').index), 3);
        tickUntil(scene, () => rowsFor(scene, 3).some(row => row.path === 'Detail>Balanced') &&
            (currentChild(scene) ? currentChild(scene).p>.97 : scene.slot('h', 3) > 131),
            'visible secondary rows');
        assert.equal(Number(received('received')), 1, 'Menu navigation emitted a leaf action');
        heldClick(...menuPoint(scene, rowByPath(scene, 'Detail>Balanced').index), 3);
        assert.equal(Number(scene.value('UI event number')), before + 2);
        assert.equal(scene.value('UI path'), 'Detail>Balanced');
        assert.equal(Number(scene.slot('UI open', 3)), 0);
        tickUntil(scene, () => Number(received('received')) === 2, 'second actual broadcast handler');
        assert.equal(received('UI action'), 'Detail>Balanced');
        assert.equal(received('UI path'), 'Detail>Balanced');
        assert.equal(Number(received('UI source')), 3);
        assert.deepEqual(vm.runtime.getTargetForStage().blocks._scripts, []);
        report.observations[`import_${mode}`] = {stageScripts: 0, received: Number(received('received')),
            action: received('UI action'), path: received('UI path'), source: Number(received('UI source'))};
    });
    assert.equal(digest(componentFile), report.componentSHA256);
    assert.deepEqual(scene.errors, []);
    vm.stopAll();
}

async function main() {
    if (!importOnly) {
        await testStudioControls();
        await testPublicControls();
        await testBusyFrameClick();
    }
    if (importOnly) assert.ok(componentFile, 'An import-only check requires an explicit sprite3');
    if (componentFile) {
        await testSpriteImport(true);
        await testSpriteImport(false);
    }
    assert.equal(digest(projectFile), report.sha256);
    report.passed = true;
}

main().catch(error => { report.passed = false; report.error = String(error.stack || error); })
    .finally(() => {
        fs.mkdirSync(path.dirname(reportFile), {recursive: true});
        fs.writeFileSync(reportFile, JSON.stringify(report, null, 2) + '\n');
        console.log(JSON.stringify(report, null, 2));
        process.exit(report.passed ? 0 : 1);
    });

