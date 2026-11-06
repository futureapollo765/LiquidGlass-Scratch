"""Upgrade native 0.6.0 menus with independent travel and growth springs.

Each property carries its displayed position and velocity from frame to frame.
Scratch's timer supplies real elapsed seconds. The closed-form update remains
stable when an interpreted rendering frame lasts longer than a display tick.
"""
import json
from .stable_pen import Node, arg, iff
from .ui_components import (
    UIProgram, abs_, add, AND, div, eq, gt, lt, math, maximum, minimum,
    mul, NOT, OR, repeat, sub,
)
from .menu_layers import POSE, STEP, insert_before, li, procs
from .motion_layout import GEOMETRY, PHASE, set_socket


TIMING_NAMES = ('open travel', 'open growth', 'close travel', 'close growth', 'bounce')
TIMING_DEFAULTS = (.52, .84, .72, .46, .30)
TIMING_SUFFIX = ''.join(' ' + field + ' %s' for field in TIMING_NAMES)
CLOCK = 'UI step menu springs %s open travel %s open growth %s close travel %s close growth %s bounce %s'
SOLVE = 'UI advance spring position %s velocity %s target %s seconds %s bounce %s elapsed %s'
PROJECT = 'UI read menu spring pose %s'
MAX_DURATION = 4
MAX_BOUNCE = .70
SLOT_VALUES = {
    'UI travel progress':0, 'UI travel velocity':0,
    'UI growth progress':0, 'UI growth velocity':0,
    'UI menu clock':0, 'UI frame seconds':0,
    'UI open growth seconds':TIMING_DEFAULTS[1], 'UI close growth seconds':TIMING_DEFAULTS[3],
    'UI menu bounce':TIMING_DEFAULTS[4],
}


def advance_spring(n):
    """Exact underdamped/critically damped solution for an arbitrary initial velocity.

    The spring has unit mass, angular frequency 2π/duration, and damping ratio
    1–bounce. Scratch trigonometric blocks use degrees. For critical damping,
    sin(w*t)/w tends to t, so no division by zero is needed.
    """
    v=n.v
    target=arg('target')
    elapsed=arg('elapsed')
    position=arg('position')
    velocity=arg('velocity')
    omega=v('UI natural frequency')
    loss=v('UI decay rate')
    cosine=v('UI spring cosine')
    sinc=v('UI spring sinc')
    delta=v('UI spring displacement')
    damping=v('UI spring envelope')
    snap=[n.set('UI spring p',target),n.set('UI spring v',0)]
    finish=AND(lt(abs_(sub(v('UI spring p'),target)),.00065),
               lt(abs_(v('UI spring v')),.012))
    oscillate=[
        n.set('UI damped frequency',mul(omega,math('sqrt',sub(1,mul(v('UI damping ratio'),v('UI damping ratio')))))),
        n.set('UI spring angle',mul(mul(v('UI damped frequency'),elapsed),180/3.141592653589793)),
        n.set('UI spring cosine',math('cos',v('UI spring angle'))),
        n.set('UI spring sinc',div(math('sin',v('UI spring angle')),v('UI damped frequency'))),
    ]
    step=[
        n.set('UI spring duration',arg('seconds')),*n.clip('UI spring duration',1/240,MAX_DURATION),
        n.set('UI natural frequency',div(2*3.141592653589793,v('UI spring duration'))),
        n.set('UI damping ratio',sub(1,arg('bounce'))),
        n.set('UI decay rate',mul(omega,v('UI damping ratio'))),
        n.set('UI spring displacement',sub(position,target)),
        n.set('UI spring envelope',math('e ^',mul(mul(-1,loss),elapsed))),
        n.set('UI spring cosine',1),n.set('UI spring sinc',elapsed),
        iff(gt(arg('bounce'),.000001),oscillate),
        n.set('UI spring p',add(target,mul(damping,
            add(mul(delta,cosine),mul(add(velocity,mul(loss,delta)),sinc))))),
        n.set('UI spring v',mul(damping,sub(mul(velocity,cosine),
            mul(add(mul(loss,velocity),mul(mul(omega,omega),delta)),sinc)))),
        iff(finish,snap),
    ]
    immediate=OR(NOT(gt(arg('seconds'),0)),gt(elapsed,mul(12,arg('seconds'))))
    return [iff(immediate,snap,[
        n.set('UI spring p',position),n.set('UI spring v',velocity),
        iff(AND(gt(elapsed,0),NOT(AND(eq(position,target),eq(velocity,0)))),step)])]


def update_clocks(n):
    owner=arg('owner')
    v=n.v
    goal=n.item('UI open',owner)
    # Newly installed slots start at their launcher even if this is their
    # first menu after a long-running host project. Later frames use the full
    # interval; a reset of Scratch's shared timer produces a zero-length step.
    body=[
        n.set('UI clock now',Node('sensing_timer')),
        n.set('UI clock dt',maximum(0,sub(v('UI clock now'),n.item('UI menu clock',owner)))),
        iff(NOT(eq(n.item('UI motion kind',owner),'Menu')),[
            n.set('UI clock dt',0),
            *[n.replace(field,owner,0) for field in ('UI travel progress','UI travel velocity',
                                                    'UI growth progress','UI growth velocity','UI menu open fade')]]),
        n.replace('UI menu clock',owner,v('UI clock now')),n.replace('UI frame seconds',owner,v('UI clock dt')),
        n.set('UI effective bounce',arg('bounce')),*n.clip('UI effective bounce',0,MAX_BOUNCE),
        n.replace('UI menu bounce',owner,v('UI effective bounce')),
    ]
    for channel in ('travel','growth'):
        value='UI '+channel+' progress'
        velocity='UI '+channel+' velocity'
        body += [
            n.set('UI opening seconds',arg('open '+channel)),*n.clip('UI opening seconds',0,MAX_DURATION),
            n.set('UI closing seconds',arg('close '+channel)),*n.clip('UI closing seconds',0,MAX_DURATION),
        ]
        if channel=='growth':
            body += [n.replace('UI open growth seconds',owner,v('UI opening seconds')),
                     n.replace('UI close growth seconds',owner,v('UI closing seconds'))]
        body += [
            n.set('UI selected seconds',v('UI opening seconds')),
            iff(eq(goal,0),[n.set('UI selected seconds',v('UI closing seconds'))]),
            n.call(SOLVE,n.item(value,owner),n.item(velocity,owner),goal,v('UI selected seconds'),
                   v('UI effective bounce'),v('UI clock dt')),
            n.replace(value,owner,v('UI spring p')),n.replace(velocity,owner,v('UI spring v')),
        ]
    # Labels may fade in/out, but an overshoot around a resting endpoint
    # should not reveal the previous page again during the settling tail.
    previous_fade=n.item('UI menu open fade',owner)
    body += [
        n.set('UI face progress',n.item('UI growth progress',owner)),*n.clip('UI face progress',0,1),
        iff(eq(goal,1),[n.replace('UI menu open fade',owner,maximum(previous_fade,v('UI face progress')))],
            [n.replace('UI menu open fade',owner,minimum(previous_fade,v('UI face progress')))]),
        n.replace('UI menu open velocity',owner,n.item('UI growth velocity',owner)),
    ]
    return body


def root_pose(n):
    owner=arg('owner');v=n.v
    # Preserve spring overshoot for the surface's center and dimensions.
    # Only opacity and the pressure-dependent optical accent are bounded.
    return [
        n.set('UI center phase',n.item('UI travel progress',owner)),
        n.set('UI size phase',n.item('UI growth progress',owner)),
        n.set('UI choreography p',n.item('UI menu open fade',owner)),
        n.set('UI travel pulse',minimum(.55,abs_(sub(v('UI center phase'),v('UI size phase'))))),
    ]


def replace_call(n, previous, replacement):
    """Keep the original statement and its incoming edge, replacing its inputs and mutation."""
    block=n.blocks[previous]
    for binding in block['inputs'].values():
        for child in binding[1:]:
            if isinstance(child,str):n.remove(child)
    transient=n.emit(replacement,block['parent'])
    fresh=n.blocks.pop(transient)
    block['mutation']=fresh['mutation']
    block['inputs']=fresh['inputs']
    for binding in block['inputs'].values():
        for child in binding[1:]:
            if isinstance(child,str):n.blocks[child]['parent']=previous


def remove_old_root_clock(n):
    definition=n.definition(POSE);seq=n.sequence(definition);blocks=n.blocks
    # Check semantic anchors before removing the old common phase. The next
    # statement saves the configured panel width for nested menu layout.
    stop=next(i for i,k in enumerate(seq) if blocks[k]['fields'].get('LIST',[None])[0]=='UI menu panel width')
    removed=seq[:stop]
    if (not removed or blocks[removed[0]]['fields'].get('VARIABLE',[None])[0]!='UI step dt'
            or not any(blocks[k].get('mutation',{}).get('proccode')==STEP for k in removed)
            or not any(blocks[k]['fields'].get('LIST',[None])[0]=='UI menu open fade' for k in removed)):
        raise ValueError('Could not identify the 0.6.0 root clock')
    blocks[definition]['next']=seq[stop];blocks[seq[stop]]['parent']=definition
    for k in removed:n.remove(k)
    # Private pages grow from their own invoking row. Only their one growth
    # spring runs here; a different helper supplies the root's two channels.
    children=[k for k in procs(n,definition,'procedures_call')
              if blocks[k]['mutation']['proccode']==STEP]
    if len(children)!=1:raise ValueError('Expected one private spring in UI panels')
    owner=arg('owner');layer=n.v('UI panel step');goal=li(n,'goal',layer)
    time=n.v('UI layer duration')
    insert_before(n,children[0],[n.set('UI layer duration',n.item('UI open growth seconds',owner)),
        iff(eq(goal,0),[n.set('UI layer duration',n.item('UI close growth seconds',owner))])])
    replace_call(n,children[0],n.call(SOLVE,li(n,'p',layer),li(n,'v',layer),goal,time,
                 n.item('UI menu bounce',owner),n.item('UI frame seconds',owner)))
    # A private surface merges back into its row at first contact. Once it
    # disappears there, do not let a mathematical rebound reveal its ink.
    n.attach(children[0],[iff(AND(eq(goal,0),NOT(gt(n.v('UI spring p'),0))),
             [n.set('UI spring p',0),n.set('UI spring v',0)])],blocks[children[0]]['next'])


def extend_menu(n,code):
    proto_key=n.blocks[n.definition(code)]['inputs']['custom_block'][1]
    proto=n.blocks[proto_key];mutation=proto['mutation']
    argids=['lgtiming'+s for s in ('opentravel','opengrowth','closetravel','closegrowth','bounce')]
    for field,extra in [('argumentids',argids),('argumentnames',TIMING_NAMES),
                        ('argumentdefaults',[str(x) for x in TIMING_DEFAULTS])]:
        mutation[field]=json.dumps([*json.loads(mutation[field]),*extra],separators=(',',':'))
    mutation['proccode']=code+TIMING_SUFFIX
    if proto['inputs'] or proto.get('shadow'):
        for aid,name in zip(argids,TIMING_NAMES):
            reporter=arg(name);reporter.shadow=True
            proto['inputs'][aid]=[1,n.emit(reporter,proto_key)]
    for block in list(n.blocks.values()):
        if isinstance(block,dict) and block['opcode']=='procedures_call' and block['mutation']['proccode']==code:
            block['mutation'].update(proccode=mutation['proccode'],argumentids=mutation['argumentids'])
            for aid,value in zip(argids,TIMING_DEFAULTS):
                block['inputs'][aid]=[1,[10,str(value)]]
    n.procs[mutation['proccode']]=mutation


def apply_menu_timing(target, *, studio=True):
    n=UIProgram(target,exporting=not studio)
    menu=next(code for code in n.procs if code.startswith('Menu %s x '))
    if menu.endswith(TIMING_SUFFIX):raise ValueError('Menu timing already installed')
    specs=(
        (SOLVE,('position','velocity','target','seconds','bounce','elapsed'),advance_spring),
        (CLOCK,('owner',*TIMING_NAMES),update_clocks),
        (PROJECT,('owner',),root_pose),
    )
    for code,fields,_ in specs:n.declare(code,fields)
    for j,(code,_,body) in enumerate(specs):
        n.define(code,body(n),(162000+j*7500,7000))
    public=n.definition(menu)
    pose_call=next(k for k in procs(n,public,'procedures_call') if n.blocks[k]['mutation']['proccode']==POSE)
    insert_before(n,pose_call,[n.call(CLOCK,n.v('UI slot'),*[arg(k) for k in TIMING_NAMES])])
    remove_old_root_clock(n)
    layout=n.definition(GEOMETRY)
    project=next(k for k in procs(n,layout,'procedures_call') if n.blocks[k]['mutation']['proccode']==PHASE)
    replace_call(n,project,n.call(PROJECT,arg('owner')))
    # Continue smoothing custom destination changes while either channel is
    # moving, including when independent zero-duration growth already closed.
    progress=next(k for k in procs(n,layout,'data_replaceitemoflist')
                  if n.blocks[k]['fields']['LIST'][0]=='UI last open phase')
    set_socket(n,progress,'ITEM',maximum(abs_(n.item('UI travel progress',arg('owner'))),
                                         abs_(n.item('UI growth progress',arg('owner')))))
    # Extreme custom sizes and a lively close can undershoot below an 8 px
    # launcher. Bound actual body geometry before calculating its radius.
    thickness=next(k for k in procs(n,layout,'data_setvariableto')
                   if n.blocks[k]['fields']['VARIABLE'][0]=='UI half thickness')
    insert_before(n,thickness,[*n.clip('UI width',8,440),*n.clip('UI height',8,300)])
    reset=n.definition('UI reset')
    n.attach(n.sequence(reset)[-1],[cmd for field,value in SLOT_VALUES.items()
            for cmd in (n.clear(field),repeat(8,[n.add(field,value)]))],None)
    for field,value in SLOT_VALUES.items():
        target['lists'][n.storage(field,True)[1]][1]=[value]*8
    extend_menu(n,menu)
    return target
