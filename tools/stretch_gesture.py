"""Upgrade native UI drag deformation in a saved 0.6.0 renderer.

The center follows signed motion measured from the press point. Size records
each axis's greatest excursion during this press, so moving back across the
press point cannot fold a stretched capsule. Both quantities relax on release.
"""
from .menu_layers import li, mix, procs, replace_body
from .motion_layout import PULL, STRETCH
from .stable_pen import arg, iff
from .ui_components import UIProgram, AND, OR, NOT, abs_, add, div, eq, gt, lt, maximum, minimum, mul, repeat, sub

REACH = ('UI grip reach x', 'UI grip reach y')
BIAS = ('UI grip start x', 'UI grip start y')
POINTER = ('UI grip target x', 'UI grip target y')
GUIDE = ('UI grip guide x', 'UI grip guide y')
GESTURE = 'UI grip active'


def contact(n):
    owner=arg('owner')
    v=n.v
    def item(name):
        return n.item(name,owner)
    def put(name,value):
        return n.replace(name,owner,value)

    enabled=OR(eq(item('UI kind'),'Button'),eq(item('UI drag enabled'),1))
    held=AND(eq(v('UI pressed id'),owner),AND(eq(v('UI down'),1),enabled))
    captured=[
        n.set('UI captured path',''),
        iff(gt(v('UI pressed layer'),0),
            [n.set('UI captured path',li(n,'path',v('UI pressed layer')))]),
    ]
    path_changed=NOT(eq(v('UI captured path'),item('UI contact path')))
    # A rapid re-grab on the same face starts where its release animation is.
    # A new descendant owns its own origin; residual from the previous face
    # must never get applied to this different layer.
    begin=[iff(path_changed,[put(name,0) for name in (*REACH,'UI contact x','UI contact y')]),
           *[put('UI grip '+field+' '+axis,item('UI contact '+axis))
             for axis in 'xy' for field in ('start','target','guide')],
           put('UI contact path',v('UI captured path')),put(GESTURE,1)]
    captured.append(iff(OR(eq(item(GESTURE),0),path_changed),begin))

    released=[put(GESTURE,0)]
    for axis,limit in [('x',28),('y',20)]:
        center='UI contact '+axis
        reach='UI grip reach '+axis
        distance=sub(v('UI pointer '+axis),v('UI down '+axis))
        force=mul(mul(.65,item('pull')),distance)
        bias=item('UI grip start '+axis)
        previous='UI grip target '+axis
        guide='UI grip guide '+axis
        target=v('UI grip target');step=v('UI pointer step')
        next_goal=v('UI grip destination')
        # A stepped pointer leaves part of its motion for subsequent renders.
        # If it reverses before reaching the old target, throw away residual
        # travel in the wrong direction. The new guide then follows the pointer
        # back immediately and remains stable when the next sample is stationary.
        redirected=[
            n.set('UI grip destination',item(guide)),
            iff(NOT(gt(mul(step,sub(next_goal,item(center))),0)),
                [n.set('UI grip destination',item(center))]),
            n.change('UI grip destination',step),
            # Returning on one side of the press should never cross the grip
            # ahead of the pointer itself. Preserve a re-grab's original bias.
            iff(AND(gt(sub(target,bias),0),gt(sub(item(center),bias),0)),
                [n.set('UI grip destination',maximum(bias,next_goal))]),
            iff(AND(lt(sub(target,bias),0),lt(sub(item(center),bias),0)),
                [n.set('UI grip destination',minimum(bias,next_goal))])]
        captured.extend([
            n.set('UI grip force',force),
            n.set('UI grip target',add(bias,
                div(mul(limit,v('UI grip force')),add(limit,abs_(v('UI grip force')))))),
            *n.clip('UI grip target',-limit,limit),
            n.set('UI pointer step',sub(target,item(previous))),
            iff(NOT(eq(step,0)),[
                iff(gt(mul(step,sub(target,item(center))),0),
                    [n.set('UI grip destination',target)],redirected),
                *n.clip('UI grip destination',-limit,limit),
                put(guide,next_goal),put(previous,target)]),
            n.set('UI grip center',mix(item(center),item(guide),v('UI motion relax'))),
            iff(lt(abs_(sub(item(guide),v('UI grip center'))),.01),
                [n.set('UI grip center',item(guide))]),
            put(center,v('UI grip center')),
            # Extension follows observed center travel, including catch-up
            # after a long pointer step. It never contracts while gripped.
            iff(gt(abs_(v('UI grip center')),item(reach)),[put(reach,abs_(v('UI grip center')))]),
        ])
        for name in (center,reach):
            released.extend([n.set('UI grip residual',mix(item(name),0,v('UI motion relax'))),
                             iff(lt(abs_(v('UI grip residual')),.016),[n.set('UI grip residual',0)]),
                             put(name,v('UI grip residual'))])
    released.append(iff(AND(eq(item(REACH[0]),0),eq(item(REACH[1]),0)),[put('UI contact path','')]))
    return [iff(held,captured,released)]


def scale(n):
    body=[]
    for axis,extent in [('x','width'),('y','height')]:
        # Each moving axis may grow. No amount is subtracted from the
        # perpendicular axis, even during a diagonal or a quick reversal.
        body.extend([n.set('UI stretch '+axis,div(mul(1.35,n.item('UI grip reach '+axis,arg('owner'))),
                                                  maximum(8,arg(extent)))),
                     *n.clip('UI stretch '+axis,0,.38),
                     n.set('UI axis scale '+axis,add(1,n.v('UI stretch '+axis)))])
    return body


def apply_stretch_gesture(target,*,studio=True):
    n=UIProgram(target,exporting=not studio)
    if GESTURE in {pair[0] for pair in target['lists'].values()}:
        raise ValueError('Stretch-only gesture is already installed')
    replace_body(n,PULL,contact(n))
    replace_body(n,STRETCH,scale(n))
    names=(*REACH,*BIAS,*POINTER,*GUIDE,GESTURE)
    # The public slot can be removed or reused for another component while a
    # pointer is down. Clear the new state alongside its existing grip state.
    settle=n.definition('UI settle')
    slot_reset=[key for key in procs(n,settle,'data_replaceitemoflist')
                if n.blocks[key]['fields']['LIST'][0]=='UI contact y']
    if len(slot_reset)!=1:
        raise ValueError('Could not locate the slot-reuse reset in UI settle')
    at=slot_reset[0]
    n.attach(at,[n.replace(name,n.v('UI settle id'),0) for name in names],n.blocks[at]['next'])
    reset=n.definition('UI reset')
    n.attach(n.sequence(reset)[-1],[step for name in names
        for step in (n.clear(name),repeat(8,[n.add(name,0)]))],None)
    for name in names:
        target['lists'][n.storage(name,True)[1]][1]=[0]*8
    return target
