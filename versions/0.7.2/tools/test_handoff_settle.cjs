#!/usr/bin/env node
/** Verify actual native title/chevron marks on both sides of a collapsing row. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const [file,reportFile]=process.argv.slice(2);
if(!reportFile)throw Error('Usage: node test_handoff_settle.cjs Studio.sb3 report.json');
const report={project:file,sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),cases:[]};
const near=(a,b,eps=.09)=>assert.ok(Math.abs(a-b)<=eps,`${a} != ${b} ±${eps}`);
const items='First|Second|Work>Archive|Work>Zeta>One|Work>Zeta>Two';
async function fixture(){
    const {VM,Storage,JSZip}=H.libraries();
    const zip=await JSZip.loadAsync(fs.readFileSync(file)),doc=JSON.parse(await zip.file('project.json').async('string'));
    const sprite=doc.targets.find(t=>t.name==='Liquid Glass');
    const menu=Object.values(sprite.blocks).find(b=>b.opcode==='procedures_call'&&b.mutation.proccode.startsWith('Menu %s '));
    const proto=Object.values(sprite.blocks).find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode===menu.mutation.proccode);
    const names=JSON.parse(proto.mutation.argumentnames),ids=JSON.parse(proto.mutation.argumentids);
    // Clamp near the lower stage edge to give the shared text measurable travel.
    for(const [name,value] of Object.entries({x:165,y:-102,alignment:'bottom left',items,bounce:.47,'close growth':.64})){
        menu.inputs[ids[names.indexOf(name)]]=[1,[10,String(value)]];
    }
    zip.file('project.json',JSON.stringify(doc));
    const vm=new VM();vm.attachStorage(new Storage());await vm.loadProject(await zip.generateAsync({type:'nodebuffer'}));
    vm.setCompilerOptions({enabled:true});const target=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass');
    const state=new Map(Object.values(target.variables).map(v=>[v.name,v])),get=n=>state.get(n)?.value;
    const costume=()=>target.sprite.costumes[target.currentCostume]?.name||'';
    let frame=0,marks=[];
    function record(type,src,x,y,u,v,penAlpha){
        if(Number(get('UI art id'))!==3||penAlpha<.003)return;
        const rot=!!Number(get('UI rotating chevron'));
        if(!['UI glyph [W]','UI glyph [Z]','UI icon next'].includes(src))return;
        const layer=Number(get('UI draw layer')),ox=type==='stamp'?x:Number(get('UI letter world x')),
            oy=type==='stamp'?y:Number(get('UI letter world y'));
        marks.push({src,type,layer,ox,oy,x,y,u,v,rot,alpha:penAlpha,cos:Number(get('UI chevron cos')),sin:Number(get('UI chevron sin'))});
    }
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},pick:()=>-1,penClear(){},
        penPoint(_skin,a,x,y){if(a.color4f[0]>.92)record('point',costume(),x,y,x,y,a.color4f[3]);},
        penLine(_skin,a,x,y,u,v){if(a.color4f[0]>.92)record('line',costume(),x,y,u,v,a.color4f[3]);},
        penStamp(){
            const drawn=costume(),tile=drawn.startsWith('UI ink sample ');
            const src=tile?(target.sprite.costumes[Number(get('UI path index'))-1]?.name||''):drawn;
            record(tile?'tile':'stamp',src,target.x,target.y,target.x,target.y,1-Number(target.effects.ghost)/100);
        }};
    const timer=vm.runtime.ioDevices.clock._projectTimer;timer.nowObj={now:()=>frame*1000/30};timer.startTime=0;
    function tick(){frame++;marks=[];vm.runtime._step();return [...marks];}
    function mouse(x,y,isDown){vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});}
    function click(x,y){mouse(x,y,true);tick();tick();mouse(x,y,false);return tick();}
    function spin(count){for(let j=0;j<count;j++)tick();}
    function layer(path){const i=get('UI layer path').indexOf(path);if(i<0)return null;
        const at=(n,fallback=n)=>Number((get('UI layer '+n)??get('UI layer '+fallback))[i]);
        return {id:i+1,p:at('p'),v:at('v'),ip:at('ink p','p'),iv:at('ink v','v'),goal:at('goal'),
                x:at('x'),y:at('y'),h:at('h'),rows:at('rows')};}
    function row(path){
        const j=get('UI row path').findIndex((p,j)=>p===path&&Number(get('UI row id')[j])===3);
        assert.ok(j>=0,'Missing '+path);const i=Number(get('UI row layer')[j])-1,idx=Number(get('UI row index')[j]);
        const x=i<0?Number(get('x')[2]):Number(get('UI layer x')[i]);
        const y=i<0?Number(get('y')[2]):Number(get('UI layer y')[i]);
        const h=i<0?Number(get('h')[2])*get('scaleY')[2]:Number(get('UI layer h')[i]);
        const pitch=i<0?Number(get('UI row height')[2])*h/get('UI expanded height')[2]:h/(Number(get('UI layer rows')[i])+1);
        return [x,y+h/2-(idx+.5)*pitch];
    }
    function force(){state.get('displayedScene').value='capture title';return tick();}
    function open(path){click(...row(path));spin(85);assert.equal(layer(path)?.goal,1);near(layer(path).ip,1);return layer(path);}
    function startBack(path){const l=layer(path);return click(l.x,l.y+l.h/2-.5*l.h/(l.rows+1));}
    mouse(-225,156,false);vm.greenFlag();spin(6);state.get('Quality').value=4;click(Number(get('x')[2]),Number(get('y')[2]));spin(75);
    return {vm,tick,spin,force,row,open,startBack,click,layer,get,mouse};
}

function glyph(marks,glyph,expectedLayer){
    const draws=marks.filter(m=>m.src==='UI glyph ['+glyph+']');
    const runs=new Map(draws.map(m=>[[m.layer,m.ox,m.oy].join(':'),m]));
    assert.equal(runs.size,1,'Expected exactly one visible run of '+glyph);
    const run=[...runs.values()][0];assert.equal(run.layer,expectedLayer,'Wrong title owner');
    const arrows=marks.filter(m=>m.src==='UI icon next'&&m.rot&&m.layer===expectedLayer&&Math.abs(m.oy-run.oy)<.08);
    return {x:run.ox,y:run.oy,layer:run.layer,arrows};
}
function delta(a,b){return Math.hypot(a.x-b.x,a.y-b.y);}
function dotBeyond(candidate,source,open){
    const dx=open.x-source.x,dy=open.y-source.y,dist=Math.hypot(dx,dy);
    assert.ok(dist>4,'The stage-edge fixture must give the title visible travel');
    return -((candidate.x-source.x)*dx+(candidate.y-source.y)*dy)/dist;
}
function measure(s,path,letter,parent){
    const origin=glyph(s.force(),letter,parent);
    const opened=s.open(path),top=glyph(s.force(),letter,opened.id);
    const openAngle=top.arrows.find(a=>a.rot);assert.ok(openAngle);near(openAngle.sin,1,.001);
    s.startBack(path);
    const tail=[];
    let last=null,returned=null;
    for(let i=0;i<125;i++){
        const marks=s.tick(),l=s.layer(path);
        if(!marks.length)continue;
        const owns=!!(l&&(l.p>.001||l.ip!==0||l.iv!==0));
        const actual=glyph(marks,letter,owns?l.id:parent);
        if(owns){
            assert.ok(actual.arrows.length,'Missing physical carried disclosure');
            const arrow=actual.arrows[0];near(arrow.oy,actual.y);
            near(arrow.sin,Math.sin(Math.min(1,l.ip)*Math.PI/2),.001);
            last={x:actual.x,y:actual.y};
            if(l.p===0&&l.ip<0)tail.push({ink:l.ip,v:l.iv,x:actual.x,y:actual.y,arrow:[arrow.ox,arrow.oy],angle:90*l.ip,
                beyond:dotBeyond(actual,origin,top)});
        }else if(last){returned={x:actual.x,y:actual.y};break;}
    }
    assert.ok(tail.length>=3,'Title ownership ended at surface contact');
    const peak=tail.reduce((a,b)=>a.beyond>b.beyond?a:b);
    assert.ok(peak.beyond>.5,'The painted title did not visibly cross its source endpoint: '+JSON.stringify(peak));
    assert.ok(peak.angle<-.5,'The disclosure did not rotate through its source angle');
    assert.ok(returned,'Parent never recovered title ownership');
    assert.ok(delta(last,returned)<.22,'Discontinuous final title handoff');
    near(returned.x,origin.x,.2);near(returned.y,origin.y,.2);
    s.spin(5);assert.equal(s.layer(path),null);
    return {path,source:[origin.x,origin.y],opened:[top.x,top.y],physicalTailFrames:tail.length,peak,last,returned};
}

function interrupt(s){
    const l=s.open('Work');s.startBack('Work');
    for(let i=0;i<45&&!(s.layer('Work')?.ip<-.015);i++)s.tick();
    const before=s.layer('Work');assert.ok(before&&before.p===0&&before.ip<0);
    const src=s.row('Work');s.mouse(...src,true);s.tick();const held=s.layer('Work');s.mouse(...src,false);const event=s.tick();const again=s.layer('Work');
    assert.ok(again&&again.goal===1,'A tap on the visible source row did not reverse the return');
    assert.equal(again.id,l.id);assert.equal(s.get('UI layer path').filter(v=>v==='Work').length,1);
    assert.ok(again.ip<0&&Math.abs(again.ip-held.ip)<.12,'Retiring spring restarted at zero');
    if(event.length)glyph(event,'W',again.id);
    s.spin(80);near(s.layer('Work').ip,1);assert.equal(s.get('UI event number'),0);
    return {path:'Work',before,after:again};
}
(async()=>{const s=await fixture();
    report.cases.push(measure(s,'Work','W',0));
    const outer=s.open('Work');report.cases.push(measure(s,'Work>Zeta','Z',outer.id));
    s.startBack('Work');s.spin(85);report.interruption=interrupt(s);
    s.vm.stopAll();report.passed=true;
})().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.writeFileSync(reportFile,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));process.exit(report.passed?0:1);});
