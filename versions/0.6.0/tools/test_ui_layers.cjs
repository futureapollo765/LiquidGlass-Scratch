#!/usr/bin/env node
/** Exercise nested menus through real green-flag, mouse, shader and foreground paths. */
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');
const H = require('./vm_harness.cjs');

const [projectFile, outputFile] = process.argv.slice(2);
if (!outputFile) throw new Error('Usage: node test_ui_layers.cjs Studio.sb3 report.json');
const items = 'Help|Quit|Work>ZFolder>Jet|Work>ZFolder>Kiwi|Work>Archive';
const hash = filename => crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');
const report = {project:projectFile, sha256:hash(projectFile), fixtureItems:items,
    fixture:'In-memory menu-only scene. Remove the example sidebar and button calls, retain their public definitions, and set the visible Menu options input to a two-level hierarchy.',
    checks:[], transitions:[]};
const near = (a,b,t=.1) => assert.ok(Math.abs(Number(a)-Number(b))<=t, `Expected ${a} within ${t} of ${b}`);
function check(name, callback) { callback(); report.checks.push({name,passed:true}); }

async function makeScene() {
    const {VM,Storage,JSZip} = H.libraries();
    const zip = await JSZip.loadAsync(fs.readFileSync(projectFile));
    const doc = JSON.parse(await zip.file('project.json').async('string'));
    const source = doc.targets.find(t=>t.name==='Liquid Glass');
    const proto = Object.values(source.blocks).find(b=>b?.opcode==='procedures_prototype'&&b.mutation.proccode.startsWith('Menu %s '));
    const argNames=JSON.parse(proto.mutation.argumentnames), ids=JSON.parse(proto.mutation.argumentids);
    const choices=ids[argNames.indexOf('items')];
    let substitutions=0;
    for(const block of Object.values(source.blocks)) {
        if(block?.opcode==='procedures_call' && block.mutation.proccode===proto.mutation.proccode) {
            const binding=block.inputs[choices];
            if(binding?.[0]===1 && binding[1]?.[0]===10 && String(binding[1][1]).includes('Background>Photo')) {
                binding[1][1]=items; substitutions++;
            }
        }
    }
    assert.equal(substitutions,1,'Expected a single configurable menu in the demo');
    function removeOwnedInput(id) {
        const b=source.blocks[id]; if(!b) return;
        for(const input of Object.values(b.inputs||{})) for(const child of input.slice(1)) {
            if(typeof child==='string') removeOwnedInput(child);
        }
        delete source.blocks[id];
    }
    let removed=0;
    for(const [id,b] of Object.entries(source.blocks)) {
        if(b?.opcode!=='procedures_call' || !/^(Background|Button) %s /.test(b.mutation.proccode)) continue;
        if(!b.parent || !b.next || source.blocks[b.parent]?.next!==id) continue;
        source.blocks[b.parent].next=b.next; source.blocks[b.next].parent=b.parent;
        removeOwnedInput(id); removed++;
    }
    assert.equal(removed,2);
    zip.file('project.json',JSON.stringify(doc));
    const vm=new VM(); vm.attachStorage(new Storage());
    await vm.loadProject(await zip.generateAsync({type:'nodebuffer'}));
    vm.setCompilerOptions({enabled:true});
    const sprite=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass');
    const errors=[]; vm.on('COMPILE_ERROR',(...args)=>errors.push(args.map(String)));
    const variable = n=>H.getVariable(vm,'Liquid Glass',n);
    const get = n=>variable(n).value;
    const set = (n,x)=>{variable(n).value=x;};
    let now=0, elapsed=0, stamps=[], maskAlpha=0, sequence=0, rootPixel=null;
    const probes=[];
    const clock=vm.runtime.ioDevices.clock._projectTimer;
    clock.nowObj={now:()=>now}; clock.startTime=0;
    function stroke(attrs,x,y,u,v) {
        sequence++;
        const costume=sprite.sprite.costumes[sprite.currentCostume]?.name || '';
        if(attrs.color4f[0]>.9 && attrs.color4f[3]>.01 && /^(UI glyph |UI icon )/.test(costume)) {
            stamps.push({costume,x:Number(get('UI letter world x')),y:Number(get('UI letter world y')),
                ghost:100*(1-Number(get('UI ink opacity'))),owner:Number(get('UI art id')),layer:Number(get('UI draw layer'))});
        }
        const rgb=attrs.color4f.slice(0,3).map(c=>Math.round(c*255));
        if(rgb[0]===36 && rgb[1]===48 && rgb[2]===68) maskAlpha=Math.max(maskAlpha,attrs.color4f[3]);
        if(Math.abs((x+u)/2-60)<1e-5 && Math.abs(y-80)<1e-5 &&
            Math.abs(v-80)<1e-5 && attrs.diameter>2 && attrs.color4f[3]>.95) rootPixel=rgb;
        // Every tracked point lies well below the only public component.
        // A real line covering that stage point therefore belongs to child
        // art whether the VM paints it separately or in its retained band.
        if(!probes.length || attrs.color4f[3]<.02) return;
        const dx=u-x,dy=v-y;
        for(const p of probes) {
            const t=dx||dy?Math.max(0,Math.min(1,((p.x-x)*dx+(p.y-y)*dy)/(dx*dx+dy*dy))):0;
            if(Math.hypot(p.x-x-t*dx,p.y-y-t*dy)<attrs.diameter/2-.05) p.lastPrivate=sequence;
        }
    }
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},
        penClear(){},penPoint(_skin,attrs,x,y){stroke(attrs,x,y,x,y);},
        penLine(_skin,attrs,x,y,u,v){stroke(attrs,x,y,u,v);},pick:()=>-1,
        penStamp() {
            sequence++;
            const costume=sprite.sprite.costumes[sprite.currentCostume]?.name || '';
            if(costume.startsWith('LG strip ')) {
                for(const p of probes) if(p.y>=sprite.y-4 && p.y<sprite.y+4) p.lastClean=sequence;
            }
            if(costume.startsWith('UI glyph ') || costume.startsWith('UI icon '))
                stamps.push({costume,x:Number(sprite.x),y:Number(sprite.y),ghost:Number(sprite.effects.ghost)||0,
                    owner:Number(get('UI art id')),layer:Number(get('UI draw layer'))});
        }};
    function tick() {
        now+=1000/30; elapsed++; stamps=[]; maskAlpha=0; vm.runtime._step();
        return {tick:elapsed,stamps:[...stamps],maskAlpha,rootPixel};
    }
    function until(predicate, label, max=180) {
        for(let i=0;i<max;i++) { if(predicate()) return; tick(); }
        assert.ok(predicate(),`Timed out waiting for ${label}`);
    }
    function mouse(x,y,down) { vm.postIOData('mouse',{x:x+240,y:180-y,canvasWidth:480,canvasHeight:360,isDown:down}); }
    function list(name) { return get('UI layer '+name); }
    function layer(path) {
        const at=list('path').findIndex((p,i)=>p===path && Number(list('owner')[i])===3);
        if(at<0) return null;
        const val=n=>Number(list(n)[at]);
        return {index:at+1,path,parent:list('parent')[at],row:val('row'),p:val('p'),goal:val('goal'),
            x:val('x'),y:val('y'),w:val('w'),h:val('h'),pitch:val('h')/(val('rows')+1),dim:val('dim')};
    }
    function root() {
        const val=n=>Number(get(n)[2]);
        return {index:0,path:'',x:val('x'),y:val('y'),w:val('w')*val('scaleX'),
            h:val('h')*val('scaleY'),pitch:val('UI row height')*val('h')*val('scaleY')/val('UI expanded height'),dim:val('UI menu dim')};
    }
    function row(path) {
        const at=get('UI row path').findIndex((p,i)=>p===path && Number(get('UI row id')[i])===3);
        assert.ok(at>=0,`Missing option ${path}: ${JSON.stringify(get('UI row path'))}`);
        const index=Number(get('UI row index')[at]), owner=Number(get('UI row layer')[at]);
        const panel=owner ? layer(list('path')[owner-1]):root();
        assert.ok(panel);
        return {path,index,owner,x:panel.x,y:panel.y+panel.h/2-(index+.5)*panel.pitch};
    }
    function header(panel) { return {index:0,owner:panel.index,x:panel.x,y:panel.y+panel.h/2-.5*panel.pitch}; }
    function press(hit) {
        mouse(hit.x,hit.y,true);
        until(()=>Number(get('UI pressed id'))===3 && Number(get('UI pressed row'))===hit.index
            && Number(get('UI pressed layer'))===hit.owner,`native hit on layer ${hit.owner}, row ${hit.index}`);
    }
    function release(hit) { mouse(hit.x,hit.y,false); }
    return {vm,sprite,errors,get,set,tick,until,mouse,layer,root,row,header,press,release,list,probes};
}

function observe(scene, path, hit, direction) {
    const frames=[];
    let sentHover=false, intermediateHit=null;
    scene.press(hit); scene.release(hit);
    for(let i=0;i<100;i++) {
        const ink=scene.tick();
        const layer=scene.layer(path);
        frames.push({tick:ink.tick,layer,root:scene.root(),ink:ink.stamps,maskAlpha:ink.maskAlpha,rootPixel:ink.rootPixel});
        if (direction==='push' && layer && layer.p>.12 && layer.p<.95) {
            if(sentHover && Number(scene.get('UI hover layer'))===layer.index && Number(scene.get('UI hover row'))===0) {
                intermediateHit=layer.p;
            }
            if(!sentHover) {
                const header=scene.header(layer);
                scene.mouse(header.x,header.y,false); sentHover=true;
            }
        }
        if(direction==='push' && layer && layer.p>=.999 && frames.length>8) break;
        if(direction==='pop' && !layer && frames.some(f=>f.layer)) break;
    }
    const phases=frames.filter(f=>f.layer).map(f=>f.layer.p);
    assert.ok(phases.some(p=>p>.01 && p<.99),`No intermediate ${direction} phase for ${path}`);
    if(direction==='push') assert.ok(intermediateHit!==null,`The growing panel's visible header did not receive the pointer: ${path}`);
    report.transitions.push({path,direction,first:frames[0].layer,
        phases:phases.map(p=>+p.toFixed(4)),intermediateHit,last:frames.at(-1).layer});
    return frames;
}

async function main() {
    const s=await makeScene();
    s.mouse(215,-150,false); s.vm.greenFlag(); s.tick();
    s.until(()=>Number(s.get('Frames'))>=1,'first UI frame');
    s.set('Quality',4);
    const initialEvents=Number(s.get('UI event number'));
    const compact={owner:0,index:0,x:s.root().x,y:s.root().y};
    s.press(compact); s.release(compact);
    const opening=[];
    for(let i=0;i<90;i++) {
        const ink=s.tick();
        opening.push({fade:s.get('UI menu open fade')[2],h:s.root().h,ink:ink.stamps,rootPixel:ink.rootPixel});
        if(Number(s.get('UI open')[2])===1 && Math.abs(s.root().h-136)<.3) break;
    }
    check('Launcher and expanded menu content fade while the root changes shape',()=>{
        assert.ok(opening.some(f=>f.fade>.01 && f.fade<.99 && f.h>42 && f.h<136
            && f.ink.some(g=>g.owner===3 && g.ghost>1 && g.ghost<99)));
        near(s.root().h,136,.3);
    });
    const calling=s.row('Work'), rootBefore=s.root();
    const first=observe(s,'Work',calling,'push');
    check('The first child grows from its calling row while preserving the root menu',()=>{
        const start=first.find(f=>f.layer && f.layer.p>.001)?.layer, end=first.at(-1).layer;
        assert.ok(start && end && end.p>=.999);
        assert.equal(start.parent,''); assert.equal(start.row,calling.index);
        assert.ok(start.p<.4,`Child appeared abruptly at progress ${start.p}`);
        near(start.y,calling.y,12);
        assert.ok(start.h<end.h-15);
        assert.ok(end.h<rootBefore.h-15,'Parent and first child should have different row geometry');
        assert.equal(s.row('Quit').owner,0); assert.equal(s.row('Work>ZFolder').owner,end.index);
        assert.ok(first.at(-1).root.dim>.2,'Root material did not dim');
        assert.ok(first.some(f=>f.root.dim>0 && f.root.dim<first.at(-1).root.dim-.01));
        assert.deepEqual(s.get('active').slice(3,8).map(Number),[0,0,0,0,0]);
        assert.ok(Math.hypot(s.root().x-rootBefore.x,s.root().y-rootBefore.y)>1,
            'The parent did not move under the new child');
    });
    check('Native layer painting dims the parent, fades the child’s content, and draws it in front',()=>{
        const before=opening.at(-1).rootPixel, after=first.at(-1).rootPixel;
        const darkened=before && after && before.some((c,i)=>c>after[i]+3);
        assert.ok(first.some(f=>f.maskAlpha>.15) || darkened,
            `No rendered parent dimming detected: ${JSON.stringify({before,after})}`);
        report.parentDim={before,after,maskAlpha:Math.max(...first.map(f=>f.maskAlpha))};
        assert.ok(first.some(f=>f.ink.some(g=>g.owner===3 && g.layer===0 && g.ghost>10)),
            'Parent content did not dim');
        assert.ok(first.some(f=>f.ink.some(g=>g.owner===3 && g.layer===1 && g.ghost>1 && g.ghost<99)),
            'Child content never passed through a partially visible state');
        assert.ok(first.some(f=>{
            const rootEnd=f.ink.findLastIndex(g=>g.owner===3 && g.layer===0);
            const childStart=f.ink.findIndex(g=>g.owner===3 && g.layer===1);
            return rootEnd>=0 && childStart>rootEnd;
        }));
    });
    const exposed=s.layer('Work');
    for(const dx of [-8,0,8]) for(const dy of [8,13]) {
        s.probes.push({x:exposed.x+dx,y:exposed.y-exposed.h/2+dy,lastPrivate:0,lastClean:0});
    }
    assert.ok(s.probes.every(p=>p.y<s.root().y-s.root().h/2-1),'Fixture must expose child pixels beyond its parent');
    const deeperHit=s.row('Work>ZFolder');
    const deeper=observe(s,'Work>ZFolder',deeperHit,'push');
    check('A second-level menu starts from its parent row and receives independent geometry, dimming and hit ownership',()=>{
        const firstChild=s.layer('Work'), grandchild=s.layer('Work>ZFolder');
        assert.ok(firstChild && grandchild && grandchild.index!==firstChild.index);
        assert.equal(grandchild.parent,'Work'); assert.equal(grandchild.row,deeperHit.index);
        assert.ok(firstChild.dim>.2);
        assert.equal(s.row('Work>ZFolder>Jet').owner,grandchild.index);
        assert.ok(deeper.some(f=>f.layer?.p>0 && f.layer.p<1));
        s.mouse(s.row('Work>ZFolder>Jet').x,s.row('Work>ZFolder>Jet').y,false); s.tick();
        assert.equal(Number(s.get('UI hover layer')),grandchild.index);
        assert.equal(Number(s.get('UI hover row')),s.row('Work>ZFolder>Jet').index);
    });
    const pop=observe(s,'Work>ZFolder',s.header(s.layer('Work>ZFolder')),'pop');
    check('Back animates the selected child into its source row and restores the preceding page',()=>{
        assert.ok(pop.some(f=>f.layer && f.layer.goal===0));
        assert.equal(s.layer('Work>ZFolder'),null); assert.ok(s.layer('Work'));
        assert.equal(s.get('UI page')[2],'Work');
        assert.equal(Number(s.get('UI event number')),initialEvents);
    });
    observe(s,'Work',s.header(s.layer('Work')),'pop');
    s.until(()=>Math.abs(s.root().h-136)<.2,'root geometry to settle after its child retreats');
    check('Returning to the root restores its original brightness and dimensions without delivering a leaf action',()=>{
        assert.equal(s.get('UI page')[2],''); assert.equal(s.layer('Work'),null);
        near(s.root().dim,0,.02); near(s.root().h,rootBefore.h,.5);
        assert.equal(Number(s.get('UI event number')),initialEvents);
    });
    check('Popping the final child restores exposed child pixels outside the root on a menu-only stage',()=>{
        const painted=s.probes.filter(p=>p.lastPrivate>0);
        assert.ok(painted.length>=3,'No tracked probe was painted by private glass');
        assert.ok(painted.every(p=>p.lastClean>p.lastPrivate),JSON.stringify(painted));
        report.restoredProbes=painted;
    });
    observe(s,'Work',s.row('Work'),'push'); observe(s,'Work>ZFolder',s.row('Work>ZFolder'),'push');
    const leaf=s.row('Work>ZFolder>Jet'); s.press(leaf); s.release(leaf);
    s.until(()=>Number(s.get('UI event number'))===initialEvents+1,'selection through native child hit testing');
    check('A nested leaf delivers exactly one action with the complete path and original public menu ID',()=>{
        assert.equal(s.get('UI action'),'Work>ZFolder>Jet'); assert.equal(s.get('UI path'),'Work>ZFolder>Jet');
        assert.equal(Number(s.get('UI source')),3);
        for(let i=0;i<65;i++) s.tick();
        assert.equal(Number(s.get('UI event number')),initialEvents+1);
        assert.equal(Number(s.get('UI open')[2]),0);
    });
    assert.deepEqual(s.errors,[]); s.vm.stopAll();
    assert.equal(hash(projectFile),report.sha256); report.passed=true;
}
main().catch(e=>{report.passed=false;report.error=String(e.stack||e);}).finally(()=>{
    fs.mkdirSync(path.dirname(outputFile),{recursive:true});
    fs.writeFileSync(outputFile,JSON.stringify(report,null,2)+'\n');
    console.log(JSON.stringify({passed:report.passed,checks:report.checks.length,error:report.error},null,2));
    process.exit(report.passed?0:1);
});
