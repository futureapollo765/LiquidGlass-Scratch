#!/usr/bin/env node
/** Run the migrated public blocks in the green-flag loop; observe real pointer input and Pen output. */
const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const [file,output]=process.argv.slice(2);
if(!output)throw Error('Usage: node test_control_motion.cjs Studio.sb3 report.json');
const report={sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),checks:[],positions:{},ink:[]};
const near=(a,b,t=.11)=>assert.ok(Math.abs(a-b)<=t,`Expected ${a} within ${t} of ${b}`);
const anchor=[15,28],button=[-80,-92],rest=[100,40],panel=[180,96];
async function scene(){
    const {VM,Storage,JSZip}=H.libraries(),z=await JSZip.loadAsync(fs.readFileSync(file));
    const doc=JSON.parse(await z.file('project.json').async('string')),t=doc.targets.find(s=>s.name==='Liquid Glass');
    const blocks=Object.values(t.blocks);
    function configure(kind,fields){
        const proto=blocks.find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith(kind+' %s '));
        const calls=blocks.filter(b=>b.opcode==='procedures_call'&&b.mutation.proccode===proto.mutation.proccode);
        assert.equal(calls.length,1);
        const keys=JSON.parse(proto.mutation.argumentids),names=JSON.parse(proto.mutation.argumentnames);
        for(const [name,val] of Object.entries(fields)){
            assert.ok(names.includes(name),'Missing '+kind+' '+name);const id=keys[names.indexOf(name)];
            if(typeof val==='object'){
                const vid='fixture-input-'+name;
                t.variables[vid]=[vid,val.initial];calls[0].inputs[id]=[3,[12,vid,vid],[10,'']];
            }else calls[0].inputs[id]=[1,[10,String(val)]];
        }
    }
    configure('Button',{x:button[0],y:button[1],shape:'capsule',width:140,height:46,label:'HH',pull:1,quality:4});
    configure('Menu',{x:anchor[0],y:anchor[1],launcher:'capsule',width:rest[0],height:rest[1],label:'HH',
        'panel width':panel[0],'row height':24,items:'One|Two|Three',mode:0,drag:1,pull:1,quality:4,
        alignment:{initial:'bottom center'},'expanded x':{initial:0},'expanded y':{initial:0}});
    z.file('project.json',JSON.stringify(doc));const vm=new VM();vm.attachStorage(new Storage());
    await vm.loadProject(await z.generateAsync({type:'nodebuffer'}));vm.setCompilerOptions({enabled:true});
    const target=vm.runtime.targets.find(e=>e.getName()==='Liquid Glass');
    const variable=n=>H.getVariable(vm,'Liquid Glass',n), get=n=>variable(n).value;
    const slot=(n,id)=>Number(get(n)[id-1]);
    const pose=id=>({x:slot('x',id),y:slot('y',id),w:slot('w',id),h:slot('h',id),
        sx:slot('scaleX',id),sy:slot('scaleY',id),phase:slot('UI menu open fade',id)});
    let now=0,ink=[],lastInk=[];
    const costume=()=>target.sprite.costumes[target.currentCostume]?.name;
    function stroke(a,x,y,u,v){
        const art=costume();
        if(!a.color4f[3] || !(art==='UI glyph [H]' || /^UI icon (down|up)$/.test(art)))return;
        // Track the native white foreground ink separately from its dark outline.
        if(a.color4f[0]<.9)return;
        ink.push({owner:Number(get('UI art id')),art,x,y,u,v,radius:a.diameter/2,alpha:Number(get('UI ink opacity')),
            origin:Number(get('UI letter world x')),originY:Number(get('UI letter world y'))});
    }
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},pick:()=>-1,penClear(){},
        penPoint(_,a,x,y){stroke(a,x,y,x,y);},penLine(_,a,x,y,u,v){stroke(a,x,y,u,v);},
        penStamp(){const art=costume();if(art==='UI glyph [H]' || /^UI icon (down|up)$/.test(art))
            ink.push({owner:Number(get('UI art id')),art,alpha:Number(get('UI ink opacity')),stamp:true,x:target.x,y:target.y,size:target.size});}};
    const clock=vm.runtime.ioDevices.clock._projectTimer;clock.nowObj={now:()=>now};clock.startTime=0;
    const tick=(n=1)=>{for(let i=0;i<n;i++){ink=[];now+=1000/30;vm.runtime._step();if(ink.length)lastInk=ink;}};
    const mouse=(x,y,isDown)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});
    const click=(x,y)=>{mouse(x,y,true);tick(2);mouse(x,y,false);tick();};
    function settle(id,p){for(let i=0;i<70;i++){tick();if(Math.abs(pose(id).phase-p)<1e-6)break;}
        near(pose(id).phase,p,.0001);tick(4);}
    return {vm,mouse,tick,click,pose,get,slot,settle,ink:()=>lastInk,set:(key,val)=>{variable('fixture-input-'+key).value=val;}};
}
function checkInk(s,ref,id,pose,name){
    const base=id===2?[140,46]:rest;
    const sx=pose.w*pose.sx/base[0],sy=pose.h*pose.sy/base[1],a=id===2?button:anchor;
    const groups=new Map();
    for(const e of s.ink().filter(e=>e.owner===id&&!e.stamp&&e.art==='UI glyph [H]')){
        if(!groups.has(e.origin))groups.set(e.origin,[]);groups.get(e.origin).push(e);
    }
    assert.equal(groups.size,2,'Both H outlines must be drawn using native Pen strokes');
    const sorted=[...groups.values()].sort((l,r)=>l[0].origin-r[0].origin);
    const bounds=[];
    for(const [index,g] of sorted.entries()){
        const ox=pose.x+(ref[index].x-a[0])*sx, oy=pose.y+(ref[index].y-a[1])*sy;
        near(g[0].origin,ox,.05);
        const got=[Math.min(...g.map(e=>Math.min(e.x,e.u)-e.radius)),Math.max(...g.map(e=>Math.max(e.x,e.u)+e.radius)),
            Math.min(...g.map(e=>Math.min(e.y,e.v)-e.radius)),Math.max(...g.map(e=>Math.max(e.y,e.v)+e.radius))];
        // Reference comes from the original H SVG: x=0..7, y=-4..6, with a 1.42 px rounded stroke.
        const want=[ox-.71*sx,ox+7.71*sx,oy-4.71*sy,oy+6.71*sy];
        want.forEach((n,i)=>near(got[i],n,1.1));
        bounds.push(got.map(v=>Math.round(v*100)/100));
    }
    near(sorted[1][0].origin-sorted[0][0].origin,(ref[1].x-ref[0].x)*sx,.05);
    report.ink.push({name,sx,sy,bounds});
}
function normalized(p,end){
    const dx=end[0]-anchor[0],dy=end[1]-anchor[1];
    return {travel:((p.x-anchor[0])*dx+(p.y-anchor[1])*dy)/(dx*dx+dy*dy),size:(p.h-rest[1])/(panel[1]-rest[1]),phase:p.phase};
}
async function main(){
    const s=await scene();
    s.mouse(224,-155,false);s.vm.greenFlag();s.tick(5);
    const canonical=s.ink().filter(e=>e.stamp);
    for(const [id,at] of [[2,button],[3,anchor]]){
        const ref=canonical.filter(e=>e.owner===id&&e.art==='UI glyph [H]').sort((a,b)=>a.x-b.x);assert.equal(ref.length,2);
        const before=Number(s.get('UI event number'));
        for(const [dx,dy] of [[92,0],[0,-72],[-70,45]]){
            s.mouse(...at,true);s.tick(2);s.mouse(at[0]+dx,at[1]+dy,true);s.tick(8);
            const p=s.pose(id);
            for(const [delta,center,val] of [[dx,at[0],p.x],[dy,at[1],p.y]]){
                if(delta===0)near(val,center,.01);
                else assert.ok((val-center)/delta>.02&&(val-center)/delta<.65,'Expected a bounded signed displacement');
            }
            if(dx===0)assert.ok(p.sx<1&&p.sy>1.02);
            if(dy===0)assert.ok(p.sx>1.02&&p.sy<1);
            checkInk(s,ref,id,p,id+': '+dx+','+dy);
            s.mouse(at[0]+dx,at[1]+dy,false);s.tick(45);
            near(s.pose(id).x,at[0],.05);near(s.pose(id).y,at[1],.05);
            near(s.pose(id).sx,1,.01);near(s.pose(id).sy,1,.01);
            assert.equal(Number(s.get('UI event number')),before);assert.equal(s.slot('UI open',3),0);
        }
    }
    report.checks.push('Button and Menu follow signed horizontal, vertical and diagonal pulls and retract to their configured centers without activating.',
        'Native white glyph outlines and inter-letter spacing agree with independently transformed source SVG edges through six control poses.');
    const modes=['top left','top right','bottom left','bottom right','bottom center','custom'];
    for(const mode of modes){
        const end=mode==='custom'?[116,-61]:[anchor[0]+(mode.includes('left')?-40:mode.includes('right')?40:0),
            anchor[1]+(mode.includes('top')?28:-28)];
        s.set('alignment',mode);s.set('expanded x',end[0]);s.set('expanded y',end[1]);s.tick(2);
        s.click(...anchor);s.mouse(224,-155,false);
        const open=[];let traveling;
        for(let i=0;i<60;i++){
            s.tick();const g=s.pose(3);open.push(normalized(g,end));
            if(mode==='bottom center'&&!traveling&&g.phase>.35&&g.phase<.85)traveling={pose:g,ink:[...s.ink()]};
            if(g.phase===1)break;
        }
        const p=s.pose(3);near(p.phase,1);near(p.x,end[0]);near(p.y,end[1]);near(p.w,panel[0]);near(p.h,panel[1]);
        for(const f of open.filter(f=>f.phase>.08&&f.phase<.98)){
            near(f.travel,1-(1-f.phase)**2,.022);
            // The launcher's transient hover/press lift can contribute about two stage pixels.
            near(f.size,f.phase**2,.045);
        }
        assert.ok(open.some(f=>f.phase<.85&&f.travel>f.size+.23),'Position must lead panel growth');
        if(mode==='bottom center'){
            assert.ok(traveling);
            const g=traveling.pose;
            const pos=e=>[e.stamp?e.x:e.origin,e.stamp?e.y:e.originY];
            for(const [face,base,center,targetInk,alpha,icon] of [
                ['launcher',rest,anchor,canonical,1-g.phase,'down'],['panel',panel,end,s.ink(),g.phase,'up'],
            ]){
                const sx=g.w*g.sx/base[0],sy=g.h*g.sy/base[1];
                const faceInk=traveling.ink.filter(e=>e.owner===3&&Math.abs(e.alpha-alpha)<.0001);
                const originals=targetInk.filter(e=>e.owner===3&&e.stamp&&(e.art==='UI glyph [H]'||e.art==='UI icon '+icon));
                assert.equal(originals.length,3,'Expected two title letters and the '+face+' arrow');
                assert.ok(faceInk.some(e=>!e.stamp),'Expected native nonuniform Pen artwork in transition');
                for(const orig of originals){
                    const x=g.x+(orig.x-center[0])*sx,y=g.y+(orig.y-center[1])*sy;
                    assert.ok(faceInk.some(e=>e.art===orig.art&&Math.abs(pos(e)[0]-x)<.06&&Math.abs(pos(e)[1]-y)<.06),
                        face+' '+orig.art+' must stay registered during the crossfade');
                }
            }
            report.checks.push('Both transitioning Menu titles and their up/down icons use the same moving, independently scaled face as their glass.');
        }
        const newEnd=[...end];
        if(mode==='custom'){
            const newer=[-119,79];s.set('expanded x',newer[0]);s.set('expanded y',newer[1]);s.tick();
            const mid=s.pose(3);assert.ok(mid.x<end[0]&&mid.x>newer[0]&&mid.y>end[1]&&mid.y<newer[1]);
            s.tick(40);near(s.pose(3).x,newer[0]);near(s.pose(3).y,newer[1]);newEnd.splice(0,2,...newer);
            report.positions.retarget={initial:end,first:[mid.x,mid.y],settled:newer};
        }
        s.mouse(224,-155,true);s.tick();s.mouse(224,-155,false);
        const close=[];for(let i=0;i<65;i++){s.tick();const g=s.pose(3);close.push(normalized(g,newEnd));if(g.phase===0)break;}
        near(s.pose(3).x,anchor[0]);near(s.pose(3).y,anchor[1]);near(s.pose(3).w,rest[0]);near(s.pose(3).h,rest[1]);
        for(const f of close.filter(f=>f.phase>.08&&f.phase<.98)){
            near(f.travel,1-(1-f.phase)**2,.022);
            // The launcher's transient hover/press lift can contribute about two stage pixels.
            near(f.size,f.phase**2,.045);
        }
        assert.ok(close.some(f=>f.phase<.85&&f.travel>f.size+.23),'Closing must retrace the opening curves');
        report.positions[mode]={end,intermediate:open.find(f=>f.phase>.25&&f.phase<.8)};
    }
    // Reverse mid-flight using a real outside press, prior to reaching either endpoint.
    s.set('alignment','bottom right');s.tick(2);s.click(...anchor);s.mouse(224,-155,false);
    let p=s.pose(3);for(let i=0;i<12&&p.phase<.42;i++){s.tick();p=s.pose(3);}
    assert.ok(p.phase>.22&&p.phase<.88,'Expected an interruptible intermediate pose');
    s.mouse(224,-155,true);s.tick();s.mouse(224,-155,false);
    assert.equal(s.slot('UI open',3),0);
    const turn=[p];
    for(let i=0;i<12;i++){s.tick();turn.push(s.pose(3));if(turn.at(-1).phase<p.phase)break;}
    const q=turn.at(-1);
    assert.ok(q.phase>0&&q.phase<p.phase&&q.h<p.h,'The same intermediate body must ease into closing');
    for(let i=1;i<turn.length;i++)assert.ok(Math.abs(turn[i].phase-turn[i-1].phase)<.26,'A reversal jumped between poses');
    report.positions.reversal=turn.map(f=>Number(f.phase.toFixed(4)));
    s.settle(3,0);near(s.pose(3).x,anchor[0]);near(s.pose(3).y,anchor[1]);
    report.checks.push('All four corners and bottom center reach the requested layout; custom coordinates retarget smoothly while open.',
        'Position leads size on opening and the same two curves retrace on closing; an in-flight outside press reverses continuously.');
    s.vm.stopAll();report.passed=true;
}
main().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));process.exit(report.passed?0:1);
});
