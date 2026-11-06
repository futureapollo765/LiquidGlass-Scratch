/** Exercise both the private corner refraction field and the actual layered Pen image. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const crypto = require('node:crypto');
const H = require('./vm_harness.cjs');
const [previous, current, output] = process.argv.slice(2);
const report = {previousSHA256:digest(previous), sha256:digest(current), checks:[]};
function digest(path) {return crypto.createHash('sha256').update(fs.readFileSync(path)).digest('hex');}
const near=(a,b,tol)=>assert.ok(Math.abs(a-b)<=tol,`${a} differs from ${b} by more than ${tol}`);
async function probe(file) {
    const vm=await H.loadProject(file,{compiler:true}), name='Liquid Glass';
    const target=vm.runtime.targets.find(t=>t.getName()===name);
    const get=k=>H.getVariable(vm,name,k).value;
    const set=(k,v)=>{H.getVariable(vm,name,k).value=v;};
    const call=(code,...args)=>H.invoke(vm,name,code,args,{maxMilliseconds:90000});
    const pixels=new Map();
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},
        pick:()=>-1,penStamp(){},penPoint(){},penClear(){},
        penLine(s,a,x,y,u,v){if(y===v)pixels.set(`${(x+u)/2},${y}`,Array.from(a.color4f).slice(0,3).map(c=>Math.round(255*c)));}};
    call('LG initialize');set('UI view',1);set('Background',1);set('Original RGB',Array(172800).fill(0x8090a0));
    const proto=Object.values(target.blocks._blocks).find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith('Glass %s x '));
    const names=JSON.parse(proto.mutation.argumentnames), defaults=JSON.parse(proto.mutation.argumentdefaults);
    const args={id:3,x:0,y:0,width:210,height:100,shape:1,radius:16,reflection:.50,distortion:0,edge:0,highlight:0,tint:0,join:0,group:0,transition:0,
        drag:0,quality:1,'tint color':'#FFFFFF',transparency:100,brightness:0,blur:0};
    call(proto.mutation.proccode,...names.map((n,i)=>args[n]??defaults[i]));
    call('LG advance');
    for(const [n,value] of Object.entries({'UI live':1,'UI kind':'Menu','UI label':'','UI open':1,'UI page':'Child','UI row height':28,
        'UI menu open fade':1,'UI menu dim':1,'UI root page fade':1}))get(n)[2]=value;
    const record={owner:3,path:'Child',parent:'',row:1,p:1,v:0,goal:1,x:0,y:-45,w:150,h:78,r:12,rows:0,pitch:28,offset:0,dim:0,fade:1,'next offset':-1,strokes:0};
    for(const [k,value] of Object.entries(record))set('UI layer '+k,[value]);
    call('LG render');
    const strip=[-56,-54,-52,-50,-48,-46,-44].map(y=>({y,rgb:pixels.get('20,'+y)}));
    for (const sample of strip) assert.ok(sample.rgb,'Missing a real Pen pixel in the child');
    const exposedParent=pixels.get('20,25'); assert.ok(exposedParent);
    get('distortion')[2]=1;set('UI lens band',32);set('UI private q',1);set('frameBG',1);
    const shade=(x,y)=>{
        call('UI layer rounded shade %s x %s y %s',1,x,y);
        return [get('UI source x'),get('UI source y'),get('UI pixel coverage')];
    };
    // Both points are well inside a corner. In the old optical normal this is
    // the exact point at which the "nearest side" flipped from X to Y.
    const jump=[];
    for(const u of [-1,1])for(const v of [-1,1]) {
        const x=u*(75-12-2), y=-45+v*(39-12-2);
        const a=shade(x,y-v*.01),b=shade(x,y+v*.01);
        jump.push(Math.hypot(a[0]-b[0],a[1]-b[1]));
    }
    // Exact rounded-box coverage and an unbroken rim all the way into each flat side.
    const coverage=[];
    for(const u of [-1,1])for(const v of [-1,1])for(const degrees of [0,15,30,45,60,75,90]) {
        const theta=degrees*Math.PI/180;
        const x=u*(75-12+12*Math.cos(theta)), y=-45+v*(39-12+12*Math.sin(theta));
        coverage.push(shade(x,y)[2]);
    }
    vm.stopAll();return {jump,strip,exposedParent,coverage};
}
(async()=>{
    const old=await probe(previous),fresh=await probe(current);
    assert.ok(Math.min(...old.jump)>10,'Original corner switch was not reproduced');
    assert.ok(Math.max(...fresh.jump)<.15,'A 0.02-pixel move crossed a discontinuity in the new optical map');
    report.checks.push('All four private corners refract continuously across the nearest-side boundary');
    assert.ok(old.strip.some(s=>s.rgb[0]<120),'Original dimming cutoff was not reproduced');
    for(const s of fresh.strip)for(const [i,v] of [128,144,160].entries()) near(s.rgb[i],v,1);
    assert.ok(fresh.exposedParent[0]<115,'The exposed parent should remain dimmed');
    report.checks.push('A clear child has continuous color across the back panel edge while the exposed parent still dims');
    for(const a of fresh.coverage)near(a,.5,1e-6);
    report.checks.push('All 28 samples along the four arcs and their tangent endpoints retain half coverage');
    report.previous=old;report.current=fresh;report.passed=true;
})().catch(e=>{report.error=String(e.stack||e);report.passed=false;}).finally(()=>{
    fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({passed:report.passed,error:report.error,oldJump:report.previous?.jump,newJump:report.current?.jump}));
    process.exit(report.passed?0:1);
});
