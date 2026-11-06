#!/usr/bin/env node
/** Observe physical native glyph/chevron marks and the actual native menu loop.
 * Run the shipped example and a copy of the same single Menu call at a stage
 * boundary. No renderer or menu implementation is stubbed.
 */
const assert=require('node:assert/strict');
const fs=require('node:fs'),crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const [archive,output]=process.argv.slice(2);
if(!output)throw Error('Usage: node test_menu_handoff.cjs Studio.sb3 results.json');
const report={sha256:crypto.createHash('sha256').update(fs.readFileSync(archive)).digest('hex'),scenes:[]};
const near=(v,e,epsilon=.09)=>assert.ok(Math.abs(v-e)<=epsilon,`${v} != ${e} (tolerance ${epsilon})`);
async function scene(atEdge){
    const {VM,Storage,JSZip}=H.libraries();const z=await JSZip.loadAsync(fs.readFileSync(archive));
    const doc=JSON.parse(await z.file('project.json').async('string')),sprite=doc.targets.find(t=>t.name==='Liquid Glass');
    const inset=Object.values(sprite.blocks).some(b=>b.opcode==='procedures_prototype'
        &&b.mutation.proccode.startsWith('UI inset menu highlight x '));
    if(atEdge){
        const call=Object.values(sprite.blocks).find(b=>b.opcode==='procedures_call'&&b.mutation.proccode.startsWith('Menu %s '));assert.ok(call);
        const proto=Object.values(sprite.blocks).find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode===call.mutation.proccode);
        const names=JSON.parse(proto.mutation.argumentnames),ids=JSON.parse(proto.mutation.argumentids);
        for(const [k,value] of [['x',211],['y',-148],['alignment','bottom right']])call.inputs[ids[names.indexOf(k)]]=[1,[typeof value==='number'?4:10,String(value)]];
        z.file('project.json',JSON.stringify(doc));
    }
    const vm=new VM();vm.attachStorage(new Storage());await vm.loadProject(await z.generateAsync({type:'nodebuffer'}));
    vm.setCompilerOptions({enabled:true});const target=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass');
    const vars=new Map(Object.values(target.variables).map(v=>[v.name,v])),get=k=>vars.get(k)?.value;
    let tickId=0,marks=[];
    function mark(kind,x,y,u=x,v=y){
        if(Number(get('UI art id'))!==3)return;
        const current=target.sprite.costumes[target.currentCostume]?.name||'';
        const tile=kind==='stamp'&&current.startsWith('UI ink sample ');
        const art=tile?target.sprite.costumes[Number(get('UI path index'))-1]?.name:current;
        if(tile&&1-Number(target.effects.ghost)/100<.003)return;
        if(!['UI glyph [M]','UI icon next','UI icon back'].includes(art))return;
        const layer=Number(get('UI draw layer')),rot=Number(get('UI rotating chevron'))===1;
        const ox=kind==='stamp'&&!tile?x:get('UI letter world x'),oy=kind==='stamp'&&!tile?y:get('UI letter world y');
        marks.push({art,layer,ox,oy,x,y,u,v,rot,p:layer?get('UI layer p')[layer-1]:0,
                    tile,kind,direction:target.direction,scaleX:get('UI ink scale x'),scaleY:get('UI ink scale y'),opacity:get('UI ink opacity')});
    }
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},pick:()=>-1,penClear(){},
        penPoint(_skin,a,x,y){if(a.color4f[0]>.9&&a.color4f[3]>.002)mark('pen',x,y)},
        penLine(_skin,a,x,y,u,v){if(a.color4f[0]>.9&&a.color4f[3]>.002)mark('pen',x,y,u,v)},
        penStamp(){mark('stamp',...H.inkStampCenter(target))}};
    const clock=vm.runtime.ioDevices.clock._projectTimer;clock.nowObj={now:()=>tickId*1000/30};clock.startTime=0;
    const mouse=(x,y,isDown)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});
    const tick=()=>{tickId++;marks=[];vm.runtime._step();return marks};
    const settle=n=>{for(let i=0;i<n;i++)tick()};
    const click=(x,y)=>{mouse(x,y,true);settle(2);mouse(x,y,false);tick()};
    const child=()=>{
        const i=get('UI layer path').indexOf('Menu finish');
        if(i<0)return null;
        const state=Object.fromEntries('x y w h r p goal'.split(' ').map(k=>[k,Number(get('UI layer '+k)[i])]));
        state.ink=Number(get('UI layer ink p')?.[i]??state.p);
        state.speed=Number(get('UI layer ink v')?.[i]??0);
        return state;
    };
    function row(){
        const at=get('UI row path').findIndex((p,i)=>p==='Menu finish'&&Number(get('UI row layer')[i])===0);assert.ok(at>=0);
        const sw=Number(get('w')[2])*Number(get('scaleX')[2]), sh=Number(get('h')[2])*Number(get('scaleY')[2]),pitch=Number(get('UI row height')[2]),
            sx=sw/Number(get('UI expanded width')[2]),sy=sh/Number(get('UI expanded height')[2]), idx=Number(get('UI row index')[at]);
        return {x:Number(get('x')[2])-(inset?sx:0),y:Number(get('y')[2])+sh/2-(idx+.5)*pitch*sy,
                w:sw-10*sx,h:(pitch-(inset?8:4))*sy,sx,sy};
    }
    mouse(-220,176,false);vm.greenFlag();settle(4);
    vars.get('Quality').value=4;
    click(Number(get('x')[2]),Number(get('y')[2]));settle(65);const initial=row();
    mouse(initial.x,initial.y,true);settle(2);
    const actual=row();mouse(actual.x,actual.y,false);const openingMark=tick();
    let birth=child();assert.ok(birth);near(birth.p,0,.0001);
    near(birth.x,actual.x);near(birth.y,actual.y);near(birth.w,actual.w);near(birth.h,actual.h);near(birth.r,Math.min(actual.w,actual.h)/2);
    let frames=[],seen=0;
    function observe(markList,phase){
        const layer=child();
        if(!markList.length)return;
        const titles=markList.filter(m=>m.art==='UI glyph [M]');
        const distinct=new Map(titles.map(m=>[[m.layer,m.ox,m.oy].join(','),m]));
        assert.equal(distinct.size,1,`A drawn frame emitted ${distinct.size} title runs during ${phase}`);
        const m=[...distinct.values()][0];
        const transferred=Boolean(layer&&(layer.p>.001||
            (vars.has('UI layer ink p')&&(layer.ink!==0||layer.speed!==0))));
        assert.equal(m.layer,transferred?1:0,'Title displayed by wrong face');
        if(!transferred)return;
        const arrows=markList.filter(a=>a.layer===1&&a.art==='UI icon next'&&a.rot&&(a.kind==='stamp'||Math.hypot(a.u-a.x,a.v-a.y)>0));
        assert.ok(arrows.length>=1,'The shared chevron produced no native marks');
        assert.ok(!markList.some(a=>a.layer===1&&a.art==='UI icon back'),'Old left back glyph was still painted');
        const arrow=arrows[0];near(arrow.oy,m.oy);assert.ok(arrow.ox>m.ox);
        const f=Math.min(1,layer.ink);
        // Original source asset d="M8 5l5 5-5 5", centered at (10,10).
        // Native stage Y points upward. Clockwise turn takes (+5,-5) to (-5,-5).
        const r=f*Math.PI/2,dx=(5*Math.cos(r)-5*Math.sin(r))*arrow.scaleX,
              dy=(-5*Math.cos(r)-5*Math.sin(r))*arrow.scaleY;
        if(arrow.kind==='stamp'&&!arrow.tile){
            // The native costume closely matches this almost-uniform transform.
            near(((arrow.direction-(90+90*f)+540)%360)-180,0,.07);
        }else if(!arrow.tile){
            assert.ok(arrows.length>=2,'Expected the original two chevron strokes');
            near(arrow.u-arrow.x,dx,.07);near(arrow.v-arrow.y,dy,.07);
            const last=arrows[1];
            near(last.u-last.x,(-5*Math.cos(r)-5*Math.sin(r))*last.scaleX,.07);
            near(last.v-last.y,(5*Math.sin(r)-5*Math.cos(r))*last.scaleY,.07);
        }else{
            // Check the emitted white tile footprint on both rotated arms,
            // not just the requested angle or the costume's source name.
            for(const [lx,ly] of [[-.75,3.75],[2.5,.5],[.5,-2.5],[-.75,-3.75]]){
                const x=arrow.ox+(lx*Math.cos(r)+ly*Math.sin(r))*arrow.scaleX,
                      y=arrow.oy+(-lx*Math.sin(r)+ly*Math.cos(r))*arrow.scaleY;
                assert.ok(arrows.some(dot=>Math.hypot(dot.x-x,dot.y-y)<1.3),
                    `No chevron tile on the expected arm at ${x},${y} (angle ${90*f})`);
            }
        }
        if(layer.p>.08&&layer.p<.93)seen++;
        frames.push({phase,p:layer.p,title:[m.ox,m.oy],arrow:[arrow.ox,arrow.oy],rotation:90*f});
    }
    observe(openingMark,'birth');
    for(let k=0;k<75;k++){const events=tick();observe(events,'open');}
    const open=child();near(open.p,1,.0001);assert.ok(frames.length>=3&&seen>0);
    const source=row(),expectedY=Math.max(-178+open.h/2,Math.min(178-open.h/2,source.y+source.h/2-open.h/2));
    near(open.y,expectedY,.22);assert.ok(open.x-open.w/2>=-240.001&&open.x+open.w/2<=240.001);
    const headerY=open.y+open.h/2-Number(get('UI row height')[2])/2;
    mouse(open.x,headerY,true);settle(2);mouse(open.x,headerY,false);tick();
    for(let k=0;k<80;k++)observe(tick(),'back');
    assert.equal(child(),null);assert.equal(Number(get('UI open')[2]),1);assert.equal(get('UI page')[2],'');
    assert.ok(frames.filter(f=>f.phase==='back'&&f.rotation>1&&f.rotation<89).length>=2);
    // Reverse twice before the first transition settles. A retiring sheet
    // keeps its record and optical pose when the same source row is tapped.
    let beforeReopen=null,reopened=null;
    if(!atEdge){
    settle(10);let r=row();click(r.x,r.y);
    for(let k=0;k<75&&(!child()||child().p<.43);k++)observe(tick(),'rapid opening');
    let mid=child();assert.ok(mid && mid.p<.99);
    const header=()=>{const z=child();return [z.x,z.y+z.h/2-.5*z.h/(Number(get('UI layer rows')[0])+1)]};
    const fixedHeader=header();mouse(...fixedHeader,true);observe(tick(),'rapid opening');mouse(...fixedHeader,false);observe(tick(),'rapid Back');
    assert.equal(child().goal,0,'A hit on the moving header did not reverse the sheet');
    observe(tick(),'rapid Back');r=row();mouse(r.x,r.y,true);observe(tick(),'rapid Back');
    beforeReopen=child();mouse(r.x,r.y,false);observe(tick(),'rapid reopen');
    reopened=child();assert.equal(reopened.goal,1);assert.equal(get('UI layer path').length,1);
    assert.ok(reopened.p>.01&&Math.abs(reopened.p-beforeReopen.p)<.35,'Reopening began a second title or restarted its spring');
    for(let k=0;k<55;k++)observe(tick(),'rapid reopen');
    near(child().p,1,.001);assert.equal(Number(get('UI event number')),0);
    }
    const result={atEdge,sourceAtPress:actual,birth,openingFirst:frames[0],open,beforeReopen,reopened,
        backIntermediate:frames.find(f=>f.phase==='back'&&f.rotation>1&&f.rotation<89),
        backOvershoot:frames.filter(f=>f.phase==='back'&&f.rotation<0).sort((a,b)=>a.rotation-b.rotation)[0]??null,
        frames:frames.length};
    vm.stopAll();return result;
}
Promise.resolve().then(async()=>{report.scenes.push(await scene(false),await scene(true));report.passed=true;})
.catch(e=>{report.passed=false;report.error=String(e.stack||e)}).finally(()=>{
    fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));process.exit(report.passed?0:1);
});
