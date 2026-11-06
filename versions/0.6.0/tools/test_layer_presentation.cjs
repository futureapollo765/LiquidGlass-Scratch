#!/usr/bin/env node
/** Check live exposure of an already-visible private panel at real VM yields.
 * Changes only in-memory state. Samples actual Pen draws at stage-pixel centers.
 * An optional, single 525 ms simulated slow stamp ensures the real uncompiled
 * scheduler can present any state in which multiple separated strips went blank.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const here=path.join(__dirname,'vm_harness.cjs');
const H=require(fs.existsSync(here)?here:path.resolve(__dirname,'../../../tools/vm_harness.cjs'));
const [project,output]=process.argv.slice(2);
if(!output)throw Error('Usage: node test_layer_presentation.cjs Studio.sb3 report.json');
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const report={project,sha256:hash(project),method:'TurboWarp desktop VM in interpreter mode with native Pen callbacks. Nine stage pixel centers inside the same private surface, separated by 16 px; traces include each scheduler yield. Allow up to two adjacent rows to be repainted at once. One 525 ms simulated slow Pen stamp is permitted when three rows are simultaneously missing.'};
const lg='Liquid Glass';
function unpack(rgb){return [(rgb>>16)&255,(rgb>>8)&255,rgb&255];}
function blend(dst,src,a){return dst.map((c,i)=>Math.round(c*(1-a)+src[i]*a));}
function deviation(a,b){return Math.max(...a.map((v,i)=>Math.abs(v-b[i])));}
async function main(){
    const vm=await H.loadProject(project),target=vm.runtime.targets.find(t=>t.getName()===lg);
    vm.setCompilerOptions({enabled:false});
    const varObj=name=>H.getVariable(vm,lg,name), get=name=>varObj(name).value, set=(name,x)=>{varObj(name).value=x;};
    const call=(code,...args)=>H.invoke(vm,lg,code,args,{maxMilliseconds:240000});
    const probes=Array.from({length:9},(_,i)=>({x:105.5,y:64.5-i*16,color:[0,0,0]}));
    const pixels=get('Original RGB');
    for(const p of probes)p.wallpaper=unpack(Number(pixels[(179-Math.floor(p.y))*480+Math.floor(p.x)+240]));
    let track=false,stall=false,stamps=0,lines=0,maxIntermediate=0,everMissing=false,phase='first',ticks=[];
    const missing=()=>probes.reduce((n,p)=>n+Number(deviation(p.color,p.finished)>20),0);
    function observe(allowStall){
        if(!track)return;
        const lost=missing();maxIntermediate=Math.max(maxIntermediate,lost);everMissing ||= lost>0;
        if(allowStall && lost>=3 && !stall){
            stall=true;const until=performance.now()+525;while(performance.now()<until){} // One bounded simulated slow GPU submit.
        }
    }
    function stroke(a,x,y,u=x,v=y){
        lines++;if(a.color4f[3]<=0)return;
        const source=a.color4f.slice(0,3).map(c=>Math.round(c*255));
        const offset=(a.diameter===1 || a.diameter===3)?.5:0;
        x+=offset;y+=offset;u+=offset;v+=offset;
        const dx=u-x,dy=v-y,sq=dx*dx+dy*dy;
        let changed=false;
        for(const p of probes){
            if(Math.abs(p.y-y)>a.diameter/2+1)continue;
            const t=sq?Math.max(0,Math.min(1,((p.x-x)*dx+(p.y-y)*dy)/sq)):0;
            const d=Math.hypot(p.x-x-dx*t,p.y-y-dy*t);
            const coverage=Math.max(0,Math.min(1,a.diameter/2+.5-d));
            if(coverage){p.color=blend(p.color,source,coverage*a.color4f[3]);changed=true;}
        }
        if(changed)observe(false);
    }
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},pick:()=>-1,
        penClear(){for(const p of probes)p.color=[0,0,0];observe(false);},
        penPoint(_skin,a,x,y){stroke(a,x,y);},penLine(_skin,a,x,y,u,v){stroke(a,x,y,u,v);},
        penStamp(){const c=target.sprite.costumes[target.currentCostume];
            if(!c.name.startsWith('LG strip '))return; // probes avoid SVG glyphs/symbols
            stamps++;let touched=false;for(const p of probes){if(p.y>=target.y-4 && p.y<target.y+4){p.color=[...p.wallpaper];touched=true;}}
            if(touched)observe(true);
        }};
    const step=vm.runtime._step.bind(vm.runtime);
    vm.runtime._step=(...args)=>{const result=step(...args);if(track)ticks.push({phase,missing:missing(),stamps,lines});return result;};
    call('LG initialize');set('UI view',1);
    const proto=Object.values(target.blocks._blocks).find(b=>b.opcode==='procedures_prototype' && b.mutation.proccode.startsWith('Glass %s x %s'));
    const names=JSON.parse(proto.mutation.argumentnames),defaults=JSON.parse(proto.mutation.argumentdefaults);
    const values={id:3,x:-77,y:0,width:210,height:174,shape:1,radius:16,reflection:.5,distortion:1,edge:1,highlight:1,light:-30,tint:.05,join:0,group:0,transition:0,spring:18,damping:1,pull:1,drag:0,quality:1};
    call(proto.mutation.proccode,...names.map((k,i)=>values[k]??defaults[i]));
    // A contrasting fully opaque material makes the published private surface,
    // bare wallpaper and base glass readily distinguishable numerically.
    call('LG material %s tint color %s transparency %s brightness %s blur %s',3,'#ED3191',0,0,2);
    call('LG advance');
    const owner=(n,v)=>{get(n)[2]=v;};
    for(const [n,v] of Object.entries({'UI live':1,'UI kind':'Menu','UI label':'Menu','UI open':1,'UI page':'Child','UI row height':28,'UI menu open fade':1,'UI menu dim':1,'UI root page fade':1}))owner(n,v);
    const record={owner:3,path:'Child',parent:'',row:1,p:1,v:0,goal:1,x:96,y:0,w:110,h:162,r:14,rows:0,pitch:28,offset:0,dim:0,fade:1,'next offset':-1,strokes:0};
    for(const [k,v] of Object.entries(record))set('UI layer '+k,[v]);
    const initial=call('LG render');
    probes.forEach(p=>{p.finished=[...p.color];assert.ok(deviation(p.finished,p.wallpaper)>50,'Child test fixture does not cover each reference probe');});
    // Invalidate the retained scene without changing its optical result: a full
    // redraw with the same already-visible child must keep showing that child.
    set('matRevision',+get('matRevision')+1);track=true;phase='redraw';stamps=0;lines=0;
    const repeated=call('LG render');
    const maxMissingAtYield=Math.max(0,...ticks.map(t=>t.missing));
    report.fixture={quality:get('q'),probeCount:probes.length,probeLocations:probes.map(({x,y})=>[x,y]),initial,repeated};
    report.history=ticks;report.maxMissingAtYield=maxMissingAtYield;report.maxMissingDuringPaint=maxIntermediate;report.stallInjected=stall;
    report.finalDeviation=probes.map(p=>deviation(p.color,p.finished));
    assert.ok(everMissing && stamps>0 && lines>0,'Fixture must exercise a dirty retained redraw');
    assert.ok(ticks.length>=2,'Expected a costly interpreted frame to cross scheduler yields');
    assert.ok(report.finalDeviation.every(d=>d<=1),'Completed child appearance changed on identical repaint');
    assert.ok(maxMissingAtYield<=2,`Published ${maxMissingAtYield}/${probes.length} missing rows`);
    assert.ok(maxIntermediate<=2,`Erased ${maxIntermediate}/${probes.length} child rows ahead of replay`);
    track=false;const priorStamps=stamps,priorLines=lines;call('LG render');
    report.idle={stamps:stamps-priorStamps,strokes:lines-priorLines};
    assert.equal(report.idle.stamps,0);assert.equal(report.idle.strokes,0);
    assert.equal(hash(project),report.sha256);report.passed=true;vm.stopAll();
}
main().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.mkdirSync(path.dirname(output),{recursive:true});fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({passed:report.passed,maxMissingAtYield:report.maxMissingAtYield,maxMissingDuringPaint:report.maxMissingDuringPaint,error:report.error}));process.exit(report.passed?0:1);
});
