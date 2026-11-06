#!/usr/bin/env node
/** Regression checks execute the actual generated Scratch blocks in TurboWarp's VM. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const H = require('./vm_harness.cjs');
const {gridPixel} = require('./test_grid_pixels.cjs');
let API, inputNames;
const defaults = {id:1,x:0,y:0,width:80,height:80,shape:3,radius:20,reflection:.5,distortion:1,edge:1,highlight:1,light:-30,tint:.05,join:24,group:1,transition:.45,spring:18,damping:.85,pull:.9,drag:1,quality:2};
const result = {project: path.resolve(process.argv[2] || 'LiquidGlass_Studio.sb3'), tests:[], timing:{}, errors:[]};
const componentPath=path.resolve(process.argv[4]||path.join(path.dirname(result.project),'LiquidGlass_Component.sprite3'));
const digest=filename=>crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
result.artifacts=Object.fromEntries([result.project,componentPath].map(filename=>[path.basename(filename),{path:filename,sha256:digest(filename),bytes:fs.statSync(filename).size}]));
let vm;
let mode;
const sprite = 'Liquid Glass';
const variable = name => H.getVariable(vm, sprite, name);
const get = name => variable(name).value;
const set = (name, value) => { variable(name).value = value; };
const list = name => variable(name).value;
const at = (name,id=1) => list(name)[id-1];
const put = (name,id,value) => {list(name)[id-1]=value;};
const has = name => Object.values(vm.runtime.targets.find(t=>t.getName()===sprite).variables).some(v=>v.name===name);
function enterGlassDemo(tick) {
  if (!has('UI view')) return;
  vm.postIOData('keyboard',{key:'g',isDown:true});
  vm.postIOData('keyboard',{key:'g',isDown:false});
  tick(3);
  near(get('UI view'),0);
}
const invoke = (name,...args) => H.invoke(vm,sprite,name,args,{maxMilliseconds:60000});
const near = (actual,expected,tolerance=1e-8) => assert.ok(Math.abs(actual-expected)<=tolerance, `${actual} != ${expected} ±${tolerance}`);
const test = (name, fn) => {fn();result.tests.push({mode,name,passed:true});};
function glass(options={}) { const values={'tint color':'#FFFFFF',transparency:100,brightness:0,blur:0,...defaults,...options}; return invoke(API,...inputNames.map(k=>values[k])); }
function reset() {invoke('LG initialize');}
function shape(id,x,y) {invoke('LG shape %s %s %s',id,x,y);return {d:get('sd'),nx:get('nx'),ny:get('ny')};}
function field(x,y) {invoke('LG field %s %s',x,y);return get('D');}
function setOpticsFixture(size=9){
  if(has('pixelBand')){
    const light=Number(at('light'))*2*Math.PI/180;
    const values={Band:.5*Math.min(at('w'),at('h'))*at('reflection'),Distortion:at('distortion'),Edge:at('edge'),Highlight:at('highlight'),LightX:Math.cos(light),LightY:Math.sin(light),Tint:at('tint')};
    for(const [name,value]of Object.entries(values))set('pixel'+name,Array(size).fill(value));
  }else{set('owner',Array(size).fill(1));set('owner2',Array(size).fill(1));set('mixWeight',Array(size).fill(1));}
}
let time=0;
function advance(seconds=1/30) {time+=seconds;invoke('LG advance');}

async function run(compiler) {
  vm = await H.loadProject(result.project,{compiler});
  const proto=Object.values(vm.runtime.targets.find(t=>t.getName()===sprite).blocks._blocks).find(b=>b.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith('Glass %s '));
  API=proto.mutation.proccode;inputNames=JSON.parse(proto.mutation.argumentnames);
  // The project may have embedded compiler defaults; explicitly select the mode under test.
  vm.setCompilerOptions({enabled:compiler});
  mode=compiler?'TurboWarp compiler':'Scratch interpreter';
  const compileErrors=[];
  vm.on('COMPILE_ERROR',(...args)=>compileErrors.push(args.map(String)));
  const clock=vm.runtime.ioDevices.clock._projectTimer;
  time=0;clock.nowObj={now:()=>time*1000};clock.startTime=0;
  test('Initialization creates eight independent component slots',()=>{reset();assert.equal(list('active').length,8);assert.ok(list('active').every(x=>Number(x)===0));near(get('Frames'),0);});
  test('Public API clamps dimensions, radii, effect strengths and quality',()=>{
    glass({width:-900,height:0,shape:1,radius:500,reflection:7,distortion:-9,edge:99,highlight:99,tint:99,join:99,transition:99,spring:0,damping:0,pull:9,quality:99});
    for(const [name,expected] of Object.entries({w:440,h:8,r:4,reflection:1,distortion:-3,edge:6,highlight:3,tint:.75,join:60,transition:3,spring:1,damping:.1,pull:2,quality:4}))near(at(name),expected);
    glass({id:0,quality:0});near(at('quality',1),1);glass({id:99});near(at('active',8),1);
  });
  test('Rounded rectangle, capsule and circle are exact distance-field cases',()=>{
    reset();glass({shape:1,width:120,height:80,radius:16});near(shape(1,60,0).d,0);near(shape(1,0,40).d,0);assert.ok(shape(1,59,39).d>0);near(shape(1,0,0).d,-40);
    glass({id:2,shape:'capsule',width:120,height:40});near(at('r',2),20);near(shape(2,60,0).d,0);near(shape(2,0,20).d,0);near(shape(2,40+20/Math.sqrt(2),20/Math.sqrt(2)).d,0);
    glass({id:3,shape:'circle',width:80,height:19});near(at('h',3),80);near(at('r',3),40);near(shape(3,24,32).d,0);near(shape(3,0,0).d,-40);
  });
  test('Same-ID changes animate continuously while other IDs retain their settings',()=>{
    reset();glass({id:1,shape:3,width:80});glass({id:2,x:100,shape:2,width:120,height:30,reflection:.2});
    glass({id:1,x:80,shape:1,width:180,height:120,radius:20});near(at('w'),80);near(at('tw'),180);advance();assert.ok(at('w')>80&&at('w')<180);assert.ok(at('x')>0&&at('x')<80);
    near(at('w',2),120);near(at('h',2),30);near(at('reflection',2),.2);
    for(let i=0;i<90;i++)advance();near(at('w'),180,.001);near(at('x'),80,.01);near(at('r'),20,.001);
    glass({id:1,x:-50,shape:3,width:60,transition:0});advance();near(at('x'),-50);near(at('w'),60);near(at('h'),60);near(at('r'),30);
  });
  test('Nearby same-group shapes bridge without changing outer/back surfaces',()=>{
    reset();glass({id:1,x:-45,width:70,join:24});glass({id:2,x:45,width:70,join:24});
    const joined=field(0,0);assert.ok(joined<0,`bridge missing, D=${joined}`);
    for(const [x,y] of [[-80,0],[80,0],[-45,35],[45,35],[-85,0],[85,0]])near(field(x,y),Math.min(shape(1,x,y).d,shape(2,x,y).d),1e-7);
    put('group',2,2);near(field(0,0),10);put('group',2,0);near(field(0,0),10);put('group',2,1);put('join',2,0);near(field(0,0),10);
    put('join',2,24);put('x',2,150);assert.ok(field(50,0)>0);
    put('x',2,-45);near(field(-80,0),0);near(field(-45,35),0);
  });
  test('Cached field matches fresh queries and all four bounds prevent whole-shape bulges',()=>{
    reset();glass({id:1,x:-50,shape:1,width:100,height:100,radius:20,join:30});glass({id:2,x:50,shape:1,width:100,height:100,radius:20,join:30});
    invoke('LG prepare');near(get('activeCount'),2);near(get('pairCount'),1);
    for(const [x,y] of [[-100,0],[100,0],[-60,50],[0,50],[60,50],[-60,-50],[0,-50],[60,-50],[0,51],[0,-51],[-101,0],[101,0]]){
      invoke('LG sample %s %s',x,y);const cached=get('D');near(cached,Math.min(shape(1,x,y).d,shape(2,x,y).d),1e-7);near(field(x,y),cached,1e-7);assert.ok(cached>=-1e-7);
    }
    for(const [x,y] of [[-20,-10],[0,0],[12,40],[0,49.9],[-85,25]]){invoke('LG sample %s %s',x,y);const cached=get('D');near(field(x,y),cached,1e-7);}
    put('amp',1,15);invoke('LG prepare');near(list('pairLeft')[0],-130);near(list('pairTop')[0],80);
  });
  test('Two-shape joins expose continuous optical blending for unequal-size glass',()=>{
    reset();glass({id:1,x:-50,width:80,join:24});glass({id:2,x:40,width:60,join:24});
    const band=()=>has('outBand')?get('outBand'):15+5*get('materialWeight');
    field(0,0);near(band(),17.5);field(-.001,0);const left=band();field(.001,0);const right=band();assert.ok(left>17.5&&right<17.5);assert.ok(left-right<.001);
    field(-90,0);if(has('outBand'))near(get('outBand'),20);else{near(get('material'),1);near(get('secondMaterial'),1);near(get('materialWeight'),1);}
    reset();for(let id=1;id<=8;id++)glass({id,x:id*20-90,width:24,join:24});invoke('LG prepare');near(get('activeCount'),8);near(get('pairCount'),28);field(0,0);assert.ok(Number.isFinite(get('D')));
  });
  if(has('outBand')){
    test('Three-shape joins remove pair-winner seams in geometry and optical thickness',()=>{
      const audit=JSON.parse(fs.readFileSync(path.join(__dirname,'../research/nary_blend_audit.json'),'utf8'));
      for(const fixture of audit.cases){
        reset();fixture.shapes.forEach((s,i)=>glass({id:i+1,x:s.x,y:s.y,width:s.w,height:s.h,radius:s.r,shape:s.name==='circle'?3:s.name==='capsule'?2:1,join:s.join,group:s.group}));
        const p=fixture.winner_switch,eps=.0001,[dx,dy]=p.direction,expected=fixture.orders_at_switch[0];
        near(field(p.x,p.y),expected.D,1e-6);near(get('outBand'),expected.band,1e-6);
        const leftD=field(p.x-dx*eps,p.y-dy*eps),leftBand=get('outBand');const rightD=field(p.x+dx*eps,p.y+dy*eps),rightBand=get('outBand');
        assert.ok(Math.abs(rightBand-leftBand)<.001,`three-way optical seam: ${leftBand}→${rightBand}`);assert.ok(Math.abs(rightD-leftD)<.001);
      }
    });
    test('N-ary groups and join-zero components remain optically and geometrically isolated',()=>{
      reset();glass({id:1,x:-35,y:0,width:130,height:80,shape:1,radius:18,join:30});glass({id:2,x:40,y:10,width:70,height:70,shape:3,join:30});
      const d12=field(27.83096047272784,-19),band12=get('outBand');glass({id:3,x:10,y:-35,width:120,height:38,shape:2,join:30,group:2});
      const d3=shape(3,27.83096047272784,-19).d;near(field(27.83096047272784,-19),Math.min(d12,d3),1e-6);near(get('outBand'),d3<d12?9.5:band12,1e-6);
      put('group',3,1);put('join',3,0);near(field(27.83096047272784,-19),Math.min(d12,d3),1e-6);near(get('outBand'),d3<d12?9.5:band12,1e-6);
    });
    test('Double-angle light blending preserves symmetric highlights and wraps angles smoothly',()=>{
      reset();glass({id:1,x:-45,width:70,join:30,light:179});glass({id:2,x:45,width:70,join:30,light:-179});field(0,0);near(get('outLightX'),Math.cos(2*Math.PI/180),1e-8);near(get('outLightY'),0,1e-8);
      put('light',1,0);put('light',2,180);field(0,0);near(get('outLightX'),1,1e-8);near(get('outLightY'),0,1e-8);
    });
  }
  test('Horizontal pull makes centered axis-aligned ellipses with reciprocal squeeze and elastic recovery',()=>{
    reset();glass({shape:3,width:80,pull:1});glass({x:150,shape:3,width:80,pull:1});advance();assert.ok(at('amp')>0);near(at('w'),80);near(at('h'),80);
    // Pure-axis pull preserves area; diagonal composition intentionally need not.
    const scaleX=at('scaleX'),scaleY=at('scaleY');assert.ok(scaleX>1&&scaleX<=1.65+1e-10);near(scaleX*scaleY,1);
    for(let angle=0;angle<360;angle+=30){
      const bx=40*Math.cos(angle*Math.PI/180),by=40*Math.sin(angle*Math.PI/180);
      const x=at('x')+bx*scaleX,y=at('y')+by*scaleY;
      const a=shape(1,x,y);near(a.d,0,1e-6);near(Math.hypot(a.nx,a.ny),1,1e-6);
      const opposite=shape(1,2*at('x')-x,2*at('y')-y);near(opposite.d,a.d,1e-6);near(opposite.nx,-a.nx,1e-6);near(opposite.ny,-a.ny,1e-6);
      const h=.01,gx=(shape(1,x+h,y).d-shape(1,x-h,y).d)/(2*h),gy=(shape(1,x,y+h).d-shape(1,x,y-h).d)/(2*h),len=Math.hypot(gx,gy);
      assert.ok((a.nx*gx+a.ny*gy)/len>.9999,'analytic normal disagrees with finite differences');
      for(const value of Object.values(a))assert.ok(Number.isFinite(value));
    }
    for(const [x,y] of [[-240,-180],[240,180],[0,0],[150,0]])for(const v of Object.values(shape(1,x,y)))assert.ok(Number.isFinite(v));
    for(let i=0;i<150;i++)advance();assert.ok(at('amp')<.01,`pull did not settle: ${at('amp')}`);near(at('w'),80);near(at('h'),80);
  });
  test('Vertical and diagonal pull combine independent axes without rotating circle ellipses',()=>{
    for(const [tx,ty]of[[0,150],[100,100],[100,-70]]){
      reset();glass({shape:3,width:80,pull:1});glass({x:tx,y:ty,shape:3,width:80,pull:1});advance();const sx=at('scaleX'),sy=at('scaleY');
      if(tx===0){assert.ok(sx<1&&sy>1);near(sx*sy,1);}if(tx===ty){assert.ok(sx>1&&sy>1);near(sx,sy);assert.ok(sx*sy>1);}
      const right=shape(1,at('x')+40*sx,at('y')),top=shape(1,at('x'),at('y')+40*sy);near(right.d,0,1e-6);near(top.d,0,1e-6);near(right.nx,1);near(right.ny,0);near(top.nx,0);near(top.ny,1);
      for(let angle=15;angle<360;angle+=30){const bx=40*Math.cos(angle*Math.PI/180),by=40*Math.sin(angle*Math.PI/180);near(shape(1,at('x')+sx*bx,at('y')+sy*by).d,0,1e-6);}
      near(at('w'),80);near(at('h'),80);
    }
  });
  test('Rounded rectangle and capsule pull squeeze both sides equally without tapering',()=>{
    for(const kind of [1,2]){
      reset();const height=kind===1?60:40,radius=kind===1?12:20;
      glass({shape:kind,width:120,height,radius,pull:1});glass({x:100,y:65,shape:kind,width:120,height,radius,pull:1});advance();
      const sx=at('scaleX'),sy=at('scaleY');assert.ok(sx!==1||sy!==1);near(at('w'),120);near(at('h'),height);
      const forward=(bx,by)=>[at('x')+sx*bx,at('y')+sy*by];
      for(let angle=15;angle<360;angle+=30){const c=Math.cos(angle*Math.PI/180),s=Math.sin(angle*Math.PI/180),bx=(60-radius)*Math.sign(c)+radius*c,by=(height/2-radius)*Math.sign(s)+radius*s;
        const [x,y]=forward(bx,by),a=shape(1,x,y),opposite=shape(1,2*at('x')-x,2*at('y')-y);near(a.d,0,1e-6);near(opposite.d,0,1e-6);near(opposite.nx,-a.nx,1e-6);near(opposite.ny,-a.ny,1e-6);
      }
      for(const [bx,by]of[[10,5],[30,10],[-30,-10],[75,45]]){const [x,y]=forward(bx,by);near(shape(1,x,y).d,shape(1,2*at('x')-x,2*at('y')-y).d,1e-6);}
      const edgeA=forward(-20,height/2),edgeB=forward(20,height/2);near(edgeA[1],edgeB[1]);near(shape(1,...edgeA).ny,1);near(shape(1,...edgeB).ny,1);near(shape(1,...edgeA).nx,0);near(shape(1,...edgeB).nx,0);
    }
  });
  test('Mouse dragging uses contour hit-tests, preserves grab offset, and keeps other IDs independent',()=>{
    const mouse=(x,y,isDown)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});
    reset();glass({id:1,x:-60,y:0,shape:3,width:80});glass({id:2,x:70,y:0,shape:2,width:80,height:40});
    mouse(-22,38,true);advance();near(get('grab'),0);mouse(-22,38,false);advance();
    mouse(-50,10,true);advance();near(get('grab'),1);near(get('grabDX'),-10);near(get('grabDY'),-10);
    mouse(20,40,true);for(let i=0;i<5;i++)advance();near(at('tx'),10);near(at('ty'),30);assert.ok(at('amp')>0);near(at('tx',2),70);near(at('ty',2),0);
    mouse(20,40,false);advance();near(get('grab'),0);near(at('tx'),10);for(let i=0;i<150;i++)advance();assert.ok(at('amp')<.01);
    put('drag',2,0);mouse(70,0,true);advance();near(get('grab'),0);mouse(70,0,false);advance();
  });
  test('Background sampling clamps both axes independently at all four stage edges',()=>{
    for(const bg of [1,2]){
      set('Background',bg);const name=bg===1?'Original RGB':'Grid RGB';
      for(const [x,y,index] of [[-999,999,1],[999,999,480],[-999,-999,172321],[999,-999,172800],[0,0,86161]]){
        const expected=bg===2?gridPixel(list(name),()=>list('LG grid rows'),index,()=>list('LG grid pixels')):list(name)[index-1];
        invoke('LG background %s %s',x,y);near(get('sampleIndex'),index);near(Number(get('color')),Number(expected));
      }
    }
  });
  test('Shading keeps the full refraction while bounding the stage sample, RGB and opacity',()=>{
    reset();glass({reflection:1,distortion:3,highlight:3,tint:.75,edge:6});set('q',2);set('cols',3);set('D',0);set('field',[0,0,0,-2,0,2,0,0,0]);setOpticsFixture();
    invoke('LG shade %s %s %s',239,179,5);near(get('refraction'),get('shadeBand')**2*get('shadeDistortion')/10);for(const c of ['R','G','B'])assert.ok(get(c)>=0&&get(c)<=255);near(get('sampleY'),179);assert.ok(get('sampleX')>=-240&&get('sampleX')<=239);
    const pen=vm.runtime.targets.find(t=>t.getName()===sprite)._customState['Scratch.pen'];near(pen.transparency,50);assert.ok(pen.penAttributes.color4f.every(v=>v>=0&&v<=1));
    put('distortion',1,0);put('tint',1,0);put('highlight',1,0);setOpticsFixture();invoke('LG shade %s %s %s',50,-35,5);near(get('refraction'),0);near(get('sampleX'),50);near(get('sampleY'),-35);const expected=Number(list('Original RGB')[(179+35)*480+50+240]);near(get('R')*65536+get('G')*256+get('B'),expected);
  });
  test('Optics fade smoothly where merged gradients cancel while preserving ordinary edge refraction',()=>{
    reset();glass({width:80,shape:3,reflection:.5,distortion:1,highlight:0,tint:0});set('q',1);set('cols',3);set('D',-10);setOpticsFixture();
    const shadeGradient=(g)=>{set('field',[-10,-10,-10,-10-g,-10,-10+g,-10,-10,-10]);invoke('LG shade %s %s %s',0,0,5);return {gain:get('opticalGain'),ref:get('refraction'),sampleX:get('sampleX'),sampleY:get('sampleY')};};
    const edge=shadeGradient(1);near(edge.gain,1);near(edge.ref,10);near(edge.sampleX,-10);
    const weak=shadeGradient(.02);assert.ok(weak.gain<.01);assert.ok(Math.abs(weak.ref)<.1);near(weak.sampleX,0);
    const zero=shadeGradient(0);near(zero.gain,0);near(zero.ref,0);near(zero.sampleX,0);near(zero.sampleY,0);
    const left=shadeGradient(-.001),right=shadeGradient(.001);assert.ok(Math.abs(left.ref)+Math.abs(right.ref)<.001);
  });
  if(compiler){
    test('Compiled demo completes one full field-and-shading render with finite pixels',()=>{
      reset();invoke('LG demo');advance();const perf=invoke('LG render');result.timing.compiledDemoRenderMs=perf.elapsedMs;result.timing.gridCells=list('field').length;assert.ok(list('field').length>1000);assert.ok(list('field').every(Number.isFinite));
      if(has('pixelBand'))for(const name of ['Band','Distortion','Edge','Highlight','LightX','LightY','Tint']){assert.equal(list('pixel'+name).length,list('field').length);assert.ok(list('pixel'+name).every(Number.isFinite));}else assert.ok(list('owner').every(x=>x>=1&&x<=8));
      near(get('Frames'),1);assert.equal(list('field').length,get('rows')*get('cols'));
      const start=performance.now();for(let i=0;i<3;i++)invoke('LG render');result.timing.compiledDemoAverageMs=(performance.now()-start)/3;
    });
    test('Joined rectangle-circle center no longer creates a dark refraction seam',()=>{
      reset();glass({id:1,x:-90,y:10,width:156,height:96,shape:1,radius:24,join:30,quality:1});glass({id:2,x:30,y:10,width:76,height:76,shape:3,join:30,quality:1});advance();invoke('LG render');
      const opticalPoint=(x,y)=>{const cell=Math.round((get('top')-y)/get('q'))*get('cols')+Math.round((x-get('left'))/get('q'))+1;set('D',list('field')[cell-1]);invoke('LG shade %s %s %s',x,y,cell);return{x:x-get('normalX')*get('refraction'),y:y-get('normalY')*get('refraction'),gain:get('opticalGain'),offset:get('refraction')};};
      const a=opticalPoint(-11,11),b=opticalPoint(-10,11),jump=Math.hypot(a.x-b.x,a.y-b.y);
      result.timing.joinCenterTextureJump=jump;
      assert.ok(jump<1.5,`joined-center mapping jump ${jump}px per pixel`);assert.ok(a.gain<.02&&b.gain<.02);assert.ok(Math.abs(a.offset)<.2&&Math.abs(b.offset)<.2);
    });
    test('Real green-flag scheduler keeps rendering and responds to all demo keyboard controls',()=>{
      const tick=(n=1)=>{for(let i=0;i<n;i++){time+=1/30;vm.runtime._step();}};
      const key=k=>{vm.postIOData('keyboard',{key:k,isDown:true});vm.postIOData('keyboard',{key:k,isDown:false});tick(2);};
      vm.greenFlag();tick(4);near(get('Frames'),4);assert.ok(vm.runtime.threads.some(t=>t.isCompiled));
      enterGlassDemo(tick);
      key('3');near(get('Shape'),3);tick(45);near(at('w'),96,.001);near(at('h'),96,.001);near(at('r'),48,.001);
      key('2');near(get('Shape'),2);tick(45);near(at('w'),156,.001);near(at('h'),64,.001);near(at('r'),32,.001);
      key(' ');near(get('Menu'),1);tick(45);near(at('w'),238,.001);near(at('h'),146,.001);
      key('1');near(get('Shape'),1);near(get('Menu'),0);
      key('b');near(get('Background'),2);key('b');near(get('Background'),1);
      key('q');near(get('Quality'),3);near(at('quality'),3);key('e');near(get('Controls'),1);key('e');near(get('Controls'),0);
      key('m');near(get('Auto'),1);const before=get('demoX2');tick(6);assert.notEqual(get('demoX2'),before);key('m');near(get('Auto'),0);
      key('p');near(get('PullDemo'),1);near(get('Auto'),0);tick(6);assert.ok([1,2,3].every(id=>at('scaleX',id)>1));key('p');near(get('PullDemo'),0);
      const beforeFrames=get('Frames');tick(3);near(get('Frames'),beforeFrames+3);
      key('r');tick(2);near(get('Shape'),1);near(get('Quality'),2);near(get('Controls'),0);assert.ok(get('Frames')>=2);assert.ok(vm.runtime.threads.some(t=>t.isCompiled&&t.status!==4));
      result.timing.schedulerFramesVerified=beforeFrames+3;
    });
    test('Real forever loop integrates mouse drag, preserves deformation, then settles on release',()=>{
      const tick=(n=1)=>{for(let i=0;i<n;i++){time+=1/30;vm.runtime._step();}};
      const mouse=(x,y,isDown)=>vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown});
      vm.greenFlag();tick(2);enterGlassDemo(tick);mouse(-90,10,true);tick(1);near(get('grab'),1);mouse(-30,50,true);tick(8);near(at('tx'),-30);near(at('ty'),50);assert.ok(at('amp')>0);near(at('w'),156);near(at('h'),96);near(at('tx',2),85);
      mouse(-30,50,false);tick(1);near(get('grab'),0);tick(60);near(at('x'),-30,.01);near(at('y'),50,.01);assert.ok(at('amp')<.01);near(get('demoX1'),-30);near(get('demoY1'),50);assert.ok(get('Frames')>=72);
    });
    assert.equal(compileErrors.length,0,JSON.stringify(compileErrors));
  }
  vm.stopAll();
}

async function validatePackaging(){
  mode='Native package/import';
  const {VM,Storage,JSZip}=H.libraries();
  const projectArchive=await JSZip.loadAsync(fs.readFileSync(result.project));
  const project=JSON.parse(await projectArchive.file('project.json').async('string'));
  const componentArchive=await JSZip.loadAsync(fs.readFileSync(componentPath));
  const component=JSON.parse(await componentArchive.file('sprite.json').async('string'));
  const chain=(blocks,start)=>{const out=[];let id=start;while(id){assert.ok(out.length<100,'unexpected entry-script cycle');out.push(blocks[id]);id=blocks[id].next;}return out;};
  const code=b=>b?.mutation?.proccode;
  const entryHat=blocks=>Object.values(blocks).find(b=>b.opcode==='event_whenflagclicked' && code(blocks[b.next])==='LG initialize');
  const checkEntry=first=>{
    assert.equal(first.opcode,'event_whenflagclicked');
    for(const pos of [first.x,first.y]) assert.ok(Number.isFinite(pos)&&pos>=0&&pos<=180,'green flag should be visible near the upper-left workspace');
  };
  test('Studio first script exposes three native Glass calls directly in its forever loop',()=>{
    const target=project.targets.find(t=>t.name===sprite),blocks=target.blocks,first=entryHat(blocks);
    checkEntry(first);
    const setup=chain(blocks,first.next);assert.equal(code(setup[0]),'LG initialize');
    const forever=setup.find(b=>b.opcode==='control_forever');
    const entry=chain(blocks,forever.inputs.SUBSTACK[1]);
    const loop=entry[0].opcode==='control_if_else'?chain(blocks,entry[0].inputs.SUBSTACK2[1]):entry;
    const calls=loop.filter(b=>code(b)===API);
    assert.equal(calls.length,3);assert.deepEqual(calls.map(b=>Number(b.inputs[JSON.parse(b.mutation.argumentids)[0]][1][1])),[1,2,3]);
    assert.equal(loop.filter(b=>code(b)==='LG advance').length,1);assert.equal(loop.filter(b=>code(b)==='LG render').length,1);
    assert.ok(!loop.some(b=>code(b)==='LG demo'));
  });
  test('Importable component exposes one persistent raw Glass setup and excludes the Studio demo',()=>{
    const blocks=component.blocks,first=entryHat(blocks);checkEntry(first);
    const setup=chain(blocks,first.next);assert.equal(code(setup[0]),'LG initialize');
    const forever=setup.find(b=>b.opcode==='control_forever');
    const loop=chain(blocks,forever.inputs.SUBSTACK[1]);
    if(loop[0].opcode==='control_if_else'){
      const raw=chain(blocks,loop[0].inputs.SUBSTACK2[1]);
      assert.ok(chain(blocks,raw[0].inputs.SUBSTACK[1]).some(b=>code(b)===API));
      assert.deepEqual(raw.slice(1).map(code),['LG advance','LG render']);
      assert.equal(loop[1].opcode,'control_wait');
    } else {
      assert.equal(code(setup[1]),API);
      assert.deepEqual(loop.map(b=>code(b)||b.opcode),['LG advance','LG render','control_wait']);
    }
    assert.ok(Object.values(blocks).filter(b=>b.opcode==='event_whenkeypressed')
      .every(b=>['g','r'].includes(b.fields.KEY_OPTION[0])));
    assert.ok(!Object.values(blocks).some(b=>b.mutation&&['LG demo','LG demo targets'].includes(b.mutation.proccode)));
  });
  const stage=project.targets.find(t=>t.isStage),bare=new JSZip();
  bare.file('project.json',JSON.stringify({targets:[stage],monitors:[],extensions:[],meta:project.meta}));
  for(const costume of stage.costumes)bare.file(costume.md5ext,await projectArchive.file(costume.md5ext).async('uint8array'));
  vm=new VM();vm.attachStorage(new Storage());vm.setCompilerOptions({enabled:true});
  await vm.loadProject(await bare.generateAsync({type:'nodebuffer'}));
  await vm.addSprite(fs.readFileSync(componentPath));
  let ticks=0;const clock=vm.runtime.ioDevices.clock._projectTimer;clock.nowObj={now:()=>ticks*1000/30};clock.startTime=0;
  const tick=(n=1)=>{for(let i=0;i<n;i++){ticks++;vm.runtime._step();}};
  test('Native VM addSprite imports the sprite archive and green flag runs its single component',()=>{
    assert.equal(vm.runtime.targets.filter(t=>!t.isStage).length,1);assert.equal(vm.runtime.targets.find(t=>!t.isStage).getName(),sprite);assert.ok(vm.runtime._primitives.pen_penDown);
    vm.greenFlag();tick(5);near(get('Frames'),5);enterGlassDemo(tick);near(list('active').filter(x=>Number(x)===1).length,1);near(at('w'),156);near(at('h'),96);near(at('r'),24);
    assert.ok(vm.runtime.threads.some(t=>t.isCompiled));assert.ok(list('field').length>1000);
  });
  test('Imported single component accepts a later API update without demo code overwriting it',()=>{
    glass({id:1,x:50,y:20,shape:3,width:84,height:33,transition:.3});
    const target=vm.runtime.targets.find(t=>t.getName()===sprite);
    const main=entryHat(target.blocks._blocks);
    const setup=chain(target.blocks._blocks,main.next),forever=setup.find(b=>b.opcode==='control_forever');
    // invoke() deliberately pauses all scripts; resume precisely the user's existing forever stack.
    vm.runtime._pushThread(forever.id,target,{stackClick:true});tick(45);
    near(at('x'),50,.01);near(at('y'),20,.01);near(at('w'),84,.001);near(at('h'),84,.001);near(at('r'),42,.001);near(at('tx'),50);near(at('ty'),20);
    assert.equal(list('active').filter(x=>Number(x)===1).length,1);
    vm.postIOData('keyboard',{key:'3',isDown:true});vm.postIOData('keyboard',{key:'3',isDown:false});tick(2);near(at('w'),84,.001);
  });
  vm.stopAll();
}

(async()=>{
  await run(false);await run(true);await validatePackaging();
  for(const artifact of Object.values(result.artifacts))assert.equal(digest(artifact.path),artifact.sha256,'Artifact changed during final tests');
  result.passed=true;
})().catch(error=>{result.errors.push({mode,error:String(error),stack:error.stack?.split('\n').slice(0,5)});result.passed=false;vm?.stopAll();}).finally(()=>{
  const output=process.argv[3]||'research/runtime_validation.json';fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));process.exit(result.passed?0:1);
});
