#!/usr/bin/env node
/** Validate optical controls using the actual Pen lines emitted by exported native blocks. */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const H = require('./vm_harness.cjs');
const {gridPixel, logicalGrid} = require('./test_grid_pixels.cjs');

const [previousFile, currentFile, outputFile] = process.argv.slice(2);
if (!outputFile) throw new Error('Usage: node test_materials.cjs previous.sb3 current.sb3 report.json');
const digest = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const report = {previous: previousFile, current: currentFile, previousSHA256: digest(previousFile),
    currentSHA256: digest(currentFile), checks: [], samples: {},
    method: 'Installed TurboWarp VM running native Scratch blocks in compiled and interpreted modes. Renderer callbacks record each sampled Pen line’s actual RGBA and stage position.'};

function rgb(value) { return [16, 8, 0].map(shift => value >> shift & 255); }
function nearColor(actual, expected, margin = 1) {
    assert.equal(actual.length, expected.length);
    actual.forEach((v, i) => assert.ok(Math.abs(v-expected[i]) <= margin,
        `Expected ${JSON.stringify(actual)} within ${margin} of ${JSON.stringify(expected)}`));
}
function check(name, fn) { fn(); report.checks.push({name, passed: true}); }

async function scene(filename, compiler=true) {
    const vm = await H.loadProject(filename, {compiler});
    vm.setCompilerOptions({enabled: compiler});
    const target = vm.runtime.targets.find(t => t.getName() === 'Liquid Glass');
    const lines = [];
    vm.runtime.renderer = {
        createPenSkin: () => 1, createDrawable: () => 2, updateDrawableSkinId() {}, draw() {},
        penStamp() {}, penPoint() {}, penClear() {},
        penLine(_skin, attributes, x1, y1, x2, y2) {
            if (y1 === y2) lines.push({x:(x1+x2)/2,y:y1,
                color:Array.from(attributes.color4f).slice(0,3).map(c=>Math.round(c*255)), alpha:attributes.color4f[3]});
        },
    };
    const variable = name => H.getVariable(vm, 'Liquid Glass', name);
    const get = name => variable(name).value;
    const set = (name, value) => { variable(name).value = value; };
    const call = (code, ...args) => H.invoke(vm, 'Liquid Glass', code, args, {maxMilliseconds: 90000});
    function procedure(title) {
        const proto = Object.values(target.blocks._blocks).find(b => b.opcode === 'procedures_prototype'
            && b.mutation.proccode.startsWith(title + ' %s '));
        assert.ok(proto, `Missing ${title}`);
        return proto.mutation;
    }
    function configure(title, values) {
        const proc = procedure(title), names = JSON.parse(proc.argumentnames), defaults = JSON.parse(proc.argumentdefaults);
        for (const key of Object.keys(values)) assert.ok(names.includes(key), `${title} lacks ${key}`);
        call(proc.proccode, ...names.map((name,i) => values[name] ?? defaults[i]));
    }
    function reset(bg = 2) {
        call('LG initialize'); set('UI view', 0); set('Background', bg); call('UI begin');
    }
    function place(values = {}) {
        configure('Background', {id:1,x:0,y:0,width:40,height:24,radius:4,label:'',reflection:0,
            distortion:0,edge:0,highlight:0,tint:0,'tint color':'#FFFFFF',transparency:100,
            brightness:0,blur:0,quality:2,...values});
    }
    function render() { lines.length = 0; call('LG render'); return lines.slice(); }
    function at(lines,x,y) {
        const item = lines.find(line => Math.abs(line.x-x)<1e-7 && Math.abs(line.y-y)<1e-7);
        assert.ok(item, `No native glass stroke at (${x},${y}); ${lines.length} horizontal lines`);
        assert.ok(item.alpha > .99, `Expected an interior, fully covered glass sample; alpha ${item.alpha}`);
        return item.color;
    }
    return {vm,target,call,get,set,procedure,configure,reset,place,render,at};
}

function originalColor(s,bg,x,y) {
    const clampedX = Math.max(-240,Math.min(239,Math.round(x)));
    const clampedY = Math.max(-180,Math.min(179,Math.round(y)));
    const index = (179-clampedY)*480+clampedX+241;
    return rgb(Number(bg === 2 ? gridPixel(s.get('Grid RGB'),()=>s.get('LG grid rows'),index,()=>s.get('LG grid pixels')) : s.get('Original RGB')[index-1]));
}

function neutralAndTint(previous,current) {
    const props = {id:1,x:0,y:0,width:40,height:24,radius:4,label:'',reflection:0,distortion:0,
        edge:0,highlight:0,tint:0,quality:2};
    check('All public role blocks preserve existing arguments and expose the new material inputs', () => {
        for (const name of ['Glass','Background','Button','Menu']) {
            const oldNames = JSON.parse(previous.procedure(name).argumentnames);
            const newNames = JSON.parse(current.procedure(name).argumentnames);
            const material = ['tint color','transparency','brightness','blur'];
            const placement = name==='Menu' && newNames.includes('alignment') ? ['alignment','expanded x','expanded y'] : [];
            assert.deepEqual(newNames, [...oldNames,...[...material,...placement].filter(field=>!oldNames.includes(field))]);
        }
    });
    check('Neutral settings preserve the baseline native glass stroke colors on both supplied backgrounds', () => {
        for (const bg of [1,2]) {
            previous.reset(bg); current.reset(bg);
            const oldSupportsTint=JSON.parse(previous.procedure('Background').argumentnames).includes('transparency');
            previous.configure('Background',{...props,...(oldSupportsTint?{transparency:100,brightness:0,blur:0}:{})});
            current.place({'tint color':'#ff00ff',transparency:100,brightness:0,blur:0});
            const old = previous.render(), actual = current.render();
            for (const [x,y] of [[-8,0],[0,0],[6,8]]) {
                nearColor(current.at(actual,x,y),previous.at(old,x,y));
                nearColor(current.at(actual,x,y),originalColor(current,bg,x,y));
            }
        }
    });
    check('Actual Pen color blends hex and packed tints through the requested transparency and invalidates a retained frame', () => {
        current.reset();
        const hex = '#c44820', packed = 0xc44820, background = originalColor(current,2,0,0);
        current.place({'tint color': hex, transparency:100});
        const clear = current.at(current.render(),0,0);
        nearColor(clear,background);
        assert.equal(current.render().length,0,'A stationary unchanged scene repainted');
        current.place({'tint color':hex,transparency:50});
        const half = current.at(current.render(),0,0);
        nearColor(half,rgb(packed).map((src,i)=>(src+background[i])/2));
        current.place({'tint color':packed,transparency:0});
        const opaque = current.at(current.render(),0,0);
        nearColor(opaque,rgb(packed));
        current.place({'tint color':'#1649dc',transparency:0});
        const recolored = current.at(current.render(),0,0);
        nearColor(recolored,rgb(0x1649dc));
        report.samples.tint = {clear,half,opaque,recolored};
    });
    check('Positive and negative brightness move the native output toward white and black', () => {
        const colors = [];
        const original=originalColor(current,2,6,4);
        for (const brightness of [-100,-35,0,35,100]) {
            current.place({'tint color':'#6982a5',transparency:100,brightness});
            const lit=current.at(current.render(),6,4);
            nearColor(lit,original.map(v=>v*(1-Math.abs(brightness/100))+255*Math.max(0,brightness/100)));
            colors.push(lit);
        }
        nearColor(colors[0],[0,0,0]); nearColor(colors[2],original); nearColor(colors[4],[255,255,255]);
        for (let i=1;i<colors.length;i++) {
            for (let c=0;c<3;c++) assert.ok(colors[i][c]>colors[i-1][c]);
        }
        report.samples.brightness=colors;
    });
    check('Button and Menu forward their configured material to independently shaded contours',()=>{
        current.reset();
        const common={y:0,label:'',width:54,height:28,radius:10,reflection:0,distortion:0,edge:0,
            highlight:0,tint:0,join:0,group:0,quality:2,transparency:0,brightness:0,blur:0};
        current.configure('Button',{...common,id:4,x:-42,shape:'capsule','tint color':'#e87518'});
        current.configure('Menu',{...common,id:5,x:42,launcher:'circle',mode:'toggle',items:'A|B','tint color':0x2a96ce});
        current.call('LG advance'); current.call('UI settle');
        const frame=current.render();
        nearColor(current.at(frame,-42,0),rgb(0xe87518)); nearColor(current.at(frame,42,0),rgb(0x2a96ce));
    });
}

function linkedMaterials(s) {
    s.reset();
    const properties = {y:0,width:44,height:44,shape:3,radius:22,reflection:0,distortion:0,edge:0,
        highlight:0,light:-30,tint:0,join:24,group:1,transition:0,spring:18,damping:.85,pull:0,
        drag:0,quality:2,transparency:0,brightness:0,blur:0};
    s.configure('Glass',{...properties,id:1,x:-18,'tint color':'#FF0000'});
    s.configure('Glass',{...properties,id:2,x:18,'tint color':'#0000FF'});
    s.call('LG advance');
    check('Joined glass mixes the two per-slot materials continuously through the connecting region', () => {
        const frame=s.render();
        const samples=[-14,-2,0,2,14].map(x=>s.at(frame,x,0));
        nearColor(samples[2],[127.5,0,127.5],2);
        for(let i=1;i<samples.length;i++) {
            assert.ok(samples[i-1][0]>samples[i][0] && samples[i-1][2]<samples[i][2]);
        }
        s.configure('Glass',{...properties,id:1,x:-18,'tint color':'#00FF00'});
        const recolored=s.at(s.render(),0,0);
        nearColor(recolored,[0,127.5,127.5],2);
        report.samples.joined = {samples,recolored};
    });
}

// Independent local convolution of only the tiles surrounding each probe.
// Its input is the source pixel list, never a renderer cache or shader value.
function blurOracle(source, x, y, radius) {
    const radii = [0,2,6,12,20], steps = [1,3,8,12,16];
    const clamp = (v,hi) => Math.max(0,Math.min(hi,v));
    const sx=clamp(x+240,479), sy=clamp(179-y,359);
    radius=clamp(radius,20);
    function level(i) {
        if(!i) return rgb(source[Math.round(sy)*480+Math.round(sx)]);
        const step=steps[i], cols=Math.ceil(480/step), rows=Math.ceil(360/step);
        const sigma=Math.sqrt(radii[i]**2-step**2/4)/step, support=Math.ceil(3*sigma);
        const weights=Array.from({length:2*support+1},(_,j)=>Math.exp(-((j-support)**2)/(2*sigma*sigma)));
        const total=weights.reduce((a,b)=>a+b,0);
        const base=new Map(), horizontal=new Map();
        function averageTile(c,r) {
            const key=c+r*cols;
            if(!base.has(key)) {
                const value=[0,0,0];
                for(let dy=0;dy<step;dy++) for(let dx=0;dx<step;dx++) {
                    const pixel=source[clamp(r*step+dy,359)*480+clamp(c*step+dx,479)];
                    rgb(pixel).forEach((v,ch)=>value[ch]+=v);
                }
                base.set(key,value.map(v=>Math.round(v/(step*step))));
            }
            return base.get(key);
        }
        function convolve(sample) {
            const color=[0,0,0];
            weights.forEach((w,j)=>sample(j-support).forEach((v,ch)=>color[ch]+=w*v));
            return color.map(v=>Math.round(v/total));
        }
        function row(c,r) {
            const k=c+r*cols;
            if(!horizontal.has(k)) horizontal.set(k,convolve(j=>averageTile(clamp(c+j,cols-1),r)));
            return horizontal.get(k);
        }
        const filtered=(c,r)=>convolve(j=>row(c,clamp(r+j,rows-1)));
        const u=clamp((sx+.5)/step-.5,cols-1), v=clamp((sy+.5)/step-.5,rows-1);
        const u0=Math.floor(u), v0=Math.floor(v), du=u-u0, dv=v-v0;
        const value=[0,0,0];
        for(const [c,w] of [[u0,1-du],[clamp(u0+1,cols-1),du]]) {
            for(const [r,h] of [[v0,1-dv],[clamp(v0+1,rows-1),dv]]) {
                filtered(c,r).forEach((n,ch)=>value[ch]+=n*w*h);
            }
        }
        return value;
    }
    const hi=radii.findIndex(v=>v>=radius);
    if(!hi || radius===radii[hi]) return level(hi);
    const blend=(radius-radii[hi-1])/(radii[hi]-radii[hi-1]);
    const loValue=level(hi-1), hiValue=level(hi);
    return loValue.map((v,ch)=>v*(1-blend)+hiValue[ch]*blend);
}

function blurCases(s) {
    s.reset(2);
    check('Spatial blur softens a real calibration stripe and changes the retained output at fixed geometry',()=>{
        const samples=[];
        for(const blur of [0,1,2,4,6,9,12,16,20,100]) {
            s.place({blur});
            const lines=s.render();
            if(blur===100 && !lines.length) { samples.push({...samples.at(-1),blur}); continue; }
            const left=s.at(lines,0,6), nearby=s.at(lines,4,6);
            nearColor(left,blurOracle(logicalGrid(s.get('Grid RGB'),()=>s.get('LG grid rows'),()=>s.get('LG grid pixels')),0,6,blur),2);
            nearColor(nearby,blurOracle(logicalGrid(s.get('Grid RGB'),()=>s.get('LG grid rows'),()=>s.get('LG grid pixels')),4,6,blur),2);
            samples.push({blur,left,nearby,contrast:Math.hypot(...left.map((v,i)=>v-nearby[i]))});
        }
        nearColor(samples[0].left,originalColor(s,2,0,6));
        assert.ok(samples.at(-2).contrast < samples[0].contrast*.25);
        assert.ok(samples.find(s=>s.blur===6).contrast < samples[0].contrast);
        nearColor(samples.at(-1).left,samples.at(-2).left);
        report.samples.blur=samples;
    });
    check('Blur clamps each axis at all four actual stage corners without sampling the opposite edges',()=>{
        const quadrants=[0xe61e45,0x2744d8,0x1bd766,0xdcd330];
        const fixture=new Array(480*360);
        for(let row=0;row<360;row++) for(let col=0;col<480;col++) {
            fixture[row*480+col]=quadrants[(row>=180?2:0)+(col>=240?1:0)];
        }
        s.set('Grid RGB',fixture);
        s.call('LG rebuild blur %s',2);
        const cases=[[-238,176], [238,176], [-238,-176], [238,-176]];
        const values=[];
        for(let i=0;i<cases.length;i++) {
            const [x,y]=cases[i];
            s.place({x:x<0?-230:230,y:y<0?-168:168,width:34,height:32,blur:20});
            s.call('LG advance');
            const color=s.at(s.render(),x,y);
            nearColor(color,rgb(quadrants[i]),1); values.push({x,y,color});
        }
        report.samples.cornerBlur=values;
    });
}

async function main() {
    const previous = await scene(previousFile), current = await scene(currentFile);
    check('Packed grid preserves every reference pixel, expands for editing, and restores distinct rows after edits',()=>{
        const source=previous.get('Grid RGB').map(Number), packed=()=>logicalGrid(current.get('Grid RGB'),
            ()=>current.get('LG grid rows'),()=>current.get('LG grid pixels')).map(Number);
        assert.equal(source.length,480*360);assert.deepEqual(packed(),source);
        current.call('LG expand grid for editing');assert.deepEqual(current.get('Grid RGB').map(Number),source);
        const index=480*175+29,edited=(source[index]^0xabcdef)&0xffffff;
        current.get('Grid RGB')[index]=edited;
        current.call('LG grid pixel %s',index+1);assert.equal(Number(current.get('color')),edited);
        current.call('LG pack grid rows');assert.equal(current.get('Grid RGB').length,0);
        const changed=source.slice();changed[index]=edited;assert.deepEqual(packed(),changed);
        current.call('LG expand grid for editing');current.get('Grid RGB')[index]=source[index];
        current.call('LG pack grid rows');assert.deepEqual(packed(),source);
        report.samples.gridRows={originalPixels:source.length,packedRows:current.get('LG grid pixels').length/480};
    });
    neutralAndTint(previous,current);
    linkedMaterials(current);
    blurCases(current);
    previous.vm.stopAll(); current.vm.stopAll();
    const interpreted=await scene(currentFile,false);
    check('The Scratch interpreter renders the combined spatial blur, background brightness and colored coat in order',()=>{
        interpreted.reset(2);
        interpreted.place({width:24,height:18,'tint color':'#c44820',transparency:40,brightness:35,blur:6});
        const actual=interpreted.at(interpreted.render(),0,0);
        const blurred=blurOracle(logicalGrid(interpreted.get('Grid RGB'),()=>interpreted.get('LG grid rows'),()=>interpreted.get('LG grid pixels')),0,0,6);
        const expected=blurred.map((v,i)=>(v*.65+255*.35)*.4+rgb(0xc44820)[i]*.6);
        nearColor(actual,expected,2);
        report.samples.interpretedMixture={actual,expected};
    });
    interpreted.vm.stopAll();
    assert.equal(digest(previousFile),report.previousSHA256); assert.equal(digest(currentFile),report.currentSHA256);
    report.passed=true;
}
main().catch(error=>{ report.passed=false; report.error=String(error.stack||error); }).finally(()=>{
    fs.mkdirSync(path.dirname(outputFile),{recursive:true});
    fs.writeFileSync(outputFile,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,error:report.error},null,2));
    process.exit(report.passed?0:1);
});
