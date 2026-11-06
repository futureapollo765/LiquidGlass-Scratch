#!/usr/bin/env node
const fs=require('node:fs'),crypto=require('node:crypto'),assert=require('node:assert/strict'),path=require('node:path');
const H=require('./vm_harness.cjs');
const file=process.argv[2]||'EditorVerified.sb3',output=process.argv[3]||'research/native_editor_runtime.json';
const report={project:path.resolve(file),sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),tests:[]};
(async()=>{
 const vm=await H.loadProject(file,{compiler:true});vm.setCompilerOptions({enabled:true});
 const errors=[];vm.on('COMPILE_ERROR',(...args)=>errors.push(args.map(String)));
 const value=n=>H.getVariable(vm,'Liquid Glass',n).value;
 let tickCount=0;vm.runtime.ioDevices.clock._projectTimer.nowObj={now:()=>tickCount*1000/30};
 const tick=(n=1)=>{for(let i=0;i<n;i++){tickCount++;vm.runtime._step();}};
 const check=(name,fn)=>{fn();report.tests.push({name,passed:true});};
 vm.greenFlag();tick(4);
 check('Native-editor saved project preserves all three distinct centers and renders repeatedly',()=>{
  assert.deepEqual(value('x').slice(0,3),[-90,85,20]);assert.deepEqual(value('y').slice(0,3),[10,10,-100]);assert.deepEqual(value('w').slice(0,3),[156,76,176]);assert.equal(value('Frames'),4);
 });
 report.initial={x:value('x').slice(0,3),y:value('y').slice(0,3),width:value('w').slice(0,3),height:value('h').slice(0,3)};
 check('Native-editor field samples are inside the separate components at their actual centers',()=>{
  const at=(x,y)=>value('field')[Math.round((value('top')-y)/value('q'))*value('cols')+Math.round((x-value('left'))/value('q'))];
  for(const [x,y]of[[-90,10],[85,10],[20,-100]])assert.ok(at(x,y)<-15,`field at ${x},${y}=${at(x,y)}`);
  report.centerFields=[at(-90,10),at(85,10),at(20,-100)];
 });
 vm.postIOData('keyboard',{key:'3',isDown:true});vm.postIOData('keyboard',{key:'3',isDown:false});tick(45);
 check('Native-editor preserved keyboard and forever loop change main shape to a circle',()=>{assert.equal(Number(value('Shape')),3);assert.ok(Math.abs(value('w')[0]-96)<.001);assert.ok(Math.abs(value('r')[0]-48)<.001);assert.equal(value('Frames'),49);});
 vm.stopAll();vm.setCompilerOptions({enabled:false});
 check('Native-editor geometry procedures also retain center subtraction in Scratch interpreter',()=>{
  for(const [id,x,y,r]of[[1,-90,10,48],[2,85,10,38],[3,20,-100,22]]){H.invoke(vm,'Liquid Glass','LG shape %s %s %s',[id,x,y]);assert.ok(Math.abs(value('sd')+r)<.001);}
 });
 assert.equal(errors.length,0);report.compilationErrors=errors;vm.stopAll();report.passed=true;
})().catch(e=>{report.passed=false;report.error=String(e);}).finally(()=>{fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));process.exit(report.passed?0:1);});
