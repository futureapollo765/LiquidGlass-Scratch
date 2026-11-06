#!/usr/bin/env node
/** Exercise signed pulls and reversals with the real mouse, layout and Pen runner. */
const assert=require('node:assert/strict'), crypto=require('node:crypto'), fs=require('node:fs');
const H=require('./vm_harness.cjs');
const [file,out]=process.argv.slice(2);
if(require.main===module && !out)throw Error('Usage: node test_stretch_gesture.cjs Studio.sb3 report.json');
const report={sha256:require.main===module?crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'):null,checks:[],observations:[]};
const near=(actual,expected,tolerance=.04)=>assert.ok(Math.abs(actual-expected)<=tolerance,
    'Expected '+actual+' within '+tolerance+' of '+expected);
const LG='Liquid Glass',shapeVariable='fixture button shape';
const positions={2:[0,-66],3:[0,78]};

async function scene(compiler,{filename=file,bounce}={}){
    const {VM,Storage,JSZip}=H.libraries(),zip=await JSZip.loadAsync(fs.readFileSync(filename));
    const doc=JSON.parse(await zip.file('project.json').async('string'));
    const target=doc.targets.find(t=>t.name===LG),all=Object.values(target.blocks);
    target.variables[shapeVariable]=[shapeVariable,'capsule'];
    for(const [kind,args] of [
        ['Button',{x:0,y:-66,width:132,height:44,label:'',shape:'capsule',pull:1,join:0,quality:4}],
        ['Menu',{x:0,y:78,width:124,height:40,label:'',launcher:'capsule',drag:1,pull:1,join:0,quality:4,...(bounce===undefined?{}:{bounce})}],
        ['Background',{x:-160,y:0,width:28,height:32,label:'',quality:4}],
    ]){
        const proto=all.find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith(kind+' %s '));
        const names=JSON.parse(proto.mutation.argumentnames),ids=JSON.parse(proto.mutation.argumentids);
        const calls=all.filter(b=>b.opcode==='procedures_call'&&b.mutation.proccode===proto.mutation.proccode);
        assert.equal(calls.length,1,'Expected a configurable Studio '+kind+' example');
        for(const [name,val] of Object.entries(args)){
            const id=ids[names.indexOf(name)];assert.ok(id,'Missing '+kind+' '+name);
            calls[0].inputs[id]=kind==='Button'&&name==='shape'?
                [3,[12,shapeVariable,shapeVariable],[10,'capsule']]:[1,[10,String(val)]];
        }
    }
    zip.file('project.json',JSON.stringify(doc));
    const vm=new VM();vm.attachStorage(new Storage());await vm.loadProject(await zip.generateAsync({type:'nodebuffer'}));
    vm.setCompilerOptions({enabled:compiler});
    const sprite=vm.runtime.targets.find(t=>t.getName()===LG);
    const variable=n=>H.getVariable(vm,LG,n), get=n=>variable(n).value;
    const item=(n,id)=>Number(get(n)[id-1]);
    const pose=id=>{
        const x=item('x',id),y=item('y',id),sx=item('scaleX',id),sy=item('scaleY',id);
        const w=item('w',id)*sx,h=item('h',id)*sy;
        return {x,y,sx,sy,w,h,left:x-w/2,right:x+w/2,bottom:y-h/2,top:y+h/2};
    };
    let current=[],lastPaint=[],ms=0;
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},pick:()=>-1,
        penClear(){},penStamp(){},penPoint(){},penLine(_,a,x,y,u,v){
            if(y===v&&a.diameter>=3&&a.color4f[3]>.5)
                current.push({x:(x+u)/2,y});
        }};
    const timer=vm.runtime.ioDevices.clock._projectTimer;timer.nowObj={now:()=>ms};timer.startTime=0;
    const mouse=(x,y,isDown)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});
    function frame(n=1,stepMilliseconds=1000/30){
        const limit=Date.now()+90000;
        for(let i=0;i<n;i++){
            const before=Number(get('Frames'));current=[];
            do{ms+=stepMilliseconds;vm.runtime._step();if(Date.now()>limit)throw Error('Native frame timed out');}
            while(Number(get('Frames'))===before);
            if(current.length)lastPaint=current;
        }
    }
    function painted(p){
        const probe=lastPaint.filter(s=>Math.abs(s.y-p.y)<=2.6&&Math.abs(s.x-p.x)<=p.w/2+5);
        assert.ok(probe.length>=4,'Expected native Pen strokes across this component centerline');
        const first=Math.min(...probe.map(s=>s.x)),last=Math.max(...probe.map(s=>s.x));
        near(first,p.left,5.25);near(last,p.right,5.25);
        return [first,last];
    }
    mouse(220,-158,false);vm.greenFlag();frame(5);
    return {vm,mouse,frame,pose,painted,get,shape(v){variable(shapeVariable).value=v;}};
}
function sweep(s,id,axis,sign,deltas,inspectPen){
    const [x,y]=positions[id],i=axis==='x'?0:1;
    s.mouse(220,-158,false);s.frame(5);
    const resting=s.pose(id),down=[x,y];
    down[i]-=sign*(i===0?resting.w:resting.h)*.32;
    // Hold still long enough to establish the full pressed silhouette.
    s.mouse(...down,false);s.frame(3);s.mouse(...down,true);s.frame(16);
    assert.equal(Number(s.get('UI pressed id')),id);
    const base=s.pose(id),event=Number(s.get('UI event number'));
    let prev=base,prior=0,peak=0,firstPaint,lastPaint;
    for(const d of deltas){
        const point=[...down];point[i]+=sign*d;s.mouse(...point,true);s.frame();
        const p=s.pose(id),size=i===0?p.w:p.h,baseline=i===0?base.w:base.h;
        const low=i===0?'left':'bottom',high=i===0?'right':'top';
        const direction=Math.sign(sign*(d-prior));
        assert.ok(size>=baseline-.08,'Travel shrank the pressed body');
        assert.ok(size>=(i===0?resting.w:resting.h)-.08,'Travel shrank the resting body');
        assert.ok((p[low]-prev[low])*direction>=-.10&&(p[high]-prev[high])*direction>=-.10,
            'Both borders must travel with the pointer on '+axis+' reversal: '+JSON.stringify({d,prior,prev,p}));
        near(i===0?p.sy:p.sx,1,.0001);
        if(Math.abs(d)>=40)peak=Math.max(peak,size);
        if(peak&&Math.abs(d)<=15)assert.ok(size>=peak-.16,'Crossing the press point collapsed the stretched width');
        if(inspectPen&&i===0){
            const range=s.painted(p);if(!firstPaint)firstPaint=range;lastPaint=range;
        }
        prev=p;prior=d;
    }
    assert.ok(peak>(i===0?base.w:base.h)+4);
    const last=[...down];last[i]+=sign*deltas.at(-1);s.mouse(...last,false);s.frame(33);
    s.mouse(220,-158,false);s.frame(12);
    const ended=s.pose(id);near(ended.x,x);near(ended.y,y);near(ended.sx,1);near(ended.sy,1);
    near(ended.w,resting.w,.19);near(ended.h,resting.h,.19);
    assert.equal(Number(s.get('UI event number')),event);assert.equal(Number(s.get('UI open')[2]),0);
    report.observations.push({id,axis,sign,pressed:i===0?base.w:base.h,peak,firstPaint,lastPaint});
}
function diagonal(s,id){
    const [x,y]=positions[id];s.mouse(x,y,true);s.frame(12);
    s.mouse(x+58,y+46,true);s.frame(3);const first=s.pose(id);
    assert.ok(first.sx>1.02&&first.sy>1.02);
    s.mouse(x+12,y+77,true);s.frame();const second=s.pose(id);
    assert.ok(second.left<first.left&&second.right<first.right&&second.bottom>first.bottom&&second.top>first.top);
    assert.ok(second.sx>=first.sx-.001&&second.sy>=first.sy-.001);
    s.mouse(x-45,y-38,true);s.frame();const third=s.pose(id);
    assert.ok(third.sx>=first.sx-.001&&third.sy>=second.sy-.001);
    s.mouse(x-45,y-38,false);s.frame(40);near(s.pose(id).x,x);near(s.pose(id).y,y);
}
function stepAndReverse(s,id,sign){
    const [x,y]=positions[id];
    // Start from a fully settled press so all observed width changes are the
    // grip response, not the button's separate hover/press size animation.
    function press(){
        s.mouse(x,y,false);s.frame(6);s.mouse(x,y,true);s.frame(20);
        return s.pose(id);
    }
    function sample(distance){
        s.mouse(x+sign*distance,y,true);s.frame();return s.pose(id);
    }
    function finish(){
        s.mouse(x,y,false);s.frame(60);s.mouse(220,-158,false);s.frame(8);
        near(s.pose(id).x,x);near(s.pose(id).sx,1);
    }
    const signed=p=>sign*(p.x-x);
    const bounds=(p,q,d)=>{
        assert.ok((q.left-p.left)*d>=-.06 && (q.right-p.right)*d>=-.06,
            'Painted borders moved against a directional step');
    };
    const base=press(),first=sample(96),second=sample(96);
    const ideal=28*(.65*96)/(28+.65*96);
    assert.ok(signed(first)>0 && signed(first)<ideal*.94,'First large sample snapped to the ideal pose');
    assert.ok(signed(second)>signed(first)+.1 && signed(second)<ideal);
    assert.ok(second.w>=first.w && first.w>base.w);
    bounds(base,first,sign);bounds(first,second,sign);
    s.frame(19);const held=s.pose(id);near(signed(held),ideal,.04);
    finish();
    press();const interrupted=sample(96),reverse=sample(84),catchup=sample(84);
    // The new absolute target is still ahead of the lagging center. The
    // pointer nevertheless moved back. Its old-direction residual must end
    // now and must not restart on the next stationary sample.
    assert.ok(signed(reverse)<signed(interrupted)-.12);
    assert.ok(signed(catchup)<signed(reverse)-.02);
    bounds(interrupted,reverse,-sign);bounds(reverse,catchup,-sign);
    const through=sample(-64);
    assert.ok(signed(through)<signed(catchup));
    bounds(catchup,through,-sign);
    assert.ok(through.w>=interrupted.w-.05,'Peak stretch squeezed away at the press point');
    s.frame(12);const across=s.pose(id);
    const back=sample(-50);bounds(across,back,sign);
    assert.ok(signed(back)>signed(across)+.05 && back.w>=across.w-.05);
    finish();
    (report.stepResponse ||= []).push({id,sign,ideal,first:signed(first),second:signed(second),
        held:signed(held),interrupted:signed(interrupted),reverse:signed(reverse),reverseHeld:signed(catchup),
        widthAtReversal:interrupted.w,widthAcrossOrigin:through.w});
}
async function main(){
    const s=await scene(true),path=[18,52,94,121,85,47,12,0,-15,-58,-85,-39,0,32];
    for(const [id,shape] of [[2,'capsule'],[2,'circle'],[2,'rectangle'],[3,'capsule']]){
        s.shape(shape);s.frame(35);
        sweep(s,id,'x',1,path,true);sweep(s,id,'x',-1,path,true);
        sweep(s,id,'y',1,[16,44,72,46,12,0,-30,-55,-15,0,18],false);
        diagonal(s,id);
    }
    for(const id of [2,3])for(const sign of [-1,1])stepAndReverse(s,id,sign);
    s.vm.stopAll();
    const interpreted=await scene(false);
    sweep(interpreted,2,'x',1,[32,78,105,64,12,0,-38,0],true);stepAndReverse(interpreted,2,1);interpreted.vm.stopAll();
    report.checks.push('Capsule, circular and rectangular Buttons and a capsule Menu follow both signs of cursor travel.',
        'Both contour borders travel with the cursor at every reversal; crossing the press point preserves the largest width.',
        'Pure horizontal/vertical gestures leave the other stretch at one; diagonals stretch both axes independently.',
        'Gesture release returns to the configured center and size and suppresses clicks and menu opening.',
        'Native Pen centerline endpoints follow computed glass edges in compiled and interpreted Scratch execution.',
        'A large held pointer step is followed over multiple renders until the bounded contact displacement settles.',
        'An early reversal redirects both edges immediately even when the new absolute target remains ahead; holding that pointer sample continues in the new direction.');
    report.passed=true;
}
module.exports={scene};
if(require.main===module)main().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,error:report.error}));process.exit(report.passed?0:1);
});
