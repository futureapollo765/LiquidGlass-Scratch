#!/usr/bin/env node
/** Compare native translucent strokes and single-cover samples on the exact same ink poses. */
const H=require('./vm_harness.cjs'), fs=require('node:fs'), assert=require('node:assert/strict'), crypto=require('node:crypto');
const [prior,current,out]=process.argv.slice(2);
if(!out)throw Error('Usage: node test_ink_opacity.cjs prior.sb3 current.sb3 report.json');
const hash=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const report={sha256:hash(current),priorSHA256:hash(prior),checks:[],cases:[]};
const near=(a,b,e=1e-6)=>assert.ok(Math.abs(a-b)<=e,`Expected ${a} within ${e} of ${b}`);
const clamp=a=>Math.max(0,Math.min(1,a));
async function scene(file,compiler){
    const vm=await H.loadProject(file,{compiler}),target=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass');
    const vars=new Map(Object.values(target.variables).map(v=>[v.name,v]));
    const get=k=>vars.get(k)?.value, set=(k,v)=>vars.get(k).value=v;
    let ops=[];
    const record=(attr,x,y,u,v)=>{if(attr.color4f[3]>.00001)ops.push({type:'pen',x,y,u,v,a:attr.color4f[3],d:attr.diameter});};
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},pick:()=>-1,penClear(){},
        penPoint(_,a,x,y){record(a,x,y,x,y);},penLine(_,a,x,y,u,v){record(a,x,y,u,v);},
        penStamp(){
            const name=target.sprite.costumes[target.currentCostume].name;
            ops.push({type:'tile',name,x:target.x,y:target.y,size:target.size,a:1-Number(target.effects.ghost)/100,
                source:target.sprite.costumes[Number(get('UI path index'))-1]?.name});
        }};
    const call=(code,...args)=>H.invoke(vm,'Liquid Glass',code,args,{maxMilliseconds:90000});
    call('LG initialize');
    function paint(mark,sx,sy,opacity,angle=0){
        ops=[];
        set('UI view',1);set('UI art id',3);set('UI draw layer',0);set('UI ink opacity',opacity);
        set('UI cx',.5);set('UI cy',.5);set('UI ink scale x',sx);set('UI ink scale y',sy);
        const result=mark==='chevron'?call('UI disclosure facing %s',angle):
            call('UI text %s x %s y %s width %s align %s',mark,.5,.5,80,'left');
        return {ops:ops.slice(),elapsedMs:result.elapsedMs};
    }
    return {vm,paint};
}
function mask(render,x,y){
    let alpha=0,coats=0;
    for(const op of render.ops){
        let coverage;
        if(op.type==='tile'){
            if(!op.name.startsWith('UI ink sample '))continue;
            const half=4*op.size/100;coverage=Math.abs(op.x-x)<half&&Math.abs(op.y-y)<half?1:0;
        }else{
            const dx=op.u-op.x,dy=op.v-op.y,l=dx*dx+dy*dy;
            const t=l?clamp(((x-op.x)*dx+(y-op.y)*dy)/l):0;
            coverage=clamp(op.d/2+.5-Math.hypot(x-op.x-t*dx,y-op.y-t*dy));
        }
        const ink=coverage*op.a;if(ink>.000001){coats++;alpha=ink+(1-ink)*alpha;}
    }
    return {alpha,coats};
}
async function compare(){
    const old=await scene(prior,true),next=await scene(current,true);
    for(const [mark,sx,sy,angle] of [['H',1.31,1.12,0],['O',.81,1.25,0],['é',1.28,.83,0],['chevron',1.29,.88,37]]){
        const a=.42,b=.71,previous=old.paint(mark,sx,sy,a,angle),first=next.paint(mark,sx,sy,a,angle),second=next.paint(mark,sx,sy,b,angle);
        const name=mark==='chevron'?'UI icon next':`UI glyph [${mark}]`;
        assert.ok(first.ops.length>=9,`No physical mask for ${mark}`);
        assert.ok(first.ops.every(o=>o.type==='tile'&&o.name.startsWith('UI ink sample ')&&o.source===name));
        const seen=new Set();
        for(const o of first.ops){
            near(o.x*2-Math.floor(o.x*2),.5);near(o.y*2-Math.floor(o.y*2),.5);near(o.size,6.25);
            const k=o.x+','+o.y;assert.ok(!seen.has(k),'A stage cell received two coats of the glyph');seen.add(k);
        }
        let worstOld=0,worstNew=0,inside=0;
        for(let y=-20+.25;y<=20;y+=.5)for(let x=-20+.25;x<=20;x+=.5){
            const before=mask(previous,x,y),after=mask(first,x,y),other=mask(second,x,y);
            worstOld=Math.max(worstOld,before.alpha);worstNew=Math.max(worstNew,after.alpha);
            assert.ok(after.alpha<=a+1e-6&&after.coats<=1,'Transformed joint exceeded its group opacity');
            // Cells below 0.1% alpha are culled. Their largest possible
            // difference is smaller than one native framebuffer alpha level.
            near(other.alpha,after.alpha*b/a,1/255);
            if(after.alpha>a*.97)inside++;
        }
        assert.ok(worstOld>a+.09,`Baseline did not reproduce the overlap for ${mark}`);
        assert.ok(inside>0,'The repaired glyph must still contain a full-coverage stroke');
        report.cases.push({mark,sx,sy,angle,requested:a,worstOld,worstNew,nearSolidPixels:inside,uniqueSamples:seen.size,compiledMs:first.elapsedMs});
    }
    const native=next.paint('H',.947,.956,.42);
    assert.equal(native.ops.length,1);assert.equal(native.ops[0].name,'UI glyph [H]');near(native.ops[0].a,.42);
    near(native.ops[0].x,.5);near(native.ops[0].y,.5);near(native.ops[0].size,95.15);
    const stampTurn=next.paint('chevron',.947,.956,.42,53);
    assert.equal(stampTurn.ops.length,1);assert.equal(stampTurn.ops[0].name,'UI icon next');near(stampTurn.ops[0].a,.42);
    const interpreted=await scene(current,false);
    const foreground=interpreted.paint('H',1.31,1.12,.42);
    assert.ok(foreground.ops.length>10&&foreground.ops.every(o=>o.name?.startsWith('UI ink sample ')));
    report.interpretedMs=foreground.elapsedMs;
    [old,next,interpreted].forEach(s=>s.vm.stopAll());
    report.checks.push('Every changed glyph and rotated chevron emitted at most one visible sample per physical stage cell.',
        'The original renderer exceeded group opacity at joins; the repaired output never exceeded it.',
        'Opacity changes scale the composed face/outline alpha linearly to within one framebuffer alpha level at every tested location.',
        'Independent X/Y stretch, 37-degree rotation, and accented Latin retain full-coverage visible ink.',
        'The dimmed parent-scale pose uses a single original SVG stamp within the source curve tolerance; a near-isotropic disclosure stays a single rotated stamp.',
        'The same native mask path executes without the compiler.');
    report.passed=true;
}
compare().catch(e=>{report.passed=false;report.error=String(e.stack||e)}).finally(()=>{
    fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));process.exit(report.passed?0:1);
});
