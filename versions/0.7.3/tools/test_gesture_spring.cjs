#!/usr/bin/env node
/** Drive real controls and compare displayed release motion to an independent spring solution. */
const assert=require('node:assert/strict'),fs=require('node:fs'),crypto=require('node:crypto');
const {scene}=require('./test_stretch_gesture.cjs');
const [project,output,baseline]=process.argv.slice(2);
if(!output)throw Error('Usage: node test_gesture_spring.cjs Studio.sb3 report.json [baseline.sb3]');
const hash=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const report={sha256:hash(project),checks:[],observations:{},baseline:baseline?hash(baseline):undefined};
function near(a,b,t=.015){assert.ok(Math.abs(a-b)<=t,`${a} differs from ${b} by more than ${t}`);}
function spring(position,velocity,seconds,bounce,elapsed){
    const omega=2*Math.PI/seconds,zeta=1-bounce,k=zeta*omega;
    const omegaD=omega*Math.sqrt(1-zeta*zeta),sn=omegaD?Math.sin(omegaD*elapsed)/omegaD:elapsed;
    const cs=omegaD?Math.cos(omegaD*elapsed):1,decay=Math.exp(-k*elapsed);
    return [(position*cs+(velocity+k*position)*sn)*decay,
        (velocity*cs-(k*velocity+omega*omega*position)*sn)*decay];
}
function state(s,id){
    const lane=n=>Number(s.get(n)[id-1]),p=s.pose(id);
    return {x:p.x,y:p.y,w:p.w,h:p.h,contact:lane('UI contact x'),velocity:lane('UI contact velocity x'),
        reach:lane('UI grip reach x'),stretchVelocity:lane('UI reach velocity x'),sx:p.sx,
        lift:lane('UI surface lift'),liftVelocity:lane('UI surface velocity'),dt:lane('UI grip seconds'),bounce:lane('UI grip bounce')};
}
const yFor=id=>id===2?-66:78;
function press(s,id){
    const y=yFor(id);s.mouse(220,-158,false);s.frame(12);
    s.mouse(-14,y,false);s.frame(20);s.mouse(-14,y,true);s.frame(25);
    assert.equal(Number(s.get('UI pressed id')),id);
}
function throwGrip(s,id,step=1000/30){
    press(s,id);
    s.mouse(88,yFor(id),true);s.frame(1,step);
    const first=state(s,id);s.frame(1,step);const held=state(s,id);
    assert.ok(first.contact>0&&held.contact>first.contact&&held.velocity>10&&held.stretchVelocity>10);
    s.mouse(88,yFor(id),false);s.frame(1,step);const release=state(s,id);
    for(const key of ['x','y','reach','velocity','stretchVelocity','sx'])near(release[key],held[key],.001);
    const frames=[];for(let i=0;i<35;i++){s.frame(1,step);frames.push(state(s,id));}
    return {held,release,frames};
}
function verifyThrow(s,id,track){
    const {held,release,frames}=track;
    assert.ok(release.contact>4,'Release must start away from the resting anchor.');
    let time=0;
    for(const p of frames.slice(0,12)){
        time+=p.dt;
        const [center,velocity]=spring(release.contact,release.velocity,.36,release.bounce,time);
        const [reach,stretchVelocity]=spring(release.reach,release.stretchVelocity,.36,release.bounce,time);
        near(p.contact,center,.002);near(p.velocity,velocity,.015);
        near(p.reach,reach,.002);near(p.stretchVelocity,stretchVelocity,.015);
        near(p.x,center,.02);
        // The public shape's actual width contains both the pose lift and signed extension.
        near(p.w,Number(s.get('UI resting width')[id-1])*(1+p.lift)+1.35*p.reach,.08);
    }
    assert.ok(frames.some(f=>f.x<-.3&&f.sx<.995),'Expected visible spring overshoot in the center and contour');
    assert.ok(frames.some(f=>f.x>0&&f.velocity<0),'Expected the center to turn back toward its anchor');
    const observed=frames.map(f=>f.x);
    return {heldX:held.x,releaseX:release.x,releaseVelocity:release.velocity,minX:Math.min(...observed),
        minScaleX:Math.min(...frames.map(f=>f.sx)),afterOneThird:frames[9].x};
}
async function main(){
    if(baseline){
        const s=await scene(true,{filename:baseline});
        press(s,3);s.mouse(88,78,true);s.frame(2);const held=s.pose(3);
        s.mouse(88,78,false);s.frame();const released=s.pose(3);
        report.baselineFirstRelease={heldX:held.x,releasedX:released.x,lostX:held.x-released.x};
        s.vm.stopAll();
    }
    const s=await scene(true,{filename:project});
    for(const id of [2,3]){
        const data=throwGrip(s,id);
        report.observations[id===2?'button':'menu']=verifyThrow(s,id,data);
        s.mouse(220,-158,false);s.frame(70);near(state(s,id).x,0,.005);near(state(s,id).reach,0,.005);
    }
    report.checks.push('Both Button and Menu keep their last held position, stretch and signed velocity through the release frame.',
        'The displayed center and contour follow the analytical solution, overshoot and return after a moving release; idle rendering retains the resting pose.');
    for(const id of [2,3]){
        press(s,id);s.mouse(88,yFor(id),true);const track=[];
        for(let i=0;i<27;i++){s.frame();track.push(state(s,id));}
        const ideal=28*.65*102/(28+.65*102);
        const peak=Math.max(...track.map(x=>x.contact)),last=track.at(-1);
        assert.ok(peak>ideal+.12,'The follower must be able to cross a stationary pointer target.');
        near(last.contact,ideal,.02);near(last.reach,peak,.015);
        assert.ok(track.every((p,i)=>i===0||p.reach>=track[i-1].reach-.00001),'Holding through a rebound reduced the high-water stretch');
        report.observations[id===2?'heldButton':'heldMenu']={ideal,peak,settled:last.contact,retained:last.reach};
        s.mouse(88,yFor(id),false);s.frame(65);
    }
    report.checks.push('Held Button and Menu centers overshoot a stationary pointer target and settle, while the extension keeps its highest reached value.');
    // Re-grab during rebound while the surface has not travelled back to its anchor.
    press(s,2);s.mouse(62,-66,true);s.frame(8);s.mouse(62,-66,false);s.frame(2);
    const residual=state(s,2);
    s.mouse(residual.x,-66,true);s.frame();const attached=state(s,2);
    near(residual.x,attached.x,.02);assert.equal(Number(s.get('UI pressed id')),2);
    s.mouse(residual.x-40,-66,true);s.frame();assert.ok(state(s,2).x<attached.x);
    s.mouse(residual.x-40,-66,false);s.frame(75);
    report.checks.push('A rapid second press attaches at the in-flight pose and can redirect it without a position jump.');
    // Outside hover differs from drag. Check actual diameter, not just a stored target.
    for(const id of [2,3]){
        s.mouse(220,-158,false);s.frame(55);const initial=state(s,id);
        const y=yFor(id);s.mouse(0,y,false);s.frame(3);const lift=state(s,id);
        assert.ok(lift.w>initial.w+.05&&lift.liftVelocity>0);
        s.mouse(220,-158,false);s.frame();
        let below=false;for(let i=0;i<25;i++){s.frame();if(state(s,id).w<initial.w-.03)below=true;}
        assert.ok(below,'The displayed resting silhouette should rebound after hover on slot '+id);
    }
    report.checks.push('Hover appearance springs between actual silhouettes for Button and Menu while retaining a fixed idle anchor.');
    s.vm.stopAll();
    const critical=await scene(true,{filename:project,bounce:0});
    const c=throwGrip(critical,3);
    assert.equal(c.release.bounce,0);
    assert.ok(c.frames.every(f=>f.x>=-.0001&&f.reach>=-.0001),'Zero bounce must not cross the resting pose');
    critical.vm.stopAll();
    report.checks.push('Menu bounce zero produces a critically damped, non-oscillating return.');
    const same30=await scene(true,{filename:project}),same60=await scene(true,{filename:project});
    for(const host of [same30,same60]){press(host,2);host.mouse(88,-66,true);host.frame(2);host.mouse(220,-158,false);host.frame();}
    same30.frame(6,1000/30);same60.frame(12,1000/60);
    for(const k of ['x','reach','velocity','stretchVelocity','w'])near(state(same30,2)[k],state(same60,2)[k],.02);
    same30.vm.stopAll();same60.vm.stopAll();
    report.checks.push('Six 30 Hz and twelve 60 Hz release steps give the same center, velocity and width after equal elapsed time.');
    const interpreted=await scene(false,{filename:project});const runtime=throwGrip(interpreted,2);
    near(runtime.held.x,runtime.release.x,.001);assert.ok(runtime.frames.some(p=>p.x<0));
    interpreted.vm.stopAll();report.checks.push('The installed Scratch interpreter also carries and rebounds the visible grip.');
    report.passed=true;
}
main().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.writeFileSync(output,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report,null,2));process.exit(report.passed?0:1);
});
