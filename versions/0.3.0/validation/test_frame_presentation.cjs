#!/usr/bin/env node
/** Compare frame presentation in the actual Scratch interpreter. The small CPU
 * raster below models Pen command ordering, background coverage and opacity at
 * stage-pixel centers. It is independent of the browser/GPU visual check. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const zlib = require('node:zlib');
const path = require('node:path');
const crypto = require('node:crypto');
const localHarness = path.join(__dirname, 'vm_harness.cjs');
const H = require(fs.existsSync(localHarness) ? localHarness : path.resolve(__dirname, '../../../tools/vm_harness.cjs'));

const [previousFile, currentFile, reportFile] = process.argv.slice(2);
if (!reportFile) throw Error('Usage: node test_frame_presentation.cjs previous.sb3 current.sb3 report.json');
const API = 'Glass %s x %s y %s width %s height %s shape %s radius %s reflection %s distortion %s edge %s highlight %s light %s tint %s join %s group %s transition %s spring %s damping %s pull %s drag %s quality %s';
const width = 480, height = 360;
const sha256 = filename => crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
const report = {previousFile, currentFile, previousSHA256:sha256(previousFile), currentSHA256:sha256(currentFile), scenarios: [],
    model: 'Real interpreter, with native Pen opcodes observed by a stage-resolution CPU raster. Chrome UI supplies independent visual verification.'};

function paeth(a,b,c) {
    const p = a + b - c, da = Math.abs(p-a), db = Math.abs(p-b), dc = Math.abs(p-c);
    return da <= db && da <= dc ? a : db <= dc ? b : c;
}

// The source project embeds lossless, non-interlaced 8-bit RGB/RGBA PNGs.
function decodePNG(bytes) {
    const w = bytes.readUInt32BE(16), h = bytes.readUInt32BE(20), type = bytes[25];
    assert.equal(bytes[24],8); assert.ok(type===2 || type===6, `unsupported PNG type ${type}`);
    assert.equal(bytes[28],0); const channels = type===6 ? 4 : 3, chunks=[];
    for (let pos=8; pos<bytes.length;) {
        const n=bytes.readUInt32BE(pos);
        if (bytes.toString('ascii', pos+4,pos+8)==='IDAT') chunks.push(bytes.subarray(pos+8,pos+8+n));
        pos+=n+12;
    }
    const packed=zlib.inflateSync(Buffer.concat(chunks)), pixels=Buffer.alloc(w*h*channels);
    const stride=w*channels;
    for(let y=0; y<h; y++) {
        const filter=packed[y*(stride+1)]; assert.ok(filter<=4);
        for(let j=0;j<stride;j++) {
            const i=y*stride+j, a=j>=channels ? pixels[i-channels] : 0,
                b=y ? pixels[i-stride] : 0, c=y && j>=channels ? pixels[i-stride-channels] : 0;
            const predictor=[0,a,b,(a+b)>>1,paeth(a,b,c)][filter];
            pixels[i]=(packed[y*(stride+1)+1+j]+predictor)&255;
        }
    }
    return {w,h,channels,pixels};
}

function over(dst,src,a) {
    if (a>=1) return src;
    const channel=shift => Math.round(((dst>>shift)&255)*(1-a)+((src>>shift)&255)*a);
    return channel(16)*65536+channel(8)*256+channel(0);
}

class PenTrace {
    constructor(vm,target,assets) {
        this.vm=vm; this.target=target; this.assets=assets;
        this.canvas=new Uint32Array(width*height); this.canvas.fill(0x1c3049);
        this.color=0; this.opacity=1; this.size=1; this.down=false; this.reset();
        const runtimeStep=vm.runtime._step.bind(vm.runtime);
        vm.runtime._step=(...args)=>{const result=runtimeStep(...args);this.afterStep?.();return result;};
        this.watch('pen_clear',()=>{this.canvas.fill(0x1c3049); this.clears++;});
        this.watch('pen_stamp',()=>this.stamp());
        this.watch('pen_setPenSizeTo',args=>this.size=Number(args.SIZE));
        this.watch('pen_setPenColorToColor',args=>{this.color=Number(args.COLOR)&0xffffff;this.opacity=1;});
        this.watch('pen_setPenColorParamTo',args=>{
            if(args.COLOR_PARAM==='transparency') this.opacity=1-Number(args.VALUE)/100;
        });
        this.watch('pen_penDown',()=>{this.down=true; this.stroke(target.x,target.y,target.x,target.y);});
        this.watch('pen_penUp',()=>this.down=false);
        const move=vm.runtime._primitives.motion_gotoxy;
        vm.runtime._primitives.motion_gotoxy=(args,util)=>{
            const x=target.x,y=target.y; const result=move(args,util);
            if(this.down) this.stroke(x,y,target.x,target.y);
            return result;
        };
    }
    watch(opcode,observer) {
        const original=this.vm.runtime._primitives[opcode]; assert.ok(original,opcode);
        this.vm.runtime._primitives[opcode]=(args,util)=>{observer(args,util);return original(args,util);};
    }
    reset() { this.stamps=[]; this.clears=0; this.lines=0; this.strokeCalls=0; this.commands=new Set(); }
    stamp() {
        const t=this.target,c=t.sprite.costumes[t.currentCostume], img=this.assets[c.name];
        assert.ok(img,`Missing asset ${c.name}`); const scale=t.size/100/c.bitmapResolution;
        const left=t.x-c.rotationCenterX*scale,top=t.y+c.rotationCenterY*scale;
        const rect={name:c.name,left,top,w:img.w*scale,h:img.h*scale}; this.stamps.push(rect);
        const y0=Math.max(0,Math.floor(180-top)), y1=Math.min(height,Math.ceil(180-top+rect.h));
        const x0=Math.max(0,Math.floor(240+left)),x1=Math.min(width,Math.ceil(240+left+rect.w));
        for(let j=y0;j<y1;j++)for(let i=x0;i<x1;i++) {
            const sx=Math.floor((i-239.5-left)/scale),sy=Math.floor((top-179.5+j)/scale);
            if(sx<0 || sy<0 || sx>=img.w || sy>=img.h) continue;
            const n=(sy*img.w+sx)*img.channels,rgb=img.pixels[n]*65536+img.pixels[n+1]*256+img.pixels[n+2];
            this.canvas[j*width+i]=over(this.canvas[j*width+i],rgb,img.channels===4?img.pixels[n+3]/255:1);
        }
        if(rect.w>=width && rect.h>=height) this.background=this.canvas.slice();
        this.afterStamp?.();
    }
    stroke(x,y,u,v) {
        this.strokeCalls++;
        const r=this.size/2,dx=u-x,dy=v-y,l=dx*dx+dy*dy;
        if(l) {this.lines++;this.commands.add(JSON.stringify([x,y,u,v,this.color,this.opacity,this.size]));}
        const x0=Math.max(0,Math.floor(240+Math.min(x,u)-r-1)),x1=Math.min(width,Math.ceil(240+Math.max(x,u)+r+1));
        const y0=Math.max(0,Math.floor(180-Math.max(y,v)-r-1)),y1=Math.min(height,Math.ceil(180-Math.min(y,v)+r+1));
        for(let j=y0;j<y1;j++)for(let i=x0;i<x1;i++) {
            const xx=i-239.5,yy=179.5-j,t=l?Math.max(0,Math.min(1,((xx-x)*dx+(yy-y)*dy)/l)):0;
            const coverage=Math.max(0,Math.min(1,r+.5-Math.hypot(xx-x-t*dx,yy-y-t*dy)));
            const n=j*width+i; this.canvas[n]=over(this.canvas[n],this.color,coverage*this.opacity);
        }
    }
}

async function scene(filename) {
    const zip=await H.libraries().JSZip.loadAsync(fs.readFileSync(filename));
    const project=JSON.parse(await zip.file('project.json').async('string'));
    const sprite=project.targets.find(t=>t.name==='Liquid Glass'),assets={};
    for(const c of sprite.costumes) if(c.dataFormat==='png') assets[c.name]=decodePNG(await zip.file(c.md5ext).async('nodebuffer'));
    const vm=await H.loadProject(filename), target=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass');
    const trace=new PenTrace(vm,target,assets);
    const call=(code,...args)=>H.invoke(vm,'Liquid Glass',code,args,{maxMilliseconds:90000});
    call('LG initialize');
    return {vm,call,trace,set:(name,value)=>H.getVariable(vm,'Liquid Glass',name).value=value};
}

function place(s,{id=1,x=-36,y=13,w=30,h=16,shape=1,q=2}={}) {
    s.call(API,id,x,y,w,h,shape,5,.5,1,1,1,-30,.05,7,1,0,18,.85,.9,1,q);
}

function channelDifference(x,y) {
    return Math.max(...[0,8,16].map(shift=>Math.abs(((x>>shift)&255)-((y>>shift)&255))));
}

async function main() {
    const old=await scene(previousFile),current=await scene(currentFile);
    const scenarios=[
        ['default three-shape scene',s=>s.call('LG demo')],
        ['default three-shape repeat',s=>s.call('LG demo')],
        ['first frame',s=>{s.call('LG initialize');place(s);place(s,{id:2,x:23,y:-47,w:22,h:22,shape:3});}],
        ['unchanged frame',()=>{}],
        ['move across strips',s=>place(s,{x:42,y:-40})],
        ['finer quality',s=>place(s,{x:42,y:-40,q:1})],
        ['change background',s=>s.set('Background',2)],
        ['hide both shapes',s=>{place(s,{shape:0});place(s,{id:2,shape:0});}],
        ['show after empty frame',s=>place(s,{x:24,y:34,w:57,h:13,shape:2,q:3})],
    ];
    for (const [name,setup] of scenarios) {
        const a=old.trace,b=current.trace;
        const repeated=name==='unchanged frame' || name==='default three-shape repeat';
        const beforeMove = name==='move across strips' ? b.canvas.slice() : null;
        const exposure={stampMax:0,oldTickMax:0,newTickMax:0,oldTicks:0,newTicks:0};
        a.afterStep=b.afterStep=b.afterStamp=null;
        if(repeated) {
            // Monitor unchanged visible foreground across VM ticks as well as
            // after individual strip stamps. Erasing all strips, then only
            // later painting the foreground would fail this test.
            const visible=[],background=a.background.slice();
            for(let i=0;i<a.canvas.length;i++) {
                if(channelDifference(a.canvas[i],background[i])>=12)visible.push(i);
            }
            assert.ok(visible.length>100,'baseline needs visible glass for exposure check');
            const missing=trace=>visible.filter(i=>channelDifference(trace.canvas[i],background[i])<=2).length/visible.length;
            a.afterStep=()=>{exposure.oldTicks++;exposure.oldTickMax=Math.max(exposure.oldTickMax,missing(a));};
            b.afterStep=()=>{exposure.newTicks++;exposure.newTickMax=Math.max(exposure.newTickMax,missing(b));};
            b.afterStamp=()=>{exposure.stampMax=Math.max(exposure.stampMax,missing(b));};
        }
        for(const s of [old,current]) {setup(s);s.call('LG advance');s.trace.reset();s.call('LG render');}
        const fullStamps=b.stamps.filter(s=>s.w>=width&&s.h>=height).length;
        const missing=[...a.commands].filter(k=>!b.commands.has(k)).length;
        const extras=[...b.commands].filter(k=>!a.commands.has(k)).length;
        let changed=0,maxError=0,big=0,movedPixels=0;
        for(let i=0;i<a.canvas.length;i++) {
            if(beforeMove && b.canvas[i]!==beforeMove[i])movedPixels++;
            const d=channelDifference(a.canvas[i],b.canvas[i]);if(d)changed++;if(d>3)big++;maxError=Math.max(maxError,d);
        }
        const item={name,oldClears:a.clears,clears:b.clears,fullStamps,strips:b.stamps.length-fullStamps,
            oldLines:a.lines,lines:b.lines,strokeCalls:b.strokeCalls,
            ...(beforeMove ? {movedPixels} : {}),sourceUniqueStrokes:a.commands.size,missingUniqueStrokes:missing,
            additionalUniqueStrokes:extras,changedPixels:changed,channelErrorOver3:big,maxChannelError:maxError,
            ...(repeated ? {exposure} : {})};
        report.scenarios.push(item);
        assert.equal(a.clears,1,`${name}: incorrect baseline`);
        assert.equal(b.clears,0,`${name}: global pen clear`);
        if(!['default three-shape scene','first frame','change background'].includes(name))assert.equal(fullStamps,0,`${name}: full background stamp`);
        assert.equal(changed,0,`${name}: finished frame differs at ${changed} pixels (${maxError} maximum)`);
        if(repeated) {
            assert.equal(b.strokeCalls,0,`${name}: idle frame issued Pen drawing commands`);
            assert.equal(b.stamps.length,0,`${name}: idle frame issued stamp commands`);
        } else {
            assert.equal(missing,0,`${name}: scheduled redraw omitted original draw commands`);
        }
        if(beforeMove) {
            assert.ok(movedPixels>100 && b.stamps.length>0 && b.lines>0,
                'motion must invalidate the cached frame and repaint old and new footprints');
        }
        assert.ok(exposure.stampMax<0.8 && exposure.newTickMax<0.8,`${name}: visible glass disappeared during the frame`);
        assert.equal(extras,0,`${name}: new optics draw command`);
    }
    for(const s of [old,current])s.vm.stopAll();
    report.passed=true;
}
main().catch(error=>{report.passed=false;report.error=String(error);process.exitCode=1;}).finally(()=>{
    fs.writeFileSync(reportFile,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));process.exit(process.exitCode||0);
});
