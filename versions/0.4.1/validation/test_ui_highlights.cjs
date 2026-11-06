#!/usr/bin/env node
/** Compare the real Scratch Pen extension's point/line emissions for UI washes. */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const H = require('../tools/vm_harness.cjs');

const [previousFile, currentFile, reportFile] = process.argv.slice(2);
if (!reportFile) throw new Error('Usage: node test_ui_highlights.cjs previous.sb3 current.sb3 report.json');
const WASH = 'UI wash x %s y %s width %s height %s tone %s';
const tones = {hover: [0xe3f4ff, .15], pressed: [0x7cb9ff, .45], selected: [0xa7cbff, .28]};
const neutral = [96, 96, 96];
const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const report = {previousFile, currentFile, previousSHA256: hash(previousFile), currentSHA256: hash(currentFile),
    method: 'Installed real Scratch interpreter and native Pen extension. The renderer captures emitted penPoint, penLine and penStamp calls. Interior color samples use source-over compositing over neutral RGB(96,96,96).', direct: [], foreground: []};

function near(actual, expected, margin = 1e-6) {
    assert.ok(Math.abs(actual - expected) <= margin, `Expected ${actual} to equal ${expected} ±${margin}`);
}

function channels(packed) { return [16, 8, 0].map(shift => packed >> shift & 255); }

async function scene(filename) {
    const vm = await H.loadProject(filename, {compiler: false});
    vm.setCompilerOptions({enabled: false});
    const sprite = vm.runtime.targets.find(t => t.getName() === 'Liquid Glass');
    const calls = [];
    function mark(kind, properties, x1, y1, x2, y2) {
        calls.push({kind, rgba: Array.from(properties.color4f), diameter: properties.diameter,
            x1, y1, x2, y2});
    }
    // Attach after loading. Sprite motion remains native, including the
    // onTargetMoved callback set by the real pen_down implementation.
    vm.runtime.renderer = {
        createPenSkin: () => 1, createDrawable: () => 2,
        updateDrawableSkinId() {}, draw() {},
        penPoint: (_skin, attrs, x, y) => mark('point', attrs, x, y, x, y),
        penLine: (_skin, attrs, x1, y1, x2, y2) => mark('line', attrs, x1, y1, x2, y2),
        penStamp: () => calls.push({kind: 'stamp', costume: sprite.sprite.costumes[sprite.currentCostume].name,
            x: sprite.x, y: sprite.y}),
    };
    const get = name => H.getVariable(vm, 'Liquid Glass', name).value;
    const set = (name, value) => { H.getVariable(vm, 'Liquid Glass', name).value = value; };
    const invoke = (name, ...args) => H.invoke(vm, 'Liquid Glass', name, args, {maxMilliseconds: 90000});
    function capture(name, ...args) {
        calls.length = 0;
        invoke(name, ...args);
        return calls.slice();
    }
    function configure(type, changes) {
        const proto = Object.values(sprite.blocks._blocks).find(b => b.opcode === 'procedures_prototype'
            && b.mutation.proccode.startsWith(type + ' %s '));
        assert.ok(proto, type);
        const names = JSON.parse(proto.mutation.argumentnames), defaults = JSON.parse(proto.mutation.argumentdefaults);
        invoke(proto.mutation.proccode, ...names.map((n, i) => changes[n] ?? defaults[i]));
    }
    return {vm, get, set, invoke, capture, configure};
}

function sample(calls, x, y) {
    let rgb = neutral.slice(), alpha = 0, coats = 0;
    for (const c of calls) {
        if (c.kind === 'stamp') continue;
        const dx = c.x2-c.x1, dy = c.y2-c.y1, length2 = dx*dx+dy*dy;
        const t = length2 ? Math.max(0, Math.min(1, ((x-c.x1)*dx+(y-c.y1)*dy)/length2)) : 0;
        const distance = Math.hypot(x-c.x1-t*dx,y-c.y1-t*dy);
        const coverage = Math.max(0, Math.min(1, c.diameter/2+.5-distance));
        const a = c.rgba[3]*coverage;
        if (a <= 0) continue;
        coats++;
        alpha = a+(1-a)*alpha;
        rgb = rgb.map((dst, i) => c.rgba[i]*255*a + dst*(1-a));
    }
    return {alpha, rgb, coats};
}

function toneAt(calls, x, y, tone) {
    const [color, alpha] = tones[tone], observation = sample(calls, x, y);
    near(observation.alpha, alpha);
    const desired = channels(color).map((src, i) => src*alpha+neutral[i]*(1-alpha));
    observation.rgb.forEach((actual, i) => near(actual, desired[i], .6));
    assert.equal(observation.coats, 1);
    return observation;
}

function cases(old, current) {
    const sizes = [[151,35], [178,30], [30,30], [29,96], [32.75,21.25], [16,15.75]];
    for (const [w, h] of sizes) for (const tone of Object.keys(tones)) {
        const x=11.25, y=-9.5;
        const oldCalls = old.capture(WASH,x,y,w,h,tone);
        const newCalls = current.capture(WASH,x,y,w,h,tone);
        const radius = Math.min(w,h)/2;
        const rx = w/2-radius, ry = h/2-radius;
        const points = [[x-rx,y-ry], [x,y], [x+rx,y+ry]];
        const oldSamples = points.map(([px,py]) => sample(oldCalls,px,py));
        const actual = points.map(([px,py]) => toneAt(newCalls,px,py,tone));
        const visibleCalls = newCalls.filter(c => c.kind !== 'stamp' && c.rgba[3] > 0);
        assert.equal(visibleCalls.length, 1);
        assert.equal(visibleCalls[0].kind, w === h ? 'point' : 'line');
        near(visibleCalls[0].diameter, 2*radius);
        for (const [px,py] of [[x-w/2-2,y], [x+w/2+2,y], [x,y-h/2-2], [x,y+h/2+2]]) {
            near(sample(newCalls,px,py).alpha,0);
        }
        if (w >= 2*h) {
            near(oldSamples[0].alpha, 1-(1-tones[tone][1])**2);
            near(oldSamples[1].alpha, tones[tone][1]);
            near(oldSamples[2].alpha, tones[tone][1]);
        }
        report.direct.push({w,h,tone, previousAlpha:oldSamples.map(s=>s.alpha),
            correctedAlpha:actual.map(s=>s.alpha), correctedRGB:actual[1].rgb.map(Math.round),
            visibleDraw:visibleCalls[0].kind});
    }
    for (const [w,h] of [[0,32],[32,0],[-1,24]]) {
        assert.equal(current.capture(WASH,0,0,w,h,'hover').length,0);
    }
}

function setupControls(s) {
    s.invoke('LG initialize'); s.set('UI view',1); s.invoke('UI begin');
    s.configure('Button',{id:2, x:-126, y:-25, label:'Run', width:116, height:36, shape:'capsule', join:0, quality:4});
    s.configure('Menu',{id:3,x:92,y:75,label:'Options',width:100,height:42,'panel width':164,
        'row height':34,items:'One|Two|Three',mode:'panel',drag:0,join:0,quality:4});
    s.invoke('LG advance'); s.invoke('UI settle');
}

function foreground(old,current) {
    setupControls(old); setupControls(current);
    function state(s, id, row, hover, pressed, selected) {
        s.set('UI hover id',hover ? id : 0); s.set('UI hover row',hover ? row : 0);
        s.set('UI pressed id',pressed ? id : 0); s.set('UI pressed row',pressed ? row : 0);
        s.get('UI selected path')[2] = selected ? 'Two' : '';
        return s.capture('UI foreground');
    }
    for (const [widget,tone,hover,pressed,selected] of [
        ['button','hover',1,0,0], ['button','pressed',1,1,0],
        ['row','selected',0,0,1], ['row','hover',1,0,1], ['row','pressed',1,1,1],
    ]) {
        const row=widget==='row' ? 2 : 0, id=row ? 3 : 2;
        const oldCalls=state(old,id,row,hover,pressed,selected);
        const newCalls=state(current,id,row,hover,pressed,selected);
        const cx=Number(current.get('x')[id-1]);
        const cy=Number(current.get('y')[id-1])+(row ? current.get('h')[id-1]/2-(row+.5)*34 : 0);
        const width=current.get('w')[id-1]-(row ? 10 : 7);
        const height=row ? 30 : current.get('h')[id-1]-7;
        const reach=(width-height)/2;
        const points=[[cx-reach,cy],[cx,cy],[cx+reach,cy]];
        const actual=points.map(([x,y])=>toneAt(newCalls,x,y,tone));
        if (row && selected) assert.ok(newCalls.some(c=>c.kind==='stamp' && c.costume==='UI icon check'),
            'Selected row should retain its separate checkmark');
        report.foreground.push({widget,tone,selected:Boolean(selected),
            previousAlpha:points.map(([x,y])=>sample(oldCalls,x,y).alpha),
            correctedAlpha:actual.map(s=>s.alpha), visibleCoats:actual.map(s=>s.coats)});
    }
}

(async()=>{
    const old=await scene(previousFile), current=await scene(currentFile);
    cases(old,current); foreground(old,current);
    assert.equal(hash(previousFile),report.previousSHA256); assert.equal(hash(currentFile),report.currentSHA256);
    old.vm.stopAll(); current.vm.stopAll(); report.passed=true;
})().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.mkdirSync(path.dirname(reportFile),{recursive:true});
    fs.writeFileSync(reportFile,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({passed:report.passed,direct:report.direct.length,
        foreground:report.foreground.length,error:report.error},null,2));
    process.exit(report.passed?0:1);
});
