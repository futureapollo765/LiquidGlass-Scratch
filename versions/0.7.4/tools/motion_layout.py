"""Native 0.5.0 migration for tethered controls and menu choreography."""
import json
from .stable_pen import Node, arg, iff
from .ui_components import (UIProgram, eq, gt, lt, AND, OR, NOT, add, sub, mul, div,
                            abs_, math, minimum, maximum, repeat, floor)
from .menu_layers import POSE, HIT, li, put, mix, procs, insert_before, replace_body

ALIGNMENT_INPUTS = ('alignment', 'expanded x', 'expanded y')
ALIGNMENT_DEFAULTS = ('bottom center', 0, 0)
ALIGNMENT_SUFFIX = ''.join(' ' + name + ' %s' for name in ALIGNMENT_INPUTS)
PHASE = 'UI travel curves %s'
GEOMETRY = 'UI menu layout %s at x %s y %s launcher %s width %s height %s radius %s panel %s alignment %s expanded x %s expanded y %s'
PULL = 'UI elastic contact %s'
STRETCH = 'UI elastic scale %s width %s height %s'
FLOAT = 'UI pull floating panel %s'
SLOT_VALUES = {
    'UI resting width':0, 'UI resting height':0, 'UI expanded width':0, 'UI expanded height':0,
    'UI motion kind':'', 'UI anchor shown x':0, 'UI anchor shown y':0,
    'UI contact x':0, 'UI contact y':0, 'UI contact path':'',
    'UI travel stretch x':0, 'UI travel stretch y':0,
    'UI menu alignment':'bottom center', 'UI last open phase':0,
    'UI destination x':0, 'UI destination y':0,
    'UI launcher gain':0,
}

def clip_axis(n, name, extent, limit):
    return n.clip(name,add(-limit,div(extent,2)),sub(limit,div(extent,2)))

def contains(text, part):
    return Node('operator_contains', {'STRING1':text,'STRING2':part})

def set_socket(n, key, name, value):
    old = n.blocks[key]['inputs'].get(name,[])
    for child in old[1:]:
        if isinstance(child,str):
            n.remove(child)
    if isinstance(value,Node):
        binding = [3,n.emit(value,key),[10,'']]
    elif isinstance(value,list):
        binding = [3,value,[10,'']]
    else:
        binding = [1,[10,str(value)]]
    n.blocks[key]['inputs'][name]=binding

def append_alignment_inputs(n, code):
    proto_key = n.blocks[n.definition(code)]['inputs']['custom_block'][1]
    proto = n.blocks[proto_key]
    mutation = proto['mutation']
    new_ids = ['lganchoralign','lganchorx','lganchory']
    for field,extra in [('argumentids',new_ids),('argumentnames',ALIGNMENT_INPUTS),
                        ('argumentdefaults',list(map(str,ALIGNMENT_DEFAULTS)))]:
        mutation[field] = json.dumps(json.loads(mutation[field])+list(extra),separators=(',',':'))
    mutation['proccode'] = code+ALIGNMENT_SUFFIX
    if proto['inputs'] or proto.get('shadow'):
        for aid,field in zip(new_ids,ALIGNMENT_INPUTS):
            reporter=arg(field)
            reporter.shadow=True
            proto['inputs'][aid]=[1,n.emit(reporter,proto_key)]
    for block in list(n.blocks.values()):
        if isinstance(block,dict) and block['opcode']=='procedures_call' and block['mutation']['proccode']==code:
            block['mutation'].update(proccode=mutation['proccode'],argumentids=mutation['argumentids'])
            for aid,value in zip(new_ids,ALIGNMENT_DEFAULTS):
                block['inputs'][aid]=[1,[10,str(value)]]
    n.procs[mutation['proccode']]=mutation

def curves(n):
    p=n.v('UI choreography p')
    return [n.set('UI choreography p',arg('phase')),*n.clip('UI choreography p',0,1),
            n.set('UI center phase',sub(1,mul(sub(1,p),sub(1,p)))),
            n.set('UI size phase',mul(p,p)),
            n.set('UI travel pulse',sub(n.v('UI center phase'),n.v('UI size phase')))]

def geometry(n):
    o=arg('owner');v=n.v
    lw=v('UI launcher width');lh=v('UI launcher height')
    pw=v('UI full panel width');ph=v('UI full panel height')
    mode=arg('alignment')
    circle=OR(eq(arg('launcher'),3),eq(arg('launcher'),'circle'))
    capsule=OR(eq(arg('launcher'),2),eq(arg('launcher'),'capsule'))
    dim=n.item('UI menu dim',o)
    shift_x=div(sub(pw,lw),2);shift_y=div(sub(ph,lh),2)
    phase=v('UI size phase')
    retarget=[]
    for axis in 'xy':
        name='UI open '+axis
        prior='UI destination '+axis
        retarget.extend([
            iff(AND(gt(n.item('UI last open phase',o),0),eq(n.item('UI motion kind',o),'Menu')),[
                n.set('UI moving destination',mix(n.item(prior,o),v(name),v('UI motion relax'))),
                iff(gt(abs_(sub(v(name),v('UI moving destination'))),.025),
                    [n.set(name,v('UI moving destination'))])]),
            n.replace(prior,o,v(name))])
    return [
        n.set('UI launcher width',abs_(arg('width'))),*n.clip('UI launcher width',8,440),
        n.set('UI launcher height',abs_(arg('height'))),*n.clip('UI launcher height',12,300),
        iff(circle,[n.set('UI launcher width',lh)]),
        n.replace('UI resting width',o,lw),n.replace('UI resting height',o,lh),
        n.set('UI full panel width',abs_(arg('panel'))),*n.clip('UI full panel width',8,440),
        n.set('UI full panel height',mul(add(n.item('UI menu root rows',o),1),n.item('UI row height',o))),
        *n.clip('UI full panel height',8,300),n.replace('UI expanded width',o,pw),n.replace('UI expanded height',o,ph),
        n.set('UI launcher x',arg('x')),n.set('UI launcher y',arg('y')),
        *clip_axis(n,'UI launcher x',lw,240),*clip_axis(n,'UI launcher y',lh,180),
        n.set('UI open x',v('UI launcher x')),n.set('UI open y',v('UI launcher y')),
        iff(contains(mode,'left'),[n.change('UI open x',mul(-1,shift_x))]),
        iff(contains(mode,'right'),[n.change('UI open x',shift_x)]),
        iff(contains(mode,'top'),[n.change('UI open y',shift_y)],
            [n.change('UI open y',mul(-1,shift_y))]),
        iff(eq(mode,'custom'),[n.set('UI open x',arg('expanded x')),n.set('UI open y',arg('expanded y'))]),
        *clip_axis(n,'UI open x',pw,240),*clip_axis(n,'UI open y',ph,180),
        *retarget,n.replace('UI last open phase',o,n.item('UI menu open fade',o)),
        n.call(PHASE,n.item('UI menu open fade',o)),
        n.set('UI cx',add(mix(v('UI launcher x'),v('UI open x'),v('UI center phase')),mul(4,dim))),
        n.set('UI cy',add(mix(v('UI launcher y'),v('UI open y'),v('UI center phase')),mul(6,dim))),
        n.set('UI width',sub(mix(lw,pw,phase),mul(10,dim))),
        n.set('UI height',sub(mix(lh,ph,phase),mul(6,dim))),
        n.set('UI rounded start',arg('radius')),
        iff(OR(circle,capsule),[n.set('UI rounded start',div(minimum(lw,lh),2))]),
        n.set('UI blended radius',mix(v('UI rounded start'),arg('radius'),phase)),
        n.set('UI half thickness',div(minimum(v('UI width'),v('UI height')),2)),
        n.set('UI blended radius',mix(v('UI blended radius'),v('UI half thickness'),mul(.95,v('UI travel pulse')))),
        # The launcher's pressed/hovered pose retires along with its face.
        n.set('UI launcher lift',0),
        iff(eq(v('UI hover id'),o),[n.set('UI launcher lift',.035)]),
        iff(eq(v('UI pressed id'),o),[n.set('UI launcher lift',.10),iff(circle,[n.set('UI launcher lift',.16)])]),
        n.replace('UI launcher gain',o,mix(n.item('UI launcher gain',o),v('UI launcher lift'),v('UI motion relax'))),
        iff(lt(abs_(sub(v('UI launcher lift'),n.item('UI launcher gain',o))),.0004),
            [n.replace('UI launcher gain',o,v('UI launcher lift'))]),
        n.set('UI launcher lift',add(1,mul(n.item('UI launcher gain',o),sub(1,v('UI choreography p'))))),
        *[n.set(name,mul(v(name),v('UI launcher lift'))) for name in ('UI width','UI height','UI blended radius')],
        *[n.replace('UI travel stretch '+ax,o,mul(mul(.24,v('UI travel pulse')),
              minimum(1,div(abs_(sub(v('UI open '+ax),v('UI launcher '+ax))),size))))
          for ax,size in [('x',lw),('y',lh)]],
        n.set('UI shape',1),
        *clip_axis(n,'UI cx',v('UI width'),240),*clip_axis(n,'UI cy',v('UI height'),180),
    ]

def contact(n):
    """A bounded signed displacement carries the center toward the finger.

    The axes stay separate. Initial motion is compliant; travel saturates
    instead of allowing a control to leave its layout anchor.
    """
    o=arg('owner');v=n.v
    enabled=OR(eq(n.item('UI kind',o),'Button'),eq(n.item('UI drag enabled',o),1))
    held=AND(eq(v('UI pressed id'),o),AND(eq(v('UI down'),1),enabled))
    start=[]
    for ax,limit in [('x',28),('y',20)]:
        name='UI wanted '+ax
        start.extend([n.set(name,mul(mul(.65,n.item('pull',o)),sub(v('UI pointer '+ax),v('UI down '+ax)))),
                      n.set(name,div(mul(limit,v(name)),add(limit,abs_(v(name)))))])
    return [n.set('UI wanted x',0),n.set('UI wanted y',0),
            iff(held,[n.set('UI captured path',''),iff(gt(v('UI pressed layer'),0),
                [n.set('UI captured path',li(n,'path',v('UI pressed layer')))]),
                iff(NOT(eq(v('UI captured path'),n.item('UI contact path',o))),[
                    n.replace('UI contact x',o,0),n.replace('UI contact y',o,0)]),
                n.replace('UI contact path',o,v('UI captured path')),*start]),
            *[cmd for ax in 'xy' for cmd in (
                n.set('UI relaxed contact',mix(n.item('UI contact '+ax,o),v('UI wanted '+ax),v('UI motion relax'))),
                iff(lt(abs_(v('UI relaxed contact')),.016),[n.set('UI relaxed contact',0)]),
                n.replace('UI contact '+ax,o,v('UI relaxed contact')))],
            iff(AND(eq(n.item('UI contact x',o),0),eq(n.item('UI contact y',o),0)),
                [n.replace('UI contact path',o,'')])]

def scale(n):
    o=arg('owner');v=n.v
    body=[]
    for ax,extent in [('x','width'),('y','height')]:
        body.extend([n.set('UI travel length '+ax,abs_(n.item('UI contact '+ax,o))),
                     n.set('UI stretch '+ax,div(mul(1.35,v('UI travel length '+ax)),maximum(8,arg(extent)))),
                     *n.clip('UI stretch '+ax,0,.38)])
    body += [n.set('UI cross x',0),n.set('UI cross y',0)]
    for ax,other in [('x','y'),('y','x')]:
        body.append(iff(gt(v('UI travel length '+other),v('UI travel length '+ax)),[
            n.set('UI cross '+ax,sub(1,div(v('UI travel length '+ax),v('UI travel length '+other))))]))
        body.append(n.set('UI axis scale '+ax,div(add(1,v('UI stretch '+ax)),
            add(1,mul(v('UI stretch '+other),v('UI cross '+ax))))))
    return body

def float_pull(n):
    o=arg('owner');v=n.v;i=v('UI elastic layer')
    body=[n.call(STRETCH,o,li(n,'w',i),li(n,'h',i)),
          put(n,'w',i,minimum(476,mul(li(n,'w',i),v('UI axis scale x')))),
          put(n,'h',i,minimum(356,mul(li(n,'h',i),v('UI axis scale y')))),
          put(n,'r',i,minimum(li(n,'r',i),div(minimum(li(n,'w',i),li(n,'h',i)),2)))]
    for ax,f,bound in [('x','w',240),('y','h',180)]:
        name='UI elastic '+ax
        body.extend([n.set(name,add(li(n,ax,i),n.item('UI contact '+ax,o))),
                     *clip_axis(n,name,li(n,f,i),bound),put(n,ax,i,v(name))])
    return [iff(NOT(eq(n.item('UI contact path',o),'')),[
        n.set('UI elastic layer',1),repeat(n.length('UI layer owner'),[
            iff(AND(eq(li(n,'owner',i),o),eq(li(n,'path',i),n.item('UI contact path',o))),body),
            n.change('UI elastic layer',1)])])]

def settle(n):
    v=n.v;o=v('UI settle id');kind=n.item('UI kind',o)
    button=eq(kind,'Button')
    interactive=OR(button,eq(kind,'Menu'))
    reset=[n.replace('UI contact x',o,0),n.replace('UI contact y',o,0),n.replace('UI contact path',o,''),
           n.replace('UI anchor shown x',o,n.item('tx',o)),n.replace('UI anchor shown y',o,n.item('ty',o))]
    live=[iff(NOT(eq(n.item('UI motion kind',o),kind)),reset),
          n.replace('UI motion kind',o,kind),n.call(PULL,o),
          n.set('UI axis scale x',1),n.set('UI axis scale y',1),
          iff(eq(n.item('UI contact path',o),''),[n.call(STRETCH,o,n.item('w',o),n.item('h',o))])]
    for ax in 'xy':
        anchor='UI anchor shown '+ax
        live.extend([n.set('UI pose base',n.item('t'+ax,o)),
            iff(button,[n.set('UI pose base',mix(n.item(anchor,o),v('UI pose base'),v('UI motion relax'))),
                iff(lt(abs_(sub(v('UI pose base'),n.item('t'+ax,o))),.02),[n.set('UI pose base',n.item('t'+ax,o))])]),
            n.replace(anchor,o,v('UI pose base')),
            iff(eq(n.item('UI contact path',o),''),[n.change('UI pose base',n.item('UI contact '+ax,o))]),
            iff(NOT(button),[n.change('UI axis scale '+ax,n.item('UI travel stretch '+ax,o)),
                *clip_axis(n,'UI pose base',mul(n.item('w' if ax=='x' else 'h',o),v('UI axis scale '+ax)),240 if ax=='x' else 180)]),
            n.replace(ax,o,v('UI pose base')),n.replace('v'+ax,o,0),n.replace('scale'+ax.upper(),o,v('UI axis scale '+ax))])
    live.append(n.replace('amp',o,maximum(mul(div(n.item('w',o),2),abs_(sub(v('UI axis scale x'),1))),
                                         mul(div(n.item('h',o),2),abs_(sub(v('UI axis scale y'),1))))))
    return [n.set('UI motion relax',sub(1,math('e ^',mul(-19,v('dt'))))),n.set('UI settle id',1),
            repeat(8,[iff(AND(eq(n.item('UI live',o),1),interactive),live,[n.replace('UI motion kind',o,'')]),
                      n.change('UI settle id',1)])]

def patch_interaction(n):
    d=n.definition('UI input'); b=n.blocks
    offset=next(k for k in procs(n,d,'data_replaceitemoflist') if b[k]['fields']['LIST'][0]=='UI offset x')
    track=offset
    while b[track]['parent']!=d and b[track]['parent'] not in n.sequence(d):
        track=b[track]['parent']
    while track not in n.sequence(d):
        track=b[track]['parent']
    # Replace only the drag handler; the original capture/release routing stays intact.
    for binding in b[track]['inputs'].values():
        for c in binding[1:]:
            if isinstance(c,str):
                if c==b[track]['inputs'].get('SUBSTACK',[None,None])[1]:
                    while c:
                        nxt=b[c]['next'];n.remove(c);c=nxt
                else:n.remove(c)
    b[track]['inputs']={}
    def delta(ax):return abs_(sub(n.v('UI pointer '+ax),n.v('UI down '+ax)))
    moved=OR(eq(n.v('UI pointer moved'),1),gt(add(delta('x'),delta('y')),6))
    b[track]['inputs']['CONDITION']=[2,n.emit(gt(n.v('UI pressed id'),0),track)]
    b[track]['inputs']['SUBSTACK']=[2,n.chain([iff(moved,[n.set('UI moved',1)])],track)[0]]
    # Invert the page artwork's transformed pitch at the last displayed geometry.
    row=next(k for k in procs(n,d,'data_setvariableto') if b[k]['fields']['VARIABLE'][0]=='UI hover row'
             and isinstance(b[k]['inputs']['VALUE'][1],str) and b[b[k]['inputs']['VALUE'][1]]['opcode']=='operator_mathop')
    slot=n.v('UI scan'); h=n.item('h',slot)
    pitch=div(mul(n.item('UI row height',slot),h),maximum(1,n.item('UI expanded height',slot)))
    set_socket(n,row,'VALUE',floor(div(sub(div(h,2),n.v('UI local y')),pitch)))
    hdef=n.definition(HIT); row=next(k for k in procs(n,hdef,'data_setvariableto') if b[k]['fields']['VARIABLE'][0]=='UI hover row'
                and isinstance(b[k]['inputs']['VALUE'][1],str))
    i=arg('layer')
    ref=minimum(300,mul(add(li(n,'rows',i),1),li(n,'pitch',i)))
    pitch=div(mul(li(n,'pitch',i),li(n,'h',i)),maximum(1,ref))
    set_socket(n,row,'VALUE',floor(div(sub(add(li(n,'y',i),div(li(n,'h',i),2)),n.v('UI pointer y')),pitch)))

def nested_curves(n):
    d=n.definition(POSE);b=n.blocks
    # The public custom coordinates belong to the root. Nested pages keep
    # their calling row as origin and inherit the chosen growth direction.
    writes=procs(n,d,'data_setvariableto')
    child_y=next(k for k in writes if b[k]['fields']['VARIABLE'][0]=='UI child y')
    owner=arg('owner');v=n.v
    alignment=n.item('UI menu alignment',owner)
    dx=div(sub(v('UI child width'),v('UI base w')),2)
    dy=div(sub(v('UI child height'),v('UI base pitch')),2)
    n.attach(child_y,[
        iff(contains(alignment,'left'),[n.set('UI child x',sub(v('UI base x'),dx))]),
        iff(contains(alignment,'right'),[n.set('UI child x',add(v('UI base x'),dx))]),
        iff(contains(alignment,'top'),[n.set('UI child y',add(v('UI seed y'),dy))])],b[child_y]['next'])
    changes=[]
    for k in procs(n,d,'data_replaceitemoflist'):
        name=b[k]['fields']['LIST'][0]
        if name not in ('UI layer x','UI layer y','UI layer w','UI layer h'):continue
        todo=[b[k]['inputs']['ITEM'][1]]
        found=[]
        while todo:
            key=todo.pop()
            if not isinstance(key,str):continue
            block=b[key]
            if block['opcode']=='data_itemoflist' and block['fields']['LIST'][0]=='UI layer p':
                found.append(key);continue
            todo.extend(v for binding in block['inputs'].values() for v in binding[1:] if isinstance(v,str))
        if found:changes.append((k,name,found))
    if len(changes)!=4:raise ValueError('Expected four nested geometry interpolations')
    first=next(k for k,name,_ in changes if name=='UI layer x')
    insert_before(n,first,[n.call(PHASE,li(n,'p',n.v('UI panel step')))])
    for _,name,ids in changes:
        for old in ids:
            parent=b[b[old]['parent']]
            for bind in parent['inputs'].values():
                if bind[1]==old:
                    bind[1]=n.v('UI center phase' if name in ('UI layer x','UI layer y') else 'UI size phase')
            n.remove(old)

def apply_motion_layout(target, *, studio=True):
    n=UIProgram(target,exporting=not studio)
    old_menu=next(s for s in n.procs if s.startswith('Menu %s x '))
    button=next(s for s in n.procs if s.startswith('Button %s x '))
    if old_menu.endswith(ALIGNMENT_SUFFIX):raise ValueError('Motion is already installed')
    helpers=[(PHASE,('phase',),curves),(GEOMETRY,('owner','x','y','launcher','width','height','radius','panel','alignment','expanded x','expanded y'),geometry),
             (PULL,('owner',),contact),(STRETCH,('owner','width','height'),scale),(FLOAT,('owner',),float_pull)]
    for code,fields,_ in helpers:n.declare(code,fields)
    for j,(code,_,body) in enumerate(helpers):n.define(code,body(n),(140000+(j%2)*6500,9000+(j//2)*4500))
    menu_def=n.definition(old_menu);button_def=n.definition(button)
    menu_glass=next(k for k in procs(n,menu_def,'procedures_call') if n.blocks[k]['mutation']['proccode'].startswith('Glass '))
    panel_pose=next(k for k in procs(n,menu_def,'procedures_call') if n.blocks[k]['mutation']['proccode']==POSE)
    button_glass=next(k for k in procs(n,button_def,'procedures_call') if n.blocks[k]['mutation']['proccode'].startswith('Glass '))
    o=n.v('UI slot')
    insert_before(n,panel_pose,[n.replace('UI menu alignment',o,arg('alignment'))])
    pressed_lift=next(k for k in procs(n,button_def,'data_setvariableto')
        if n.blocks[k]['fields']['VARIABLE'][0]=='UI growth'
        and isinstance(n.blocks[k]['inputs']['VALUE'][1],list)
        and str(n.blocks[k]['inputs']['VALUE'][1][1]) in ('.94','0.94'))
    is_circle=OR(eq(n.v('UI shape'),3),eq(n.v('UI shape'),'circle'))
    set_socket(n,pressed_lift,'VALUE',add(1.08,mul(.08,is_circle)))
    insert_before(n,button_glass,[n.replace('UI resting width',o,n.v('UI width')),
        n.replace('UI resting height',o,n.v('UI height'))])
    insert_before(n,menu_glass,[n.call(GEOMETRY,o,arg('x'),arg('y'),arg('launcher'),arg('width'),arg('height'),
        arg('radius'),arg('panel width'),arg('alignment'),arg('expanded x'),arg('expanded y')),n.call(FLOAT,o)])
    glass_args=json.loads(n.blocks[menu_glass]['mutation']['argumentids'])
    set_socket(n,menu_glass,glass_args[6],n.v('UI blended radius'))
    set_socket(n,menu_glass,glass_args[15],0)  # The choreography has already sampled this frame's pose.
    nested_curves(n);patch_interaction(n)
    replace_body(n,'UI settle',settle(n))
    reset=n.definition('UI reset')
    n.attach(n.sequence(reset)[-1],[cmd for k,initial in SLOT_VALUES.items()
        for cmd in (n.clear(k),repeat(8,[n.add(k,initial)]))],None)
    for k,initial in SLOT_VALUES.items():target['lists'][n.storage(k,True)[1]][1]=[initial]*8
    append_alignment_inputs(n,old_menu)
    return target
