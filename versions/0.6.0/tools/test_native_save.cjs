#!/usr/bin/env node
/** Check what Scratch's actual serializer will write *after* the renderer has run. */
const fs=require('node:fs'), assert=require('node:assert/strict'), crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const {logicalGrid}=require('./test_grid_pixels.cjs');
const [file,output]=process.argv.slice(2);
if(!output)throw Error('Usage: node test_native_save.cjs Studio.sb3 report.json');
const report={sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),saves:[]};
(async()=>{
    const vm=await H.loadProject(file,{compiler:true});
    const get=name=>H.getVariable(vm,'Liquid Glass',name).value;
    let ticks=0;
    vm.runtime.ioDevices.clock._projectTimer.nowObj={now:()=>ticks*1000/30};
    vm.runtime.ioDevices.clock._projectTimer.startTime=0;
    const tick=(n=1)=>{for(let i=0;i<n;i++){ticks++;vm.runtime._step();}};
    const mouse=(x,y,down)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown:down});
    const click=(x,y)=>{mouse(x,y,true);tick(2);mouse(x,y,false);tick(28);};
    function rowPoint(path) {
        const i=get('UI row path').findIndex((p,i)=>p===path && Number(get('UI row id')[i])===3);
        assert.ok(i>=0,'Missing active row '+path);
        const idx=Number(get('UI row index')[i]),l=Number(get('UI row layer')[i])-1;
        const [x,y,h,pitch]=l<0?[get('x')[2],get('y')[2],Number(get('h')[2])*Number(get('scaleY')[2]),Number(get('h')[2])*Number(get('scaleY')[2])*Number(get('UI row height')[2])/Number(get('UI expanded height')[2])]:
            [get('UI layer x')[l],get('UI layer y')[l],get('UI layer h')[l],Number(get('UI layer h')[l])/(Number(get('UI layer rows')[l])+1)];
        return [Number(x),Number(y)+Number(h)/2-Number(pitch)*(idx+.5)];
    }
    function save(state) {
        const json=vm.toJSON(), bytes=Buffer.byteLength(json), doc=JSON.parse(json);
        const sprite=doc.targets.find(t=>t.name==='Liquid Glass');
        assert.ok(bytes<5e6,`Native save of ${state} exceeds 5 MB: ${bytes} bytes`);
        assert.deepEqual(doc.extensions,['pen']);
        const proto=Object.values(sprite.blocks).find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith('Menu %s '));
        const inputs=JSON.parse(proto.mutation.argumentnames);
        for(const name of ['tint color','transparency','brightness','blur','alignment','expanded x','expanded y'])assert.ok(inputs.includes(name),'Saved Menu missing input '+name);
        const lists=Object.fromEntries(Object.values(sprite.lists));
        assert.equal(lists['Original RGB'].length,172800);
        assert.equal(logicalGrid(lists['Grid RGB'],()=>lists['LG grid rows'],()=>lists['LG grid pixels']).length,172800);
        report.gridStoredRows=(lists['LG grid pixels']||lists['Grid RGB']).length/480;
        report.placementInputs=inputs.slice(inputs.indexOf('alignment')); 
        report.saves.push({state,projectJsonBytes:bytes});
        return json;
    }
    mouse(234,-162,false);vm.greenFlag();tick(6);save('running, launcher closed');
    const launcher=()=>[Number(get('x')[2]),Number(get('y')[2])];
    report.launcherCenter=launcher();
    const sidebarBlur=Number(get('matBlur')[0]);
    click(...launcher());assert.equal(Number(get('UI open')[2]),1);save('root menu open');
    click(...rowPoint('Background'));assert.equal(get('UI page')[2],'Background');
    const final=save('child menu open, parent retained');
    vm.stopAll();
    // Reopen the serialized block graph with its original local assets; verify startup.
    const Zip=H.libraries().JSZip;const zip=await Zip.loadAsync(fs.readFileSync(file));
    zip.file('project.json',final);
    await vm.loadProject(await zip.generateAsync({type:'nodebuffer'}));
    vm.greenFlag();tick(4);
    assert.equal(Number(get('UI open')[2]),0);
    assert.equal(get('UI label')[2],'Options');
    // Drive a visible demo finish all the way from its root row into its child.
    click(...launcher());click(...rowPoint('Menu finish'));click(...rowPoint('Menu finish>Smoked'));
    assert.equal(get('UI action'),'Menu finish>Smoked');
    assert.equal(get('Menu finish'),'Smoked');assert.equal(Number(get('UI open')[2]),0);
    assert.equal(Number(get('matBrightness')[2]),-.12);
    assert.equal(Number(get('matBlur')[2]),12);
    click(...launcher());click(...rowPoint('Menu finish'));click(...rowPoint('Menu finish>Clear'));
    assert.equal(get('UI action'),'Menu finish>Clear');
    assert.equal(Number(get('matAlpha')[2]),0);assert.equal(Number(get('matBlur')[2]),0);
    assert.equal(Number(get('matBlur')[0]),sidebarBlur,'A menu finish must not change the sidebar');
    report.demoFinishes=['Smoked','Clear'];
    vm.stopAll();report.passed=true;
})().catch(e=>{report.passed=false;report.error=String(e);process.exitCode=1;}).finally(()=>{
    fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));process.exit(process.exitCode||0);
});
