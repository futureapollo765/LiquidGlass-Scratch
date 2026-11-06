/** Check the visible contour of the original right-facing chevron through a quarter turn. */
const fs=require('node:fs'), assert=require('node:assert/strict'), crypto=require('node:crypto');
const H=require('./vm_harness.cjs');
const [file,output]=process.argv.slice(2);
const result={sha256:crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),angles:[]};
(async()=>{
    const vm=await H.loadProject(file,{compiler:true}),target=vm.runtime.targets.find(t=>t.getName()==='Liquid Glass');
    const variable=n=>H.getVariable(vm,'Liquid Glass',n);
    let strokes=[];
    vm.runtime.renderer={createPenSkin:()=>1,createDrawable:()=>2,updateDrawableSkinId(){},draw(){},pick:()=>-1,
        penPoint(){},penStamp(){},penClear(){},penLine(_skin,a,x,y,u,v){
            if(a.color4f[0]>.8 && a.color4f[3]>.001)strokes.push({name:target.sprite.costumes[target.currentCostume].name,from:[x,y],to:[u,v]});
        }};
    H.invoke(vm,'Liquid Glass','LG initialize',[]);
    for(const [n,v] of Object.entries({'UI cx':38,'UI cy':-17,'UI ink scale x':1.4,'UI ink scale y':.8,'UI ink opacity':.83}))
        variable(n).value=v;
    for(const angle of [0,23,45,72,90,45,0]){
        strokes=[];H.invoke(vm,'Liquid Glass','UI disclosure facing %s',[angle]);
        assert.equal(strokes.length,2,'The foreground chevron must contain exactly its two original segments');
        const theta=angle*Math.PI/180;
        const points=[[-2,5],[3,0],[-2,-5]].map(([x,y])=>[
            38+1.4*(x*Math.cos(theta)+y*Math.sin(theta)), -17+.8*(y*Math.cos(theta)-x*Math.sin(theta))]);
        for(let i=0;i<2;i++){
            assert.equal(strokes[i].name,'UI icon next');
            for(const [end,j] of [['from',i],['to',i+1]])for(let k=0;k<2;k++){
                assert.ok(Math.abs(strokes[i][end][k]-points[j][k])<.001,`Angle ${angle}, ${end} mismatch`);
            }
        }
        result.angles.push({angle,tip:strokes[0].to});
    }
    vm.stopAll();result.passed=true;
})().catch(e=>{result.error=String(e.stack||e);result.passed=false;}).finally(()=>{
    fs.writeFileSync(output,JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));process.exit(result.passed?0:1);
});
