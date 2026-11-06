/** Measure independent user timing sockets by observing the displayed menu in its green-flag loop. */
const assert=require('node:assert/strict'), fs=require('node:fs'), crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const [file,output]=process.argv.slice(2);
const report={sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),checks:[],samples:{}};
const inputs=['open travel','open growth','close travel','close growth','bounce'];
const near=(a,b,t,label)=>assert.ok(Math.abs(a-b)<=t,`${label}: ${a} vs ${b}`);
async function fixture(){
    const {VM,Storage,JSZip}=H.libraries(), zip=await JSZip.loadAsync(fs.readFileSync(file));
    const doc=JSON.parse(await zip.file('project.json').async('string'));
    const t=doc.targets.find(x=>x.name==='Liquid Glass');
    const proto=Object.values(t.blocks).find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith('Menu %s '));
    const argumentNames=JSON.parse(proto.mutation.argumentnames), ids=JSON.parse(proto.mutation.argumentids);
    const firstTiming=argumentNames.indexOf('open travel');
    assert.deepEqual(argumentNames.slice(firstTiming,firstTiming+inputs.length),inputs);
    const call=Object.values(t.blocks).find(b=>b.opcode==='procedures_call'&&b.mutation.proccode===proto.mutation.proccode);
    // Four timings are plugged into ordinary variable reporters so they can
    // change live without touching the private state of the animation.
    for(const [name,value] of Object.entries({x:-45,y:40,width:42,height:42,launcher:'circle','panel width':180,
              'row height':30,items:'A|B|C',alignment:'custom','expanded x':60,'expanded y':-15,quality:4})){
        call.inputs[ids[argumentNames.indexOf(name)]]=[1,[10,String(value)]];
    }
    for(const name of inputs){
        const key='timing-fixture-'+name;t.variables[key]=[key,0];
        call.inputs[ids[argumentNames.indexOf(name)]]=[3,[12,key,key],[10,'0']];
    }
    zip.file('project.json',JSON.stringify(doc));
    const vm=new VM();vm.attachStorage(new Storage());
    await vm.loadProject(await zip.generateAsync({type:'nodebuffer'}));
    vm.setCompilerOptions({enabled:true});
    const get=n=>H.getVariable(vm,'Liquid Glass',n);
    const set=(values)=>inputs.forEach((n,i)=>get('timing-fixture-'+n).value=values[i]);
    let now=0;
    vm.runtime.ioDevices.clock._projectTimer.nowObj={now:()=>now};
    const step=(ms=1000/30)=>{now+=ms;vm.runtime._step();};
    const mouse=(x,y,isDown)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});
    const pose=()=>({x:Number(get('x').value[2]),y:Number(get('y').value[2]),w:Number(get('w').value[2]),h:Number(get('h').value[2]),
        move:(Number(get('x').value[2])+45)/105,grow:(Number(get('h').value[2])-42)/78});
    function reset(values){set(values);mouse(230,-155,false);vm.greenFlag();for(let i=0;i<5;i++)step();}
    function toggle(open){const [x,y]=open?[-45,40]:[224,-156];mouse(x,y,true);step();mouse(x,y,false);step();mouse(230,-155,false);
        assert.equal(Number(get('UI open').value[2]),open?1:0);}
    return {vm,set,step,pose,reset,toggle};
}
function measure(f,open,ms,frames){
    f.toggle(open);const values=[];
    for(let i=1;i<=frames;i++){f.step(ms);values.push({seconds:i*ms/1000,...f.pose()});}
    return values;
}
(async()=>{
    const f=await fixture();
    f.reset([.32,1.15,1.15,.32,0]);
    const open=measure(f,true,1000/30,72);
    assert.ok(open[5].move>open[5].grow+.40);
    near(open.at(-1).move,1,.001,'resting location'); near(open.at(-1).grow,1,.002,'resting size');
    const close=measure(f,false,1000/30,72);
    assert.ok(close[5].move>close[5].grow+.40);
    report.samples.independent={open200ms:open[5],close200ms:close[5]};
    f.reset([1.15,.32,.32,1.15,0]);
    const swapOpen=measure(f,true,1000/30,72), swapClose=measure(f,false,1000/30,72);
    assert.ok(swapOpen[5].grow>swapOpen[5].move+.4);
    assert.ok(swapClose[5].grow>swapClose[5].move+.4);
    report.checks.push('Swapping the two opening and two closing times independently swaps which part leads.');
    f.reset([.52,.84,.72,.46,.30]);
    const sprung=measure(f,true,1000/30,70);
    const maxTravel=Math.max(...sprung.map(x=>x.move)),maxGrowth=Math.max(...sprung.map(x=>x.grow));
    assert.ok(maxTravel>1.015 && maxTravel<1.10 && maxGrowth>1.015 && maxGrowth<1.10);
    const closure=measure(f,false,1000/30,70);
    assert.ok(Math.min(...closure.map(x=>x.move))<-.01 && Math.min(...closure.map(x=>x.grow))<-.01);
    near(closure.at(-1).move,0,.0001,'closed location');near(closure.at(-1).grow,0,.0001,'closed size');
    report.samples.bounce={maxTravel,maxGrowth};
    report.checks.push('The default spring overshoots on both opening and closing, then settles back at the configured bounds.');
    f.reset([.52,.84,.72,.46,0]);
    const quiet=measure(f,true,1000/30,70);
    assert.ok(Math.max(...quiet.map(p=>p.move))<=1.00001 && Math.max(...quiet.map(p=>p.grow))<=1.00001);
    report.checks.push('Bounce zero reaches its target without overshoot.');
    f.reset([.52,.84,.72,.46,.30]);
    const small=measure(f,true,1000/30,6);
    f.reset([.52,.84,.72,.46,.30]);
    const large=measure(f,true,100,2);
    near(small.at(-1).move,large.at(-1).move,.013,'200 ms travel across 30/10 Hz');
    near(small.at(-1).grow,large.at(-1).grow,.023,'200 ms growth across 30/10 Hz');
    report.checks.push('The same elapsed wall time gives the same intermediate pose across 30 and 10 Hz VM steps.');
    f.reset([0,1.0,.9,0,0]);f.toggle(true);f.step();
    assert.ok(f.pose().move>.999 && f.pose().grow<.18);
    for(let i=0;i<65;i++)f.step();
    f.toggle(false);f.step();assert.ok(f.pose().move>.85 && Math.abs(f.pose().grow)<.005);
    report.checks.push('A zero duration snaps only the requested channel.');
    f.vm.stopAll();report.passed=true;
})().catch(e=>{report.error=String(e.stack||e);report.passed=false;}).finally(()=>{
    fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));process.exit(report.passed?0:1);
});
