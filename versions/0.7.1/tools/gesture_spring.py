"""Add signed velocity to 0.7.0 control pull, release and surface lift."""
import json

from .menu_layers import insert_before, procs, replace_body
from .menu_timing import SOLVE
from .motion_layout import GEOMETRY, PULL, STRETCH
from .stable_pen import Node, arg, iff
from .stretch_gesture import GESTURE, REACH
from .ui_components import UIProgram, AND, OR, NOT, abs_, add, div, eq, gt, lt, math, maximum, mul, repeat, sub

SURFACE='UI spring surface %s gain %s bounce %s'
BUTTON_BASE='UI spring button shape %s'
FOLLOW='UI spring grip position %s velocity %s destination %s step %s elapsed %s bounce %s'
SLOTS={'UI grip clock':-1,'UI grip seconds':0,'UI surface kind':'','UI surface lift':0,
       'UI surface velocity':0,'UI grip bounce':.30,'UI button base ready':0,
       **{'UI button base '+k:0 for k in ('w','h','r')},
       **{'UI '+k+' velocity '+a:0 for a in 'xy' for k in ('contact','reach')}}

def surface(n):
    owner=arg('owner');v=n.v
    def get(key):return n.item(key,owner)
    def put(key,val):return n.replace(key,owner,val)
    changed=NOT(eq(get('UI surface kind'),get('UI kind')))
    return [iff(changed,[put('UI grip clock',-1),put('UI surface lift',0),put('UI surface velocity',0),
                         put('UI button base ready',0),put('UI surface kind',get('UI kind'))]),
            n.set('UI grip time',Node('sensing_timer')),n.set('UI grip delta',0),
            iff(NOT(lt(get('UI grip clock'),0)),[n.set('UI grip delta',maximum(0,sub(v('UI grip time'),get('UI grip clock'))))]),
            put('UI grip clock',v('UI grip time')),put('UI grip seconds',v('UI grip delta')),
            n.set('UI grip elasticity',arg('bounce')),*n.clip('UI grip elasticity',0,.7),put('UI grip bounce',v('UI grip elasticity')),
            n.call(SOLVE,get('UI surface lift'),get('UI surface velocity'),arg('gain'),.27,get('UI grip bounce'),v('UI grip delta')),
            put('UI surface lift',v('UI spring p')),put('UI surface velocity',v('UI spring v'))]

def button_base(n):
    # Keep the Button's existing easing when a user changes its layout width,
    # height or radius. Apply the independently integrated lift exactly once.
    owner=arg('owner');v=n.v
    def get(k):return n.item(k,owner)
    gain=add(1,get('UI surface lift'))
    speed=sub(1,math('e ^',mul(-18.4,get('UI grip seconds'))))
    body=[]
    for dim in ('w','h','r'):
        base='UI button base '+dim
        body.extend([n.set('UI base target',div(get('t'+dim),gain)),
            iff(eq(get('UI button base ready'),0),[n.replace(base,owner,v('UI base target'))],[
                n.replace(base,owner,add(get(base),mul(speed,sub(v('UI base target'),get(base))))),
                iff(lt(abs_(sub(get(base),v('UI base target'))),.001),[n.replace(base,owner,v('UI base target'))])]),
            n.replace(dim,owner,mul(get(base),gain))])
    return [iff(eq(get('UI kind'),'Button'),[*body,n.replace('UI button base ready',owner,1)])]

def follow(n):
    v=n.v;target=arg('destination');p=arg('position')
    # Only a new, reversing pointer step redirects incoming velocity. When
    # the pointer stays in place the spring can cross its target and settle.
    return [n.set('UI approach velocity',arg('velocity')),
        iff(lt(mul(arg('step'),v('UI approach velocity')),0),[n.set('UI approach velocity',0)]),
        n.set('UI follow elapsed',arg('elapsed')),iff(eq(v('UI edge'),1),[n.set('UI follow elapsed',0)]),
        n.call(SOLVE,p,v('UI approach velocity'),target,.18,arg('bounce'),v('UI follow elapsed'))]

def release(n):
    v=n.v;o=arg('owner')
    def get(key):return n.item(key,o)
    body=[]
    for axis in 'xy':
        for lane,key in [('contact','UI contact '+axis),('reach','UI grip reach '+axis)]:
            velocity='UI '+lane+' velocity '+axis
            body.extend([n.call(SOLVE,get(key),get(velocity),0,.36,get('UI grip bounce'),get('UI grip seconds')),
                         n.replace(key,o,v('UI spring p')),n.replace(velocity,o,v('UI spring v'))])
    complete=AND(AND(eq(get('UI contact x'),0),eq(get('UI contact y'),0)),
                 AND(eq(get(REACH[0]),0),eq(get(REACH[1]),0)))
    for axis in 'xy':
        for lane in ('contact','reach'):
            complete=AND(complete,eq(get('UI '+lane+' velocity '+axis),0))
    # The press/release event belongs to this frame. Carry the last displayed
    # pose and velocity through it, then integrate toward the anchor.
    return [iff(eq(get(GESTURE),1),[n.replace(GESTURE,o,0)],body),
            iff(complete,[n.replace('UI contact path',o,'')])]

def remove_range(n,first,last,replacement):
    parent=n.blocks[first]['parent'];after=n.blocks[last]['next'];old=[];key=first
    while True:
        old.append(key)
        if key==last:break
        key=n.blocks[key]['next']
    n.attach(parent,replacement,after)
    for key in old:n.remove(key)

def patch_contact(n):
    o=arg('owner');v=n.v;d=n.definition(PULL)
    root=n.sequence(d)[0]
    released=n.blocks[root]['inputs']['SUBSTACK2'][1]
    while released:
        nxt=n.blocks[released]['next'];n.remove(released);released=nxt
    n.blocks[root]['inputs']['SUBSTACK2']=[2,n.chain(release(n),root)[0]]
    for axis in 'xy':
        key='UI contact '+axis;velocity='UI contact velocity '+axis;reach='UI grip reach '+axis
        center_put=next(k for k in procs(n,d,'data_replaceitemoflist') if n.blocks[k]['fields']['LIST'][0]==key
                        and n.blocks[k]['inputs']['ITEM'][1]==n.v('UI grip center'))
        snap=n.blocks[center_put]['parent'];old=n.blocks[snap]['parent'];high=n.blocks[center_put]['next']
        if n.blocks[snap]['opcode']!='control_if' or n.blocks[high]['opcode']!='control_if':
            raise ValueError('Unrecognized captured grip sequence')
        extent_velocity='UI reach velocity '+axis
        advance=[n.call(FOLLOW,n.item(key,o),n.item(velocity,o),n.item('UI grip guide '+axis,o),v('UI pointer step'),
                        n.item('UI grip seconds',o),n.item('UI grip bounce',o)),
                 n.set('UI grip center',v('UI spring p')),n.replace(velocity,o,v('UI spring v')),n.replace(key,o,v('UI grip center')),
                 n.replace(extent_velocity,o,0),
                 iff(gt(abs_(v('UI grip center')),n.item(reach,o)),[
                     n.replace(reach,o,abs_(v('UI grip center'))),
                     n.replace(extent_velocity,o,mul(v('UI spring v'),sub(1,mul(2,lt(v('UI grip center'),0)))))])]
        remove_range(n,old,high,advance)
    # A press on a different floating pane starts a new local frame.
    clear=next(k for k in procs(n,d,'data_replaceitemoflist') if n.blocks[k]['fields']['LIST'][0]=='UI contact y'
               and n.blocks[k]['inputs']['ITEM'][1][1] in ('0',0))
    n.attach(clear,[n.replace('UI '+name+' velocity '+axis,o,0)
                    for name in ('contact','reach') for axis in 'xy'],n.blocks[clear]['next'])

def patch_scale(n):
    # On release, a small negative spring excursion is safe and visible. While
    # held the high-water extent is strictly nonnegative, even at a reversal.
    v=n.v;body=[]
    for axis,extent in [('x','width'),('y','height')]:
        lane='UI stretch '+axis
        body.extend([n.set(lane,div(mul(1.35,n.item('UI grip reach '+axis,arg('owner'))),maximum(8,arg(extent)))),
            *n.clip(lane,-.08,.38),iff(eq(n.item(GESTURE,arg('owner')),1),[n.set(lane,maximum(0,v(lane)))]),
            n.set('UI axis scale '+axis,add(1,v(lane)))])
    replace_body(n,STRETCH,body)

def add_button_bounce(n,button,studio):
    menu=next(code for code in n.procs if code.startswith('Menu %s x '))
    example=.30
    if studio:
        menu_arg=json.loads(n.procs[menu]['argumentids'])[-1]
        for b in n.blocks.values():
            if not isinstance(b,dict) or b['opcode']!='procedures_call' or b['mutation']['proccode']!=menu:continue
            value=b['inputs'].get(menu_arg,[])
            if len(value)>1 and value[0]==1 and isinstance(value[1],list):
                try:example=max(0,min(.70,float(value[1][1])))
                except (TypeError,ValueError):pass
                break
    aid='lggesturebuttonbounce';updated=button+' bounce %s'
    definition=n.definition(button);proto=n.blocks[n.blocks[definition]['inputs']['custom_block'][1]]
    m=proto['mutation']
    for field,new in [('argumentids',aid),('argumentnames','bounce'),('argumentdefaults','0.3')]:
        m[field]=json.dumps([*json.loads(m[field]),new],separators=(',',':'))
    m['proccode']=updated
    if proto['inputs'] or proto.get('shadow'):
        reporter=arg('bounce');reporter.shadow=True
        proto['inputs'][aid]=[1,n.emit(reporter,n.blocks[definition]['inputs']['custom_block'][1])]
    for b in list(n.blocks.values()):
        if isinstance(b,dict) and b['opcode']=='procedures_call' and b['mutation']['proccode']==button:
            b['mutation'].update(proccode=updated,argumentids=m['argumentids'])
            b['inputs'][aid]=[1,[10,str(example)]]
    n.procs[updated]=m

def apply_gesture_spring(target,*,studio=True):
    n=UIProgram(target,exporting=not studio)
    for idx,(code,args,fn) in enumerate(((SURFACE,('owner','gain','bounce'),surface),(BUTTON_BASE,('owner',),button_base),
        (FOLLOW,('position','velocity','destination','step','elapsed','bounce'),follow))):
        n.declare(code,args);n.define(code,fn(n),(154000,9000+4000*idx))
    button=next(k for k in n.procs if k.startswith('Button %s x '))
    glass=next(k for k in procs(n,n.definition(button),'procedures_call') if n.blocks[k]['mutation']['proccode'].startswith('Glass '))
    o=n.v('UI slot')
    insert_before(n,glass,[n.call(SURFACE,o,sub(n.v('UI growth'),1),arg('bounce')),n.set('UI growth',add(1,n.item('UI surface lift',o)))])
    base=n.definition(GEOMETRY)
    gain=next(k for k in procs(n,base,'data_replaceitemoflist') if n.blocks[k]['fields']['LIST'][0]=='UI launcher gain')
    snap=n.blocks[gain]['next']
    if n.blocks[snap]['opcode']!='control_if':raise ValueError('Unexpected launcher gain path')
    remove_range(n,gain,snap,[n.call(SURFACE,arg('owner'),n.v('UI launcher lift'),n.item('UI menu bounce',arg('owner'))),
        n.replace('UI launcher gain',arg('owner'),n.item('UI surface lift',arg('owner')))])
    settle=n.definition('UI settle')
    grip=next(k for k in procs(n,settle,'procedures_call') if n.blocks[k]['mutation']['proccode']==PULL)
    insert_before(n,grip,[n.call(BUTTON_BASE,n.v('UI settle id'))])
    reset=next(k for k in procs(n,settle,'data_replaceitemoflist') if n.blocks[k]['fields']['LIST'][0]=='UI contact y')
    n.attach(reset,[n.replace('UI '+k+' velocity '+a,n.v('UI settle id'),0)
        for k in ('contact','reach') for a in 'xy'],n.blocks[reset]['next'])
    # A missing/reused slot must get a fresh clock even if the replacement has
    # the same component type as its former occupant.
    inactive=next(k for k in procs(n,settle,'data_replaceitemoflist') if n.blocks[k]['fields']['LIST'][0]=='UI motion kind'
                  and n.blocks[k]['inputs']['ITEM'][1]==[10,''])
    n.attach(inactive,[n.replace('UI surface kind',n.v('UI settle id'),'')],n.blocks[inactive]['next'])
    patch_contact(n);patch_scale(n)
    d=n.definition('UI reset')
    n.attach(n.sequence(d)[-1],[cmd for name,initial in SLOTS.items()
        for cmd in (n.clear(name),repeat(8,[n.add(name,initial)]))],None)
    for name,initial in SLOTS.items():target['lists'][n.storage(name,True)[1]][1]=[initial]*8
    add_button_bounce(n,button,studio)
    return target
