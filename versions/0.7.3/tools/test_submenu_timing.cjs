#!/usr/bin/env node
/** Exercise public timing sockets through the native green-flag loop, including two levels of actual row navigation. */
const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const [project,out]=process.argv.slice(2);
if(!out)throw Error('Usage: node test_submenu_timing.cjs Studio.sb3 report.json');
const report={sha256:crypto.createHash('sha256').update(fs.readFileSync(project)).digest('hex'),checks:[],observations:{}};
const frame=1/30,owner=3,first='Tools',second='Tools>Data';
const timing=['open travel','open growth','close travel','close growth','bounce'];
const normal=[.42,1.18,1.25,.34,0];
function near(a,b,t,msg){assert.ok(Number.isFinite(a)&&Math.abs(a-b)<=t,`${msg}: ${a} vs ${b} (±${t})`);}
function criticallyDamped(seconds,duration){
    if(duration===0)return 1;
    const t=2*Math.PI*seconds/duration;return 1-(1+t)*Math.exp(-t);
}
async function fixture(){
    const {VM,Storage,JSZip}=H.libraries(),zip=await JSZip.loadAsync(fs.readFileSync(project));
    const doc=JSON.parse(await zip.file('project.json').async('string')),sprite=doc.targets.find(t=>t.name==='Liquid Glass');
    const all=Object.values(sprite.blocks);
    const proto=all.find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith('Menu %s '));
    const call=all.find(b=>b.opcode==='procedures_call'&&b.mutation.proccode===proto.mutation.proccode);
    const names=JSON.parse(proto.mutation.argumentnames),ids=JSON.parse(proto.mutation.argumentids);
    const setInput=(name,value)=>{const i=names.indexOf(name);assert.ok(i>=0,'Missing public socket '+name);call.inputs[ids[i]]=value;};
    for(const [k,v] of Object.entries({x:-110,y:115,width:42,height:38,launcher:'capsule',alignment:'custom',
        'expanded x':-28,'expanded y':50,'panel width':178,'row height':27,items:'Top|Tools>Data>Quartz|Tools>Data>Jade|Tools>Xray|Tools>Leaf|Exit',
        quality:4,drag:0,mode:'toggle'}))setInput(k,[1,[10,String(v)]]);
    for(const [i,key] of timing.entries()){
        const id='test submenu '+key;sprite.variables[id]=[id,normal[i]];
        setInput(key,[3,[12,id,id],[10,String(normal[i])]]);
    }
    zip.file('project.json',JSON.stringify(doc));
    const vm=new VM();vm.attachStorage(new Storage());vm.setCompilerOptions({enabled:true});
    await vm.loadProject(await zip.generateAsync({type:'nodebuffer'}));vm.setCompilerOptions({enabled:true});
    const target=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass'),vars=new Map(Object.values(target.variables).map(v=>[v.name,v]));
    const get=n=>vars.get(n)?.value,slot=n=>Number(get(n)[owner-1]);
    const bounds=new Map(),alphas=new Map();
    function watch(name,callback){
        const variable=vars.get(name);assert.ok(variable,'Missing observation '+name);
        let current=variable.value;
        Object.defineProperty(variable,'value',{configurable:true,get:()=>current,set:value=>{current=value;callback(value);}});
    }
    // Capture only the row and final endpoints the real sheet layout calculated;
    // the rendered center and size themselves are measured independently below.
    watch('UI sheet growth',()=>{
        const path=get('UI layer path')[Number(get('UI panel step'))-1];
        if(path)bounds.set(path,Object.fromEntries(['origin','finish'].map(k=>[k,Object.fromEntries(
            ['x','y','w','h'].map(a=>[a,Number(get('UI '+k+' '+a))]))])));
    });
    // This is the actual interior opacity appended to the private Pen commands.
    // A complete sheet has an interior sample even at the initial row dimensions.
    watch('UI pixel coverage',v=>{
        const path=get('UI layer path')[Number(get('UI raster pane'))-1];
        if(path)alphas.set(path,Math.max(alphas.get(path)||0,Number(v)));
    });
    let now=0;
    const clock=vm.runtime.ioDevices.clock._projectTimer;clock.nowObj={now:()=>now};clock.startTime=0;
    function tick(){now+=1000*frame;alphas.clear();vm.runtime._step();}
    const spin=n=>{for(let i=0;i<n;i++)tick();};
    const mouse=(x,y,isDown)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});
    const outside=()=>mouse(224,-159,false);
    function click(point){mouse(...point,true);tick();mouse(...point,false);tick();outside();}
    function layer(path){
        const i=get('UI layer path').indexOf(path);if(i<0)return null;
        const val=k=>Number(get('UI layer '+k)?.[i]);
        const x=val('x'),y=val('y'),w=val('w'),h=val('h');
        const {origin,finish}=bounds.get(path)||{};
        // A new record is copied from the row by UI input near the end of the
        // current frame. Its first layout pass occurs on the next display tick.
        if(!origin||!finish){
            near(val('p'),0,.0001,'Only a birth frame can lack sampled endpoints');
            return {id:i+1,goal:val('goal'),rows:val('rows'),travel:0,growth:0,x,y,w,h,alpha:0};
        }
        const dx=finish.x-origin.x,dy=finish.y-origin.y;
        const travelSpan=Math.hypot(dx,dy),growthSpan=finish.h-origin.h;
        assert.ok(travelSpan>20&&growthSpan>38,'Sheet travel and growth must be independently measurable for '+path);
        assert.ok(Math.abs(x)+w/2<=238.5&&Math.abs(y)+h/2<=178.5,'Unintended stage clamp in '+path);
        const travel=((x-origin.x)*dx+(y-origin.y)*dy)/(travelSpan**2),growth=(h-origin.h)/growthSpan;
        near(x,origin.x+travel*dx,.06,path+' center x lies on the actual row-to-sheet path');
        near(y,origin.y+travel*dy,.06,path+' center y lies on the actual row-to-sheet path');
        near(w,origin.w+growth*(finish.w-origin.w),.08,path+' width follows the same channel as height');
        return {id:i+1,path,goal:val('goal'),rows:val('rows'),travel,growth,travelSpan,growthSpan,
            ink:val('ink p'),inkVelocity:val('ink v'),travelVelocity:val('travel v'),
            x,y,w,h,alpha:alphas.get(path)??0,origin,finish};
    }
    function row(path){
        const j=get('UI row path').findIndex((p,i)=>p===path&&Number(get('UI row id')[i])===owner);
        assert.ok(j>=0,'Missing native row '+path);const id=Number(get('UI row layer')[j]),row=Number(get('UI row index')[j]);
        const parent=id?layer(get('UI layer path')[id-1]):null;
        const h=parent?parent.h:slot('h')*slot('scaleY'),w=parent?parent.w:slot('w')*slot('scaleX');
        const rh=slot('UI row height'),layoutH=parent?(parent.rows+1)*rh:slot('UI expanded height');
        const layoutW=parent?Math.min(440,slot('UI menu panel width')+8):slot('UI expanded width');
        return {x:(parent?parent.x:slot('x'))-w/layoutW,y:(parent?parent.y:slot('y'))+h/2-(row+.5)*rh*h/layoutH,
            h:(rh-8)*h/layoutH,w:(layoutW-10)*w/layoutW};
    }
    const header=l=>[l.x,l.y+l.h/2-l.h/(2*(l.rows+1))];
    function open(path){
        const r=row(path);bounds.delete(path);click([r.x,r.y]);const l=layer(path);
        assert.ok(l&&l.goal===1,'Click did not open '+path);
        near(l.x,r.x,.2,'New sheet starts at its calling row x');near(l.y,r.y,.2,'New sheet starts at its calling row y');
        near(l.w,r.w,.25,'New sheet starts at row width');near(l.h,r.h,.25,'New sheet starts at row height');
    }
    function back(path){const l=layer(path);click(header(l));assert.equal(layer(path)?.goal,0,'Back must retire exactly the selected layer');}
    function reset(times){
        bounds.clear();alphas.clear();times.forEach((v,i)=>{vars.get('test submenu '+timing[i]).value=v;});outside();vm.greenFlag();spin(5);
        vars.get('Quality').value=4;click([slot('x'),slot('y')]);spin(90);assert.equal(slot('UI open'),1);
    }
    function collection(path,n){const a=[];for(let i=0;i<n;i++){tick();a.push(layer(path));}return a;}
    return {vm,get,slot,reset,tick,spin,click,mouse,outside,open,back,row,layer,header,collection};
}
function checkTrack(track,secondsA,secondsB,opening,label){
    for(let i=0;i<track.length;i++){
        const item=track[i],seconds=(i+1)*frame;assert.ok(item,label+' retired before sample '+(i+1));
        const p=criticallyDamped(seconds,secondsA),q=criticallyDamped(seconds,secondsB);
        near(item.travel,opening?p:1-p,.025,label+' displayed position at '+seconds.toFixed(2)+' s');
        near(item.growth,opening?q:1-q,.025,label+' displayed height at '+seconds.toFixed(2)+' s');
        // The pressed source-row coat can contribute up to 15% of the remaining
        // opacity. Raw backdrop color is never used as an opacity surrogate.
        if(item.growth>.006){
            assert.ok(item.alpha>=item.growth-.035&&item.alpha<=item.growth+.15*(1-item.growth)+.035,
                label+' optical coverage '+item.alpha+' inconsistent with measured growth '+item.growth);
        }
    }
}
function short(p){return {x:p.x,y:p.y,w:p.w,h:p.h,travel:p.travel,growth:p.growth,alpha:p.alpha};}
async function main(){
    const s=await fixture();s.reset(normal);
    function cycle(path){
        s.open(path);const out=s.collection(path,6);checkTrack(out,normal[0],normal[1],true,path+' entering');
        s.spin(100);const settled=s.layer(path);near(settled.travel,1,.001,'settled center');near(settled.growth,1,.001,'settled size');
        s.back(path);const back=s.collection(path,6);checkTrack(back,normal[0],normal[1],false,path+' Back');
        out.forEach((p,i)=>{near(p.travel+back[i].travel,1,.035,'position reverses symmetrically');
            near(p.growth+back[i].growth,1,.035,'size reverses symmetrically');});
        report.observations[path]={open200ms:short(out[5]),back200ms:short(back[5])};
        s.spin(100);assert.equal(s.layer(path),null,'Back must retire '+path);assert.equal(s.slot('UI open'),1);
    }
    cycle(first);s.open(first);s.spin(100);cycle(second);
    assert.equal(s.layer(first)?.goal,1,'Grandchild Back must keep its parent open');
    report.checks.push('Source row, height, width, center and actual Pen coverage use independent opening springs; Back retraces those two channels at both depths.');
    // A partially-open top sheet and its settled ancestor should both take the
    // physical close durations when an outside press dismisses the whole stack.
    s.open(second);s.spin(5);const active=s.layer(second),top=s.layer(first);
    s.mouse(224,-159,true);s.tick();s.outside();s.tick();
    assert.equal(s.slot('UI open'),0);assert.equal(s.layer(second)?.goal,0);assert.equal(s.layer(first)?.goal,0);
    const start=s.layer(first),step=[];
    for(let i=0;i<5;i++){s.tick();step.push(s.layer(first));}
    checkTrack([start,...step],normal[2],normal[3],false,'whole-stack settled ancestor');
    const child=s.layer(second);
    assert.ok(child&&child.travel>child.growth+.28,'Partial descendant must follow fast close growth and slow close travel');
    report.observations.wholeDismiss={settledAncestor:short(step.at(-1)),partialDescendant:short(child),
        partialBefore:short(active),parentBefore:short(top)};
    s.spin(110);assert.equal(s.layer(first),null);assert.equal(s.layer(second),null);
    report.checks.push('An outside dismissal uses close travel/growth for a settled ancestor and a partially opened descendant instead of the Back durations.');
    // A leaf activation closes the same fully-open stack through a different
    // native entry point. All rows, including the deepest one, should return
    // with close timings even if the logical root is reopened during retreat.
    s.reset(normal);s.open(first);s.spin(100);s.open(second);s.spin(100);
    const leaf='Tools>Data>Quartz',hit=s.row(leaf),events=Number(s.get('UI event number'));
    s.click([hit.x,hit.y]);assert.equal(s.slot('UI open'),0);assert.equal(s.get('UI path'),leaf);
    assert.equal(Number(s.get('UI event number')),events+1);
    const closing=[[],[]];for(let i=0;i<6;i++){s.tick();closing[0].push(s.layer(first));closing[1].push(s.layer(second));}
    checkTrack(closing[0],normal[2],normal[3],false,'leaf dismissal ancestor');
    checkTrack(closing[1],normal[2],normal[3],false,'leaf dismissal descendant');
    report.observations.leafDismiss={ancestor200ms:short(closing[0][5]),descendant200ms:short(closing[1][5]),path:leaf};
    const rootY=s.slot('y')+s.slot('h')*s.slot('scaleY')/2-4;
    s.click([s.slot('x'),rootY]);assert.equal(s.slot('UI open'),1,'The launcher can be reopened while the old stack returns');
    const retreat=s.layer(second);assert.ok(retreat&&retreat.goal===0);
    s.tick();const resumed=s.layer(second);assert.ok(resumed&&resumed.goal===0);
    function criticalReturn(x,v,seconds){
        const omega=2*Math.PI/seconds;
        return (x+(v+omega*x)*frame)*Math.exp(-omega*frame);
    }
    near(resumed.travel,criticalReturn(retreat.travel,retreat.travelVelocity,normal[2]),.008,
        'A retreating sheet keeps its close-travel clock when the root reopens');
    near(resumed.growth,criticalReturn(retreat.growth,retreat.inkVelocity,normal[3]),.008,
        'A retreating sheet keeps its close-growth clock when the root reopens');
    report.checks.push('A leaf activation dismisses both settled levels; reopening the launcher does not switch those retiring sheets to Back timing.');
    // Zero travel and zero growth must not snap, hide or dispose the other lane.
    for(const [a,b,ct,cg] of [[0,1.1,0,1.1],[1.1,0,1.1,0]]){
        s.reset([a,b,ct,cg,0]);s.open(first);const [early]=s.collection(first,1);
        near(a===0?early.travel:early.growth,1,.002,'zero opening lane');
        assert.ok((a===0?early.growth:early.travel)<.08,'nonzero opening lane snapped');
        if(b===0)near(early.alpha,1,.025,'zero growth gives full optical opacity immediately');
        s.spin(100);s.back(first);const [returning]=s.collection(first,1);
        assert.ok(returning,'Independent return lane must survive the zero-duration lane');
        near(a===0?returning.travel:returning.growth,0,.002,'zero Back lane');
        assert.ok((a===0?returning.growth:returning.travel)>.92,'nonzero Back lane snapped');
        if(b===0)near(returning.alpha,0,.002,'zero growth removes the coat on Back');
        s.spin(100);s.open(first);s.spin(100);s.mouse(224,-159,true);s.tick();s.outside();s.tick();
        const closing=s.layer(first);assert.ok(closing,'Moving close lane must remain available until settlement');
        near(ct===0?closing.travel:closing.growth,0,.002,'zero whole-menu closing lane');
        assert.ok((ct===0?closing.growth:closing.travel)>.92,'nonzero dismiss lane snapped');
    }
    report.checks.push('Independent zero sockets snap only the corresponding position or size/opacity lane on opening, Back and true dismissal.');
    s.reset([1.0,1.25,.27,.35,.35]);s.open(first);s.spin(5);
    const before=s.layer(first);assert.ok(before.travel<.65&&before.growth<.55);
    s.back(first);const pivot=s.layer(first),after=s.collection(first,1)[0];
    assert.ok(pivot.travelVelocity>0&&pivot.inkVelocity>0);
    assert.ok(after.travel>pivot.travel&&after.growth>pivot.growth,
        'Changing direction must preserve each incoming signed velocity for the next displayed frame');
    const follow=s.collection(first,6);
    assert.ok(follow.some(p=>p&&p.travelVelocity<0&&p.inkVelocity<0),'Both interrupted springs must turn back');
    s.spin(100);assert.equal(s.layer(first),null);
    report.observations.interruption={before:short(before),pivot:short(pivot),after:short(after)};
    report.checks.push('A real Back press during entry preserves signed travel and growth velocities through reversal.');
    s.vm.stopAll();report.passed=true;
}
main().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));process.exit(report.passed?0:1);
});
