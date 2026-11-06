#!/usr/bin/env node
/** Compare the real Scratch Pen extension's point/line emissions for UI washes. */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const H = require('./vm_harness.cjs');

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
            x1, y1, x2, y2, costume:sprite.sprite.costumes[sprite.currentCostume]?.name});
    }
    // Attach after loading. Sprite motion remains native, including the
    // onTargetMoved callback set by the real pen_down implementation.
    vm.runtime.renderer = {
        createPenSkin: () => 1, createDrawable: () => 2,
        updateDrawableSkinId() {}, draw() {},
        penPoint: (_skin, attrs, x, y) => mark('point', attrs, x, y, x, y),
        penLine: (_skin, attrs, x1, y1, x2, y2) => mark('line', attrs, x1, y1, x2, y2),
        penStamp: () => {
            const [x,y]=H.inkStampCenter(sprite);
            calls.push({kind: 'stamp', costume: sprite.sprite.costumes[sprite.currentCostume].name,
                x,y, size:sprite.size, opacity:1-(Number(sprite.effects.ghost)||0)/100,
                source:sprite.sprite.costumes[Number(Object.values(sprite.variables).find(v=>v.name==='UI path index')?.value)-1]?.name});
        },
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
    const has = name => Object.values(sprite.variables).some(variable => variable.name === name);
    return {vm, get, set, invoke, capture, configure, has};
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
    const button={id:2, x:-126, y:-25, label:'Run', width:116, height:36, shape:'capsule', join:0, quality:4};
    const menu={id:3,x:92,y:75,label:'Options',width:100,height:42,'panel width':164,
        'row height':34,items:'One|Two|Three',mode:'panel',drag:0,join:0,quality:4};
    for(let i=0;i<90;i++) {
        s.invoke('UI begin'); s.configure('Button',button); s.configure('Menu',menu);
        s.invoke('LG advance'); s.invoke('UI settle');
        if(!s.has('UI menu open fade') || Number(s.get('UI menu open fade')[2])>=1) break;
    }
}

function highlightMarks(calls) {
    // Lettering is sometimes drawn using native Pen lines, including in the same
    // row as the wash. Measure the actual coat colors independently of that ink.
    return calls.filter(c=>c.kind!=='stamp' && Object.values(tones).some(([rgb])=>
        channels(rgb).every((v,i)=>Math.abs(c.rgba[i]*255-v)<1.6)));
}

function verifyCheckmark(s,calls,id,row) {
    const slot=(key)=>Number(s.get(key)[id-1]);
    const w=slot('w')*slot('scaleX'), h=slot('h')*slot('scaleY'), pitch=slot('UI row height');
    const sx=s.has('UI expanded width') ? w/slot('UI expanded width') : 1;
    const sy=s.has('UI expanded height') ? h/slot('UI expanded height') : 1;
    const x=slot('x')+w/2-16*sx, y=slot('y')+h/2-(row+.5)*pitch*sy;
    const stamps=calls.filter(c=>c.kind==='stamp' && c.costume==='UI icon check');
    if(stamps.length) {
        assert.equal(stamps.length,1);
        near(stamps[0].x,x,.07);near(stamps[0].y,y,.07);near(stamps[0].opacity,1,.002);
        near(stamps[0].size,50*(sx+sy),.1);
        return {method:'SVG stamp',x,y,sx,sy};
    }
    const samples=calls.filter(c=>c.kind==='stamp'&&c.costume?.startsWith('UI ink sample ')&&
        c.source==='UI icon check'&&Number(c.costume.split('/').at(-1))>=16&&c.opacity>.12);
    if(samples.length){
        const joints=[[-6,-.3],[-2,-4.1],[6,4.1]];
        for(const [lx,ly] of joints)assert.ok(samples.some(p=>Math.hypot(p.x-x-sx*lx,p.y-y-sy*ly)<1.2),
            'Expected native checkmark mask coverage at both ends and the bend');
        return {method:'affine mask',x,y,sx,sy,pixels:samples.length};
    }
    // At slightly different horizontal/vertical scales the original icon is
    // painted from its two bright source segments instead of a uniform stamp.
    const segments=calls.filter(c=>c.kind==='line' && c.costume==='UI icon check'
        && c.rgba[0]>.9 && c.rgba[3]>.01 && Math.hypot(c.x2-c.x1,c.y2-c.y1)>.01);
    assert.equal(segments.length,2,'Expected the two native bright strokes of the selected row checkmark');
    const vertices=[[-6,-.3],[-2,-4.1],[6,4.1]];
    for(let i=0;i<2;i++) {
        const c=segments[i], a=vertices[i], b=vertices[i+1];
        near(c.x1,x+sx*a[0],.065);near(c.y1,y+sy*a[1],.065);
        near(c.x2,x+sx*b[0],.065);near(c.y2,y+sy*b[1],.065);near(c.rgba[3],1,.002);
    }
    return {method:'affine Pen strokes',x,y,sx,sy,segments:segments.map(c=>[c.x1,c.y1,c.x2,c.y2])};
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
        const marks=highlightMarks(newCalls);
        const actual=points.map(([x,y])=>row ? toneAt(marks,x,y,tone) : sample(marks,x,y));
        if(!row) {
            assert.ok(marks.every(c=>c.rgba[3]===0),'A Button should never paint a visible inner highlight');
            assert.ok(actual.every(p=>p.coats===0),'Button surface must have zero interactive coats');
        }
        const checkmark=row&&selected ? verifyCheckmark(current,newCalls,id,row) : null;
        report.foreground.push({widget,tone,selected:Boolean(selected),
            previousAlpha:points.map(([x,y])=>sample(highlightMarks(oldCalls),x,y).alpha),checkmark,
            correctedAlpha:actual.map(s=>s.alpha), visibleCoats:actual.map(s=>s.coats)});
    }
    // Compare the visible ends of the real Pen stroke with the layout of
    // the header, a middle row and the last row at two different face scales.
    report.rowInsets=[];
    current.set('UI pressed id',0); current.set('UI hover id',3);
    current.get('UI selected path')[2]='';
    const slot=k=>Number(current.get(k)[2]);
    for(const [stretchX,stretchY] of [[1,1],[1.16,.91]]) {
        current.get('scaleX')[2]=stretchX; current.get('scaleY')[2]=stretchY;
        const w=slot('w')*stretchX, h=slot('h')*stretchY;
        const sx=w/slot('UI expanded width'), sy=h/slot('UI expanded height');
        const pitch=slot('UI row height')*sy;
        for(const row of [0,2,3]) {
            current.set('UI hover row',row);
            const strokes=highlightMarks(current.capture('UI foreground')).filter(c=>c.rgba[3]>.001);
            assert.equal(strokes.length,1,'A hovered menu row should have one visible highlight');
            const m=strokes[0], left=Math.min(m.x1,m.x2)-m.diameter/2, right=Math.max(m.x1,m.x2)+m.diameter/2;
            const top=Math.max(m.y1,m.y2)+m.diameter/2, bottom=Math.min(m.y1,m.y2)-m.diameter/2;
            const rowTop=slot('y')+h/2-row*pitch;
            const margins=[left-(slot('x')-w/2),slot('x')+w/2-right,rowTop-top,bottom-(rowTop-pitch)];
            [4*sx,6*sx,4*sy,4*sy].forEach((expected,i)=>near(margins[i],expected,.011));
            report.rowInsets.push({row,stretchX,stretchY,margins});
        }
    }
}

function privateRowInsets(s) {
    const clock=s.vm.runtime.ioDevices.clock._projectTimer;
    let elapsed=0;
    clock.nowObj={now:()=>elapsed};clock.startTime=0;
    s.invoke('LG initialize');s.set('UI view',1);
    const menu={id:3,x:55,y:105,label:'Options',width:110,height:42,'panel width':164,
        'row height':34,items:'Group>One|Group>Two|Group>Three',mode:'panel',drag:0,join:0,quality:4,
        'open travel':.45,'open growth':.78,'close travel':.65,'close growth':.52,bounce:.40};
    const tick=()=>{
        elapsed+=1000/30;s.invoke('UI begin');s.configure('Menu',menu);s.invoke('LG advance');s.invoke('UI settle');
    };
    const advanceUntil=(done,description)=>{
        for(let j=0;j<120;j++){tick();if(done())return;}
        assert.fail('Timed out waiting for '+description);
    };
    const layer=k=>Number(s.get('UI layer '+k)[0]);
    const geometry=(child)=>{
        if(child){
            const h=layer('h'),w=layer('w'),refW=menu['panel width']+8,pitch=menu['row height'];
            return {x:layer('x'),y:layer('y'),w,h,sx:w/refW,sy:h/((layer('rows')+1)*pitch),pitch};
        }
        const slot=k=>Number(s.get(k)[2]),w=slot('w')*slot('scaleX'),h=slot('h')*slot('scaleY');
        return {x:slot('x'),y:slot('y'),w,h,sx:w/slot('UI expanded width'),sy:h/slot('UI expanded height'),pitch:menu['row height']};
    };
    function sampleInsets(row,which){
        const child=which!=='source tail',g=geometry(child);
        s.set('UI pressed id',0);s.set('UI hover id',3);s.set('UI hover row',row);s.set('UI hover layer',child?1:0);
        const marks=highlightMarks(s.capture('UI foreground')).filter(m=>m.rgba[3]>.001);
        assert.ok(marks.length,'Missing the real hover wash for '+which);
        const left=Math.min(...marks.map(m=>Math.min(m.x1,m.x2)-m.diameter/2));
        const right=Math.max(...marks.map(m=>Math.max(m.x1,m.x2)+m.diameter/2));
        const top=Math.max(...marks.map(m=>Math.max(m.y1,m.y2)+m.diameter/2));
        const bottom=Math.min(...marks.map(m=>Math.min(m.y1,m.y2)-m.diameter/2));
        const pitch=g.pitch*g.sy, upper=g.y+g.h/2-row*pitch;
        const margins=[left-(g.x-g.w/2),g.x+g.w/2-right,upper-top,bottom-(upper-pitch)];
        const tolerance=child?.02:1.05; // underlying root is clipped to existing stage-pixel scanlines
        [4*g.sx,6*g.sx,4*g.sy,4*g.sy].forEach((ref,i)=>near(margins[i],ref,tolerance));
        const rowY=upper-pitch/2;
        // The source underneath a retained child now consists of one-pixel
        // scanlines; inspect a stage texel center rather than the AA boundary.
        const center=sample(marks,g.x-g.sx,child?rowY:Math.floor(rowY)+.5);
        if(child){
            // The top layer washes use the layer's phase in their real Pen opacity.
            near(center.alpha,.15*Math.min(1,Math.max(0,layer('p'))),.001);
            assert.equal(center.coats,1,'Child row painted more than one visible coat');
        }else{
            near(center.alpha,.15,.001);
        }
        report.privateRowInsets.push({which,row,p:layer('p'),ink:layer('ink p'),margins,alpha:center.alpha});
    }
    report.privateRowInsets=[];
    advanceUntil(()=>Number(s.get('UI menu open fade')[2])>=1,'open parent');
    s.invoke('UI push %s path %s from %s row %s',3,'Group',0,1);
    advanceUntil(()=>layer('p')>.18&&layer('p')<.85,'opening child');
    for(const row of [0,1,3])sampleInsets(row,'opening');
    advanceUntil(()=>layer('p')===1&&layer('v')===0,'settled child');
    for(const row of [0,1,3])sampleInsets(row,'settled');
    s.invoke('UI pop %s to %s',3,'');
    advanceUntil(()=>layer('p')>.15&&layer('p')<.8,'returning child');
    for(const row of [0,1,3])sampleInsets(row,'closing');
    advanceUntil(()=>layer('p')===0&&layer('ink p')<0,'merged sheet with returning title');
    sampleInsets(1,'source tail');
}

(async()=>{
    const old=await scene(previousFile), current=await scene(currentFile);
    cases(old,current); foreground(old,current); privateRowInsets(current);
    assert.equal(hash(previousFile),report.previousSHA256); assert.equal(hash(currentFile),report.currentSHA256);
    old.vm.stopAll(); current.vm.stopAll(); report.passed=true;
})().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.mkdirSync(path.dirname(reportFile),{recursive:true});
    fs.writeFileSync(reportFile,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({passed:report.passed,direct:report.direct.length,
        foreground:report.foreground.length,error:report.error},null,2));
    process.exit(report.passed?0:1);
});
