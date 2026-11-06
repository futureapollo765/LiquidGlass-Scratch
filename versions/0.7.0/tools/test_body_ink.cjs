#!/usr/bin/env node
/** Real green-flag loop with one editable Menu call changed to a circle.
 * The stationary demo button and sidebar keep their original calls.
 * Follow the circle's icon through the root crossfade and locate a child row's
 * actual Pen marks throughout its independent world-space animation.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const [file,output]=process.argv.slice(2);
if(!output)throw Error('Usage: node test_body_ink.cjs Studio.sb3 report.json');
const report={sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),checks:[]};
const near=(v,expected,t=.05)=>assert.ok(Math.abs(v-expected)<=t,`${v} differs from ${expected}`);
async function run(){
    const {VM,Storage,JSZip}=H.libraries(),z=await JSZip.loadAsync(fs.readFileSync(file));
    const project=JSON.parse(await z.file('project.json').async('string')),source=project.targets.find(t=>t.name==='Liquid Glass');
    let modified=0;
    for(const b of Object.values(source.blocks)){
        if(b.opcode!=='procedures_call'||!b.mutation.proccode.startsWith('Menu %s '))continue;
        const arg=JSON.parse(b.mutation.argumentids);
        if(b.inputs[arg[3]]?.[1]?.[1]==='Options'){b.inputs[arg[4]]=[1,[10,'circle']];modified++;}
    }
    assert.equal(modified,1);
    z.file('project.json',JSON.stringify(project));
    const vm=new VM();vm.attachStorage(new Storage());await vm.loadProject(await z.generateAsync({type:'nodebuffer'}));
    vm.setCompilerOptions({enabled:true});
    const sprite=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass');
    const vars=new Map(Object.values(sprite.variables).map(v=>[v.name,v]));
    const get=name=>vars.get(name)?.value;
    let ticks=0,events=[];
    function mark(x,y,kind) {
        const art=sprite.sprite.costumes[sprite.currentCostume]?.name;
        if(!/^UI (icon (more|down|up)|glyph \[(O|G)\])$/.test(art)||Number(get('UI art id'))!==3)return;
        const layer=Number(get('UI draw layer'));
        const pitch=Number(get('UI ink row step'));
        const sizeX=Number(get('UI ink scale x')),sizeY=Number(get('UI ink scale y'));
        const ox=kind==='stamp'?x:Number(get('UI letter world x')),oy=kind==='stamp'?y:Number(get('UI letter world y'));
        const key=[ticks,layer,art,ox,oy].join(',');
        if(events.length && events.at(-1).key===key)return;
        events.push({key,kind,art,layer,ox,oy,pitch,sizeX,sizeY,cx:Number(get('UI cx')),cy:Number(get('UI cy')),
            w:Number(get('UI width')),h:Number(get('UI height')),opacity:Number(get('UI ink opacity')),
            rowCount:get('UI layer rows')[layer-1]??0});
    }
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},pick:()=>-1,penClear(){},
        penPoint(_skin,a,x,y){if(a.color4f[0]>.9&&a.color4f[3]>.001)mark(x,y,'pen');},
        penLine(_skin,a,x,y){if(a.color4f[0]>.9&&a.color4f[3]>.001)mark(x,y,'pen');},
        penStamp(){mark(sprite.x,sprite.y,'stamp')}};
    vm.runtime.ioDevices.clock._projectTimer.nowObj={now:()=>ticks*1000/30};vm.runtime.ioDevices.clock._projectTimer.startTime=0;
    const tick=(n=1)=>{for(let i=0;i<n;i++){ticks++;vm.runtime._step();}};
    const mouse=(x,y,isDown)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});
    const click=(x,y)=>{mouse(x,y,true);tick(2);mouse(x,y,false);tick(26)};
    mouse(210,-152,false);vm.greenFlag();tick(5);
    assert.ok(events.some(e=>e.art==='UI icon more'&&e.opacity>.99));
    assert.ok(!events.some(e=>e.art==='UI glyph [O]'||e.art==='UI icon down'));
    report.checks.push('A circular closed launcher displays its own ellipsis.');
    events=[];click(60,102);
    const inflight=events.filter(e=>e.opacity>.03&&e.opacity<.97&&e.layer===0);
    assert.ok(inflight.some(e=>e.art==='UI icon more'&&e.kind==='pen'),'Growing circle lost its own source artwork');
    assert.ok(inflight.some(e=>e.art==='UI glyph [O]'&&e.kind==='pen'),'Incoming root heading never visibly scaled');
    assert.ok(!inflight.some(e=>e.art==='UI icon down'),'Circular launcher changed to the rectangular chevron during flight');
    for(const e of inflight.filter(e=>e.art==='UI icon more')){near(e.ox,e.cx);near(e.oy,e.cy);}
    report.checks.push('Circular launcher ink follows its center, shrinks or stretches with both body axes, and crossfades into the heading.');
    const rootX=get('x')[2],rootY=get('y')[2],rootH=get('h')[2],rowH=get('UI row height')[2];
    events=[];click(rootX,rootY+rootH/2-1.5*rowH);
    assert.equal(get('UI page')[2],'Background');
    const grid=events.filter(e=>e.art==='UI glyph [G]'&&e.layer>0&&e.opacity>.02);
    assert.ok(grid.length>3&&grid.some(e=>e.kind==='pen'&&e.opacity<.9));
    for(const e of grid){
        near(e.ox,e.cx+(-e.w/2+14)*e.sizeX);
        near(e.oy,e.cy+(e.h/2-2.5*e.pitch)*e.sizeY);
    }
    assert.ok(grid.some(e=>e.sizeY<.8),'Did not observe an early stretched child row');
    report.checks.push('The first visible letter of Grid remains on its transformed row throughout growth of the private child; its curves are painted at the same pose.');
    report.observations={intermediateCircleFrames:new Set(inflight.map(e=>e.key.split(',')[0])).size,
        firstVisibleChildRow:grid[0],settledChildRow:grid.at(-1)};
    vm.stopAll();report.passed=true;
}
run().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));process.exit(report.passed?0:1);
});
