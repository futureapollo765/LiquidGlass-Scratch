"""Native Liquid Glass material sampling, smooth-union mixing and cache rebuild.

apply_material(target) patches a saved Studio renderer or sprite. Seed tables are
small prefiltered samples derived from the target's own background RGB lists.
The shipped Scratch rebuild block repeats the same two filters on edited lists.
"""
import copy
import math
from .stable_pen import Native, Node, arg, iff, op
from .ui_components import (UIProgram, eq, gt, lt, AND, OR, NOT, add, sub, mul, div,
                            join, length, letter, rnd, floor, abs_, repeat, maximum, minimum)

MATERIAL = 'LG material %s tint color %s transparency %s brightness %s blur %s'
SAMPLE = 'LG material sample x %s y %s blur %s'
SAMPLE_BG = 'LG material sample x %s y %s blur %s background %s'
COMPOSITE = 'LG material composite tint %s shine %s opacity %s red %s green %s blue %s brightness %s'
REBUILD = 'LG rebuild blur %s'
LEVEL = 'LG filtered grid level %s'
BUILD = 'LG generate blur level %s'
SPECS = {MATERIAL:('slot','tint color','transparency','brightness','blur'),
         SAMPLE:('x','y','blur'), SAMPLE_BG:('x','y','blur','background'),
         COMPOSITE:('tint','shine','opacity','red','green','blue','brightness'),
         LEVEL:('level',), REBUILD:('background',), BUILD:('level',)}
RADII = (2,6,12,20)
STEPS = (3,8,12,16)
MATERIAL_LANES = ('Blur','Alpha','Red','Green','Blue','Brightness')
PIXEL_LISTS = tuple('pixelMat'+lane for lane in MATERIAL_LANES)


def gaussian_kernel(radius, step):
    # Account for the finite tile area and linear reconstruction filter. The
    # remainder of the requested variance is the discrete Gaussian on the grid.
    sigma = math.sqrt(radius*radius - step*step/4) / step
    extent = math.ceil(3*sigma)
    weights = [math.exp(-i*i/(2*sigma*sigma)) for i in range(-extent, extent+1)]
    total = sum(weights)
    return extent, [w/total for w in weights]


def pack(r,g,b):
    return ((int(r+.5)<<16) + (int(g+.5)<<8) + int(b+.5))


def seed_level(source, step, kernel):
    cols, rows = math.ceil(480/step), math.ceil(360/step)
    tiles = []
    for y in range(rows):
        for x in range(cols):
            red=green=blue=0
            for yy in range(y*step,(y+1)*step):
                line=min(359,yy)*480
                for xx in range(x*step,(x+1)*step):
                    c=source[line+min(479,xx)];red+=c>>16;green+=(c>>8)&255;blue+=c&255
            count=step*step
            tiles.append(pack(red/count,green/count,blue/count))
    extent=len(kernel)//2
    for horizontal in (True,False):
        filtered=[]
        for y in range(rows):
            for x in range(cols):
                red=green=blue=0.
                for tap,weight in enumerate(kernel):
                    delta=tap-extent
                    xx=min(cols-1,max(0,x+delta)) if horizontal else x
                    yy=y if horizontal else min(rows-1,max(0,y+delta))
                    c=tiles[yy*cols+xx];red+=(c>>16)*weight;green+=((c>>8)&255)*weight;blue+=(c&255)*weight
                filtered.append(pack(red,green,blue))
        tiles=filtered
    return tiles


def set_list(n,name,data):
    ident=n.storage(name,True)[1]
    n.target['lists'][ident][1]=list(data)


def seed_tables(n):
    start=1;kernel_start=1;metadata={name:[] for name in
        ('matLevelRadius','matLevelStep','matLevelCols','matLevelRows','matLevelStart',
         'matKernelStart','matKernelExtent','matKernel')}
    colors=[]
    for key in ('Original RGB','Grid RGB'):
        rgb=n.target['lists'][n.storage(key,True)[1]][1]
        if len(rgb)!=172800:raise ValueError(key+' must contain 480×360 packed RGB entries')
        colors.append([max(0,min(16777215,int(v))) for v in rgb])
    levels=[[],[]]
    for r,s in zip(RADII,STEPS):
        cols,rows=math.ceil(480/s),math.ceil(360/s);extent,kernel=gaussian_kernel(r,s)
        for key,v in zip(list(metadata)[:-1],(r,s,cols,rows,start,kernel_start,extent)):
            metadata[key].append(v)
        metadata['matKernel'].extend(kernel)
        for store,source in zip(levels,colors):store.extend(seed_level(source,s,kernel))
        start+=cols*rows;kernel_start+=len(kernel)
    for key,values in metadata.items():set_list(n,key,values)
    for key,values in zip(('matBlurPhoto','matBlurGrid'),levels):set_list(n,key,values)
    for name in ('matBlurPhoto B','matBlurGrid B','matBuildTiles','matBuildHorizontal'):set_list(n,name,[])
    set_list(n,'matActiveBank',[0,0]);set_list(n,'matHex',list('0123456789abcdef'))


class MaterialWriter(UIProgram):
    def __init__(self,target):
        # The material pass does not declare UI broadcasts or touch UI scripts.
        Native.__init__(self,target)
        self.next_id=max((int(k[9:]) for k in self.blocks if k.startswith('lgpresent') and k[9:].isdigit()),default=0)
        self.exporting=False;self.bids={}
        self.procs={b['mutation']['proccode']:b['mutation'] for b in self.blocks.values()
                    if isinstance(b,dict) and b.get('opcode')=='procedures_prototype'}

    def clone_statement(self,key,parent,mapping):
        """Copy one numeric fold/cache statement, including its reporter tree."""
        original=self.blocks[key]; self.next_id+=1; new='lgpresent'+str(self.next_id)
        block=copy.deepcopy(original);self.blocks[new]=block
        block.update(parent=parent,next=None);block.pop('comment',None)
        for k,field in block['fields'].items():
            if k in ('VARIABLE','LIST') and field[0] in mapping:
                block['fields'][k]=self.storage(mapping[field[0]],k=='LIST')
        for binding in block['inputs'].values():
            for j,ref in enumerate(binding[1:],1):
                if isinstance(ref,str):binding[j]=self.clone_statement(ref,new,mapping)
                elif isinstance(ref,list) and len(ref)>=3 and ref[0] in (12,13) and ref[1] in mapping:
                    binding[j]=[ref[0],*self.storage(mapping[ref[1]],ref[0]==13)]
        return new

    def owned(self,code):
        found=set();pending=[self.blocks[self.definition(code)].get('next')]
        while pending:
            key=pending.pop()
            if not key or key in found:continue
            found.add(key);b=self.blocks[key];pending.append(b.get('next'))
            for binding in b['inputs'].values():pending.extend(r for r in binding[1:] if isinstance(r,str))
        return found


def rgb(c,ch):
    if ch=='R':return floor(div(c,65536))
    if ch=='G':return Node('operator_mod',{'NUM1':floor(div(c,256)),'NUM2':256})
    return Node('operator_mod',{'NUM1':c,'NUM2':256})


def packed(r,g,b): return add(add(mul(rnd(r),65536),mul(rnd(g),256)),rnd(b))

def material_set(n):
    v=n.v;i=v('matSlot');token=arg('tint color')
    css=[n.set('matPacked',0),n.set('matDigitAt',2),n.set('matValid',1),
         repeat(6,[n.set('matDigit',n.list_op('data_itemnumoflist','matHex',ITEM=letter(v('matDigitAt'),token))),
             iff(eq(v('matDigit'),0),[n.set('matValid',0)]),
             n.set('matPacked',add(mul(v('matPacked'),16),sub(v('matDigit'),1))),n.change('matDigitAt',1)]),
         iff(eq(v('matValid'),0),[n.set('matPacked',0xDCEFFF)])]
    changed=OR(NOT(eq(n.item('matToken',i),join('@',token))),OR(NOT(eq(n.item('matAlpha',i),v('matA'))),
        OR(NOT(eq(n.item('matBlur',i),v('matRadius'))),NOT(eq(n.item('matBrightness',i),v('matBri'))))))
    update=[iff(AND(eq(letter(1,token),'#'),eq(length(token),7)),css,[n.set('matPacked',rnd(add(token,0))),*n.clip('matPacked',0,16777215)]),
            n.replace('matToken',i,join('@',token)),n.replace('matBlur',i,v('matRadius')),
            n.replace('matAlpha',i,v('matA')),n.replace('matBrightness',i,v('matBri')),
            *[n.replace('mat'+name,i,mul(v('matA'),rgb(v('matPacked'),ch))) for name,ch in zip(('Red','Green','Blue'),'RGB')],
            n.change('matRevision',1)]
    return [n.set('matSlot',rnd(arg('slot'))),*n.clip('matSlot',1,8),
            n.set('matA',sub(1,div(arg('transparency'),100))),*n.clip('matA',0,1),
            n.set('matRadius',add(arg('blur'),0)),*n.clip('matRadius',0,20),
            n.set('matBri',div(arg('brightness'),100)),*n.clip('matBri',-1,1),iff(changed,update)]


def bank_read(n,out,index):
    v=n.v
    return iff(eq(v('matReadBG'),2),[iff(eq(n.item('matActiveBank',2),1),
            [n.set(out,n.item('matBlurGrid B',index))],[n.set(out,n.item('matBlurGrid',index))])],
            [iff(eq(n.item('matActiveBank',1),1),[n.set(out,n.item('matBlurPhoto B',index))],
                 [n.set(out,n.item('matBlurPhoto',index))])])


def grid_sample(n):
    v=n.v;level=arg('level');x=v('matTileX');y=v('matTileY')
    body=[n.set('matGridStep',n.item('matLevelStep',level)),n.set('matCols',n.item('matLevelCols',level)),
          n.set('matRows',n.item('matLevelRows',level)),n.set('matTileX',sub(div(add(v('matTexX'),.5),v('matGridStep')),.5)),
          n.set('matTileY',sub(div(add(v('matTexY'),.5),v('matGridStep')),.5)),
          *n.clip('matTileX',0,sub(v('matCols'),1)),*n.clip('matTileY',0,sub(v('matRows'),1)),
          n.set('matFX',sub(x,floor(x))),n.set('matFY',sub(y,floor(y))),
          n.set('matBase',add(n.item('matLevelStart',level),add(floor(x),mul(floor(y),v('matCols'))))),
          n.set('matRight',lt(floor(x),sub(v('matCols'),1))),
          n.set('matBelow',mul(v('matCols'),lt(floor(y),sub(v('matRows'),1))))]
    # Interpolate each channel separately; interpolating packed RGB leaks carries.
    for ch in 'RGB':body.append(n.set('matGrid'+ch,0))
    for off,weight in [(0,mul(sub(1,v('matFX')),sub(1,v('matFY')))),
                       (v('matRight'),mul(v('matFX'),sub(1,v('matFY')))),
                       (v('matBelow'),mul(sub(1,v('matFX')),v('matFY'))),
                       (add(v('matRight'),v('matBelow')),mul(v('matFX'),v('matFY')))]:
        body.extend([bank_read(n,'matTap',add(v('matBase'),off)),n.set('matWeight',weight),
            *[n.change('matGrid'+ch,mul(rgb(v('matTap'),ch),v('matWeight'))) for ch in 'RGB']])
    return body


def sampling(n):
    v=n.v;r=v('matSampleRadius')
    chosen=[n.set('matHi',1),repeat(3,[iff(gt(r,n.item('matLevelRadius',v('matHi'))),[n.change('matHi',1)])]),
            n.set('matLowRadius',0),iff(AND(gt(v('matHi'),1),lt(r,n.item('matLevelRadius',v('matHi')))),[
                n.set('matLowRadius',n.item('matLevelRadius',sub(v('matHi'),1))),
                n.call(LEVEL,sub(v('matHi'),1)),*[n.set('matLow'+ch,v('matGrid'+ch)) for ch in 'RGB']]),
            n.set('matMix',div(sub(r,v('matLowRadius')),sub(n.item('matLevelRadius',v('matHi')),v('matLowRadius')))),
            n.call(LEVEL,v('matHi')),*[n.set(ch,add(v('matLow'+ch),mul(v('matMix'),sub(v('matGrid'+ch),v('matLow'+ch))))) for ch in 'RGB'],
            n.set('color',packed(v('R'),v('G'),v('B')))]
    return [n.set('matReadBG',arg('background')),n.set('matTexX',add(arg('x'),240)),*n.clip('matTexX',0,479),
            n.set('matTexY',sub(179,arg('y'))),*n.clip('matTexY',0,359),
            n.set('sampleX',maximum(-240,minimum(239,rnd(arg('x'))))),
            n.set('sampleY',maximum(-180,minimum(179,rnd(arg('y'))))),
            n.set('sampleIndex',add(add(mul(sub(179,v('sampleY')),480),v('sampleX')),241)),
            iff(eq(v('matReadBG'),2),[n.set('color',n.item('Grid RGB',v('sampleIndex')))],
                [n.set('color',n.item('Original RGB',v('sampleIndex')))]),
            *[n.set(ch,rgb(v('color'),ch)) for ch in 'RGB'],n.set('matSampleRadius',arg('blur')),*n.clip('matSampleRadius',0,20),
            iff(gt(r,0),[*[n.set('matLow'+ch,v(ch)) for ch in 'RGB'],*chosen])]


def composite(n):
    v=n.v;b=arg('brightness');a=arg('opacity');t=arg('tint');s=arg('shine')
    body=[n.set('matLightScale',sub(1,abs_(b))),n.set('matLightAdd',mul(255,maximum(0,b)))]
    for ch,pale,pm in zip('RGB',(220,239,255),('red','green','blue')):
        lit=add(mul(v(ch),v('matLightScale')),v('matLightAdd'))
        legacy=add(mul(lit,sub(1,t)),mul(pale,t))
        body.extend([n.set(ch,add(add(mul(legacy,sub(1,a)),arg(pm)),s)),*n.clip(ch,0,255)])
    return body


def kernel_build(n):
    """Generate one cache level in Scratch. All work buffers are grid-sized."""
    v=n.v;level=arg('level');cs=v('matBuildCols');rs=v('matBuildRows');step=v('matBuildStep')
    src_index=add(add(mul(minimum(v('matPy'),359),480),minimum(v('matPx'),479)),1)
    source=iff(eq(v('matBuildBG'),2),[n.set('matSource',n.item('Grid RGB',src_index))],
               [n.set('matSource',n.item('Original RGB',src_index))])
    reset=[n.set('matSum'+ch,0) for ch in 'RGB']
    tile=repeat(rs,[n.set('matBX',0),repeat(cs,[*reset,n.set('matPy',mul(v('matBY'),step)),
        repeat(step,[n.set('matPx',mul(v('matBX'),step)),repeat(step,[source,
            *[n.change('matSum'+ch,rgb(v('matSource'),ch)) for ch in 'RGB'],n.change('matPx',1)]),n.change('matPy',1)]),
        n.add('matBuildTiles',packed(*[div(v('matSum'+ch),mul(step,step)) for ch in 'RGB'])),n.change('matBX',1)]),n.change('matBY',1)])
    def output(value):
        return iff(eq(v('matBuildBG'),2),[iff(eq(v('matWriteBank'),1),[n.add('matBlurGrid B',value)],[n.add('matBlurGrid',value)])],
                   [iff(eq(v('matWriteBank'),1),[n.add('matBlurPhoto B',value)],[n.add('matBlurPhoto',value)])])
    def convolve(horizontal):
        src='matBuildTiles' if horizontal else 'matBuildHorizontal'
        offset_coord=add(v('matBX' if horizontal else 'matBY'),v('matDelta'))
        clamp_to=cs if horizontal else rs
        src_pos=add(add(mul(v('matBY') if horizontal else v('matCoord'),cs),v('matCoord') if horizontal else v('matBX')),1)
        pixel=packed(*[v('matSum'+ch) for ch in 'RGB'])
        save=n.add('matBuildHorizontal',pixel) if horizontal else output(pixel)
        return [n.set('matBY',0),repeat(rs,[n.set('matBX',0),repeat(cs,[*reset,
            n.set('matDelta',sub(0,v('matExtent'))),n.set('matWeightIndex',n.item('matKernelStart',level)),
            repeat(add(mul(v('matExtent'),2),1),[n.set('matCoord',offset_coord),*n.clip('matCoord',0,sub(clamp_to,1)),
                n.set('matSource',n.item(src,src_pos)),n.set('matBuildWeight',n.item('matKernel',v('matWeightIndex'))),
                *[n.change('matSum'+ch,mul(rgb(v('matSource'),ch),v('matBuildWeight'))) for ch in 'RGB'],
                n.change('matDelta',1),n.change('matWeightIndex',1)]),save,n.change('matBX',1)]),n.change('matBY',1)])]
    return [n.set('matBuildCols',n.item('matLevelCols',level)),n.set('matBuildRows',n.item('matLevelRows',level)),
            n.set('matBuildStep',n.item('matLevelStep',level)),n.set('matExtent',n.item('matKernelExtent',level)),
            n.clear('matBuildTiles'),n.clear('matBuildHorizontal'),n.set('matBY',0),tile,*convolve(True),*convolve(False)]


def rebuild(n):
    v=n.v
    def clear_bank(index):
        return iff(eq(v('matBuildBG'),2),[iff(eq(index,1),[n.clear('matBlurGrid B')],[n.clear('matBlurGrid')])],
                   [iff(eq(index,1),[n.clear('matBlurPhoto B')],[n.clear('matBlurPhoto')])])
    return [iff(eq(v('matBuilding'),0),[n.set('matBuilding',1),n.set('matBuildBG',1),
        iff(eq(arg('background'),2),[n.set('matBuildBG',2)]),
        n.set('matWriteBank',sub(1,n.item('matActiveBank',v('matBuildBG')))),clear_bank(v('matWriteBank')),
        n.set('matBuildLevel',1),repeat(len(RADII),[n.call(BUILD,v('matBuildLevel')),n.change('matBuildLevel',1)]),
        n.replace('matActiveBank',v('matBuildBG'),v('matWriteBank')),n.change('matRevision',1),n.change('screenGeneration',1),
        clear_bank(sub(1,v('matWriteBank'))),n.clear('matBuildTiles'),n.clear('matBuildHorizontal'),n.set('matBuilding',0)])]


def add_fold_lanes(n):
    # The tint lane already has the renderer's exact partition, initial winner,
    # and smooth-union weights. Mirror its statements rather than introducing a
    # separate nearest-component selection (which would form seams at joins).
    roles={'LG sample %s %s':{'outTint','groupTint'},'LG render':{'pixelTint'},
           'LG initialize':{'pixelTint'},'LG shade %s %s %s':{'shadeTint'}}
    if 'UI release buffers' in n.procs:roles['UI release buffers']={'pixelTint'}
    allowed={'data_setvariableto','data_replaceitemoflist','data_deletealloflist','data_addtolist'}
    for code,fields in roles.items():
        count=0
        for key in sorted(n.owned(code)):
            b=n.blocks[key]
            if b['opcode'] not in allowed:continue
            name=next((f[0] for k,f in b['fields'].items() if k in ('VARIABLE','LIST')),None)
            if name not in fields:continue
            count+=1;tail=b['next'];last=key
            for lane in MATERIAL_LANES:
                mapping={'tint':'mat'+lane,'groupTint':'groupMat'+lane,'outTint':'outMat'+lane,
                         'pixelTint':'pixelMat'+lane,'shadeTint':'shadeMat'+lane}
                new=n.clone_statement(key,last,mapping);n.blocks[last]['next']=new;last=new
            n.blocks[last]['next']=tail
            if tail:n.blocks[tail]['parent']=last
        if not count:raise ValueError(f'Missing expected tint fold in {code}')


def replace_shading(n):
    v=n.v;b=n.blocks;seq=n.sequence(n.definition('LG shade %s %s %s'))
    bg=next(key for key in seq if b[key].get('mutation',{}).get('proccode')=='LG background %s %s')
    index=seq.index(bg);decode=seq[index+1:index+4]
    if [b[k]['fields'].get('VARIABLE',[None])[0] for k in decode]!=list('RGB'):
        raise ValueError('Expected original channel decode after background lookup')
    # Reuse the exact refraction coordinate trees, including native user edits.
    before=b[bg]['parent'];after=b[decode[-1]]['next']
    gate=n.emit(iff(gt(v('shadeMatBlur'),0),[n.set('matSampleRadius',0)]),before)
    dummy=b[gate]['inputs']['SUBSTACK'][1];n.remove(dummy)
    sample=n.clone_statement(bg,gate,{})
    old_inputs=b[sample]['inputs'];old_ids=json_ids(b[sample]['mutation'])
    m=n.procs[SAMPLE];new_ids=json_ids(m)
    b[sample]['mutation']={k:copy.deepcopy(m[k]) for k in ('tagName','children','proccode','argumentids','warp')}
    b[sample]['inputs']={new_ids[0]:old_inputs[old_ids[0]],new_ids[1]:old_inputs[old_ids[1]],new_ids[2]:[2,v('shadeMatBlur')]}
    b[gate].update(opcode='control_if_else',next=after);b[gate]['inputs'].update(SUBSTACK=[2,sample],SUBSTACK2=[2,bg])
    b[bg]['parent']=gate;b[decode[-1]]['next']=None;b[before]['next']=gate;b[after]['parent']=gate

    seq=n.sequence(n.definition('LG shade %s %s %s'))
    tint=next(k for k in seq if b[k].get('fields',{}).get('VARIABLE',[None])[0]=='materialTint')
    tail=seq[seq.index(tint)+1:seq.index(tint)+4]
    if [b[k]['fields'].get('VARIABLE',[None])[0] for k in tail]!=list('RGB'):
        raise ValueError('Expected original final R/G/B shading statements')
    after=b[tail[-1]]['next']
    comp=n.call(COMPOSITE,v('materialTint'),v('shine'),v('shadeMatAlpha'),v('shadeMatRed'),v('shadeMatGreen'),v('shadeMatBlue'),v('shadeMatBrightness'))
    gate=n.emit(iff(OR(gt(v('shadeMatAlpha'),0),NOT(eq(v('shadeMatBrightness'),0))),[comp]),tint)
    b[gate].update(opcode='control_if_else',next=after);b[gate]['inputs']['SUBSTACK2']=[2,tail[0]]
    b[tail[0]]['parent']=gate;b[tail[-1]]['next']=None;b[tint]['next']=gate;b[after]['parent']=gate


def json_ids(mutation):
    import json
    return json.loads(mutation['argumentids'])


def has_scene_comparison(n, key):
    b=n.blocks[key]
    if b['opcode']!='control_if':return False
    pending=[b['inputs'].get('CONDITION',[])]; names=set()
    while pending:
        inp=pending.pop()
        for ref in inp[1:]:
            if isinstance(ref,str):
                child=n.blocks[ref];pending.extend(child['inputs'].values())
                for f in child['fields'].values():names.add(f[0])
            elif isinstance(ref,list) and len(ref)>1 and ref[0]==12:names.add(ref[1])
    return {'preparedScene','displayedScene'}<=names


def apply_material(target):
    """Add the shared optics to a saved renderer target without changing its public calls."""
    n=MaterialWriter(target)
    if MATERIAL in n.procs:raise ValueError('The renderer already has a glass material pass')
    for c,args in SPECS.items():n.declare(c,args)
    seed_tables(n)
    for lane in MATERIAL_LANES:
        set_list(n,'mat'+lane,[0]*8);set_list(n,'groupMat'+lane,[0]*8);set_list(n,'pixelMat'+lane,[])
    set_list(n,'matToken',['']*8)
    add_fold_lanes(n)
    replace_shading(n)
    v=n.v
    sample=[iff(eq(v('preparingFrame'),1),[n.set('matSampleBG',v('frameBG'))],
                [n.set('matSampleBG',v('Background'))]),
            n.call(SAMPLE_BG,arg('x'),arg('y'),arg('blur'),v('matSampleBG'))]
    code={MATERIAL:material_set(n),SAMPLE:sample,SAMPLE_BG:sampling(n),COMPOSITE:composite(n),
          LEVEL:grid_sample(n),REBUILD:rebuild(n),BUILD:kernel_build(n)}
    for j,(name,body) in enumerate(code.items()):n.define(name,body,(85040+(j%3)*8000,2400+(j//3)*6500))
    render=n.definition('LG render'); gates=[k for k in n.sequence(render) if has_scene_comparison(n,k)]
    if len(gates)!=1:raise ValueError('Expected exactly one retained-frame signature comparison')
    gate=gates[0];n.attach(n.blocks[gate]['parent'],[n.set('preparedScene',join(v('preparedScene'),join('|material:',v('matRevision'))))],gate)
    # The compact materials computed for a frame are not persistent program data.
    # Keep previous frames on the Pen layer; do not retain six per-pixel arrays
    # simply because Scratch/TurboWarp may save the project after green flag.
    n.attach(n.sequence(render)[-1],[n.clear(name) for name in PIXEL_LISTS],None)
    # A green flag interrupts any previous native rebuild. Recover its lock and
    # private workspaces without disturbing an R reset during a legitimate rebuild.
    cleanup=[n.set('matBuilding',0),n.clear('matBuildTiles'),n.clear('matBuildHorizontal')]
    for bg,a,b in [(1,'matBlurPhoto','matBlurPhoto B'),(2,'matBlurGrid','matBlurGrid B')]:
        cleanup.append(iff(eq(n.item('matActiveBank',bg),1),[n.clear(a)],[n.clear(b)]))
    n.hat('material rebuild startup cleanup',Node('event_whenflagclicked'),cleanup,85040,240)
    return target
