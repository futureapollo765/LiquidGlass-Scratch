#!/usr/bin/env node
/** Compare actual Scratch Pen colors to EffOnly's own Reflection block. */
const fs=require('node:fs'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const [previous,current,reference,out]=process.argv.slice(2);
if(!out)throw Error('Usage: node test_reference_refraction.cjs previous.sb3 current.sb3 EffOnly.sb3 report.json');
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
const report={baseline:sha(previous),sha256:sha(current),effOnlySHA256:sha(reference),checks:[],profiles:{},private:{}};
const xs=[44,52,60,64,70,74,76,78],radius=80,reflection=.5;
const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v)),near=(a,b,t=.015)=>assert.ok(Math.abs(a-b)<=t,`${a} differs from ${b} by more than ${t}`);
const unpack=v=>[v>>16&255,v>>8&255,v&255];
const strip=Array.from({length:480*360},(_,i)=>{
    const x=i%480,y=Math.floor(i/480);
    return ((Math.floor(x/10)%2?240:12)<<16)|((x%256)<<8)|(y%256);
});
function texel(x,y){return unpack(strip[clamp(179-y,0,359)*480+clamp(x+240,0,479)]);}
function sample(x,y){
    x=clamp(x,-240,239);y=clamp(y,-180,179);
    const u=Math.floor(x),v=Math.floor(y),fx=x-u,fy=y-v;
    const rgb=[0,0,0];for(const [xx,wx]of [[u,1-fx],[u+1,fx]])for(const [yy,wy]of [[v,1-fy],[v+1,fy]])
        texel(xx,yy).forEach((a,i)=>rgb[i]+=a*wx*wy);
    return rgb;
}
async function source(){
    const vm=await H.loadProject(reference,{compiler:true});
    const stage=vm.runtime.getTargetForStage(),get=n=>Object.values(stage.variables).find(v=>v.name===n);
    for(const [n,v] of Object.entries({glassRad:radius,reflection,edgeHighlight:0,glassCenterX:0,glassCenterY:0,
        original:strip.slice(),processed:strip.slice()}))get(n).value=v;
    H.invoke(vm,'LiquidGlass','ProcessImage',[],{maxMilliseconds:90000});
    const original=xs.map(x=>unpack(get('processed').value[179*480+x+240]));
    xs.forEach((x,i)=>{const d=Math.max(0,x-radius*(1-reflection))**2/10;
        assert.deepEqual(original[i],texel(Math.round(x-d),0),'EffOnly reference pixel at '+x);});
    vm.stopAll();return original;
}
async function engine(file){
    const vm=await H.loadProject(file,{compiler:true}),target=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass');
    const get=n=>H.getVariable(vm,target.getName(),n).value,set=(n,v)=>{H.getVariable(vm,target.getName(),n).value=v;};
    const call=(name,...args)=>H.invoke(vm,target.getName(),name,args,{maxMilliseconds:90000});
    const pixels=new Map();
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},pick:()=>-1,draw(){},
        penClear(){},penPoint(){},penStamp(){},penLine(_,attr,x,y,u,v){
            if(y===v&&attr.diameter>=1&&attr.color4f[3]>.99)pixels.set((x+u)/2+','+y,attr.color4f.slice(0,3).map(c=>Math.round(c*255)));
        }};
    function setup(kind,geometry={}){
        call('LG initialize');set('UI view',1);set('Background',1);set('Original RGB',strip.slice());call('UI begin');
        const proto=Object.values(target.blocks._blocks).find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith(kind+' %s '));
        const defaults=JSON.parse(proto.mutation.argumentdefaults),names=JSON.parse(proto.mutation.argumentnames);
        const values={id:3,x:0,y:0,width:2*radius,height:2*radius,shape:'circle',launcher:'circle',radius,
            reflection,distortion:1,edge:0,highlight:0,light:-30,tint:0,pull:0,join:0,group:0,quality:2,drag:0,transition:0,
            'tint color':'#fffFFF',brightness:0,transparency:100,blur:0,label:'',mode:0,items:'A|B',...geometry};
        call(proto.mutation.proccode,...names.map((n,i)=>values[n]??defaults[i]));
        call('LG advance');call('UI settle');pixels.clear();call('LG render');
    }
    function probe(x,y){
        const i=Math.round((get('top')-y)/get('q'))*get('cols')+Math.round((x-get('left'))/get('q'))+1;
        set('D',get('field')[i-1]);call('LG shade %s %s %s',x,y,i);
        return {x,y,d:get('D'),dx:get('normalX')*get('refraction'),dy:get('normalY')*get('refraction'),color:pixels.get(x+','+y)};
    }
    return {vm,target,get,set,call,pixels,setup,probe};
}
function publicTangencies(s) {
    const fixtures=[
        {name:'rounded rectangle',shape:1,w:144,h:96,r:24,faces:['horizontal','vertical']},
        {name:'capsule',shape:2,w:160,h:80,r:40,faces:['horizontal']},
    ];
    const results=[];
    const depth=2,reflection=.8;
    for(const f of fixtures){
        s.setup('Glass',{shape:f.shape,width:f.w,height:f.h,radius:f.r,reflection,quality:1});
        near(s.get('q'),1);near(Number(s.get('r')[2]),f.r);
        const band=.5*f.h*reflection,nominal=(band-depth)**2/10,innerRadius=f.r-depth;
        for(const face of f.faces)for(const signX of [-1,1])for(const signY of [-1,1]){
            const horizontal=face==='horizontal';
            const junctionX=f.w/2-f.r,junctionY=f.h/2-f.r;
            function trace(x,y){
                const q=s.probe(x,y),source=[s.get('matTexX')-240,179-s.get('matTexY')];
                // These are the actual coordinates supplied to the native texture sampler.
                near(source[0],x-q.dx,.00001);near(source[1],y-q.dy,.00001);
                assert.ok(q.color,'No opaque native Pen sample at '+x+','+y);
                sample(...source).forEach((channel,k)=>near(q.color[k],channel,2));
                const dx=x-source[0],dy=y-source[1],along=horizontal?dx*signX:dy*signY;
                const outward=horizontal?dy*signY:dx*signX;
                return {source,angle:Math.atan2(along,outward)*180/Math.PI,strength:Math.hypot(dx,dy)};
            }
            const around=[];
            for(let t=-4;t<=4;t++)around.push(trace(
                signX*(horizontal?junctionX+t:f.w/2-depth),signY*(horizontal?f.h/2-depth:junctionY+t)));
            const increments=around.slice(1).map((p,i)=>p.source.map((v,j)=>v-around[i].source[j]));
            const turning=around.slice(1).map((p,i)=>p.angle-around[i].angle);
            // One step on the inner circular arc turns its geometric normal by
            // about atan(1/r). A full nearest-side flip would be 45–90 degrees.
            const maxAngle=1.6*Math.atan(1/innerRadius)*180/Math.PI;
            for(const angle of turning)assert.ok(angle>=-.02 && angle<=maxAngle,
                'Unphysical angular turn at '+f.name+' '+face+': '+angle);
            const before=increments[3],after=increments[4];
            const kink=Math.hypot(after[0]-before[0],after[1]-before[1]);
            // The optical map rotates over the finite normal-sampling span.
            // A unit source step can be several pixels under strong refraction;
            // what matters at tangency is the difference between consecutive steps.
            const span=Math.ceil(.2*band);
            assert.ok(kink < 1+1.5*nominal/(innerRadius*span),'Flat/arc source increments jump: '+kink);
            for(const step of increments)assert.ok(Math.hypot(...step)<2+1.6*nominal/innerRadius,
                'Source skipped across the textured backdrop');
            near(around[4].strength,nominal,.02);
            const cos=Math.cos(Math.PI/6),sin=.5;
            const x=Math.round(junctionX+innerRadius*(horizontal?sin:cos))*signX;
            const y=Math.round(junctionY+innerRadius*(horizontal?cos:sin))*signY;
            const arc=trace(x,y);
            assert.ok(arc.strength>75&&arc.strength>nominal*.85);
            assert.ok(arc.angle>20&&arc.angle<40,'Expected the actual source ray to follow the curved rim');
            results.push({shape:f.name,face,signX,signY,sourceAtTangency:around[4].source,
                incomingSourceStep:before,outgoingSourceStep:after,sourceStepChange:kink,
                maxAnglePerStagePixel:Math.max(...turning),curvedDisplacement:arc.strength,curvedRayDegrees:arc.angle});
        }
    }
    return results;
}
async function main(){
    const eff=await source(),old=await engine(previous),now=await engine(current);
    for(const kind of ['Glass','Background','Button','Menu']){
        old.setup(kind);now.setup(kind);
        const comparison=xs.map((x,i)=>{
            const a=old.probe(x,0),b=now.probe(x,0),expected=Math.max(0,x-radius*(1-reflection))**2/10;
            near(b.dx,expected,.018);near(b.dy,0,.001);assert.ok(b.color&&a.color,'Expected an emitted native Pen pixel for '+kind);
            for(const [k,n] of sample(x-expected,0).entries())assert.ok(Math.abs(b.color[k]-n)<=2,JSON.stringify({kind,x,k,got:b.color,want:sample(x-expected,0),sample:[now.get('R'),now.get('G'),now.get('B')]}));
            return {x,prior:a.dx,current:b.dx,oldRGB:a.color,actualRGB:b.color,referenceNearest:eff[i]};
        });
        assert.ok(comparison.at(-1).current>comparison.at(-1).prior*1.2);
        if(kind!=='Glass')assert.ok(comparison.some(s=>Math.abs(s.oldRGB[0]-s.actualRGB[0])>180),
            'At least one high-contrast stripe must visibly move on '+kind);
        report.profiles[kind]=comparison;
    }
    report.checks.push('Raw Glass, Background, Button and Menu match EffOnly quadratic inward displacements at eight circular lens depths, including above 110 px.',
        'On the same high-contrast wallpaper, actual native Pen colors follow the restored profile on all four public components.');
    const s=now;
    const x=78, cell=Math.round((s.get('top')-0)/s.get('q'))*s.get('cols')+Math.round((x-s.get('left'))/s.get('q'))+1;
    s.get('pixelDistortion')[cell-1]=3;
    const far=s.probe(x,0);
    near(far.dx,3*144.4,.02);near(s.get('sampleX'),-240);near(s.get('sampleY'),0);
    sample(-240,0).forEach((v,k)=>near(s.get('RGB'[k]),v,.01));
    report.extendedReach={displacement:far.dx,clampedStageX:s.get('sampleX')};
    report.checks.push('A 433.2-pixel displacement past the stage boundary reads the nearest real stage pixel.');
    const pane={owner:3,path:'Child',parent:'',row:1,p:1,v:0,goal:1,x:0,y:0,w:160,h:160,r:80,rows:0,pitch:28,dim:0,fade:1};
    for(const [n,v]of Object.entries(pane))s.set('UI layer '+n,[v]);
    s.set('UI lens band',40);s.set('UI private q',1);s.set('frameBG',1);
    // The standalone shader is normally called after the layer painter sets its transient coat.
    // A native save may have been taken partway through an animation. Probe the settled pane.
    s.set('UI coat mix',0);s.set('UI transition coverage',1);
    function privateAt(x,y){
        s.call('UI layer rounded shade %s x %s y %s',1,x,y);
        return {x:s.get('UI source x'),y:s.get('UI source y'),rgb:['R','G','B'].map(k=>s.get(k))};
    }
    const face=privateAt(78,0),expected=(38**2/10);
    // The private normal includes a smooth, nonzero corner denominator.
    near(78-face.x,expected,1.2);near(face.y,0);near(s.get('UI pixel coverage'),1);sample(face.x,face.y).forEach((n,i)=>near(face.rgb[i],n,1));
    const diagA=privateAt(55,54.99),diagB=privateAt(55,55.01);
    const gap=Math.hypot(diagA.x-diagB.x,diagA.y-diagB.y);assert.ok(gap<.25);
    report.private={edgeDisplacement:78-face.x,cornerChangeOverPoint02:gap};
    report.checks.push('The private layer samples the same strong quadratic profile while its rounded corner normal stays continuous.');
    for(const bg of [1,2]){
        s.set(bg===1?'Original RGB':'Grid RGB',strip.slice());
        for(const [x,y] of [[-230.75,.4],[-230.5,.4],[-230.25,.4],[-999.3,3.4],[239.9,-180.9],[-240,179]]){
            s.call('LG material sample x %s y %s blur %s background %s',x,y,0,bg);
            const actual=['R','G','B'].map(k=>s.get(k));
            sample(x,y).forEach((n,i)=>near(actual[i],n,1e-6));
            if(x===-230.5){
                s.call('LG material sample x %s y %s blur %s background %s',x,y,2,bg);
                const high=['R','G','B'].map(k=>s.get(k));
                s.call('LG material sample x %s y %s blur %s background %s',x,y,1,bg);
                ['R','G','B'].forEach((k,i)=>near(s.get(k),(actual[i]+high[i])/2,1e-6));
            }
        }
    }
    report.checks.push('Both backgrounds interpolate individual RGB channels at fractional coordinates and clip to the nearest stage edge; radius one blends the raw and filtered images.');
    report.publicTangencies=publicTangencies(now);
    report.checks.push('Twelve public rounded-rectangle and capsule flat-to-arc junctions preserve strong curved displacement and smoothly changing source steps at both ends of every flat side.');
    old.vm.stopAll();now.vm.stopAll();report.passed=true;
}
main().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.writeFileSync(out,JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,error:report.error}));process.exit(report.passed?0:1);
});
