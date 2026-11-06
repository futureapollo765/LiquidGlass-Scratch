"""Use the current signed pull for Button and Menu deformation in native Scratch."""
from .gesture_spring import FOLLOW
from .motion_layout import PULL, STRETCH
from .menu_layers import li
from .stable_pen import arg, iff
from .stretch_gesture import GESTURE
from .ui_components import UIProgram, AND, NOT, OR, abs_, add, div, eq, gt, lt, mul, sub


TRACK = 'UI track held pull %s offset %s limit %s center %s velocity %s guide %s previous %s'
FIELDS = ('owner', 'offset', 'limit', 'center', 'velocity', 'guide', 'previous')


def track(n):
    v = n.v
    owner, offset, limit, center, velocity, guide, previous = map(arg, FIELDS)
    target = v('UI grip target')
    step = v('UI pointer step')
    dest = v('UI grip destination')
    # Usually aim at the current bounded displacement from mouse-down. If a
    # fresh step reverses before the spring has caught up, let that reversal
    # be seen immediately. Once it settles at this temporary guide, reacquire
    # the absolute target even if the mouse hasn't moved. Zero is always zero.
    redirect = [
        iff(lt(mul(step, sub(dest, center)), 0), [n.set('UI grip destination', center)]),
        n.change('UI grip destination', step),
        iff(AND(gt(mul(target, center), 0),lt(mul(target, dest), 0)), [n.set('UI grip destination', 0)]),
        *n.clip('UI grip destination', mul(-1, limit), limit),
    ]
    return [
        n.set('UI grip force', mul(mul(.65, n.item('pull', owner)), offset)),
        n.set('UI grip target', div(mul(limit, v('UI grip force')), add(limit, abs_(v('UI grip force'))))),
        n.set('UI pointer step', sub(target, previous)),
        n.set('UI grip destination', guide),
        iff(eq(step, 0), [
            iff(OR(eq(target, 0), lt(abs_(sub(guide, center)), .12)), [n.set('UI grip destination', target)]),
        ], [
            iff(OR(eq(target, 0), gt(mul(step, sub(target, center)), 0)),
                [n.set('UI grip destination', target)], redirect),
        ]),
        n.call(FOLLOW, center, velocity, dest, step, n.item('UI grip seconds', owner), n.item('UI grip bounce', owner)),
        # The contour is abs(signed spring position), never its historical
        # maximum. Its release velocity is the derivative of that same extent.
        n.set('UI grip center', v('UI spring p')),
        n.set('UI grip residual', v('UI spring v')),
        iff(lt(v('UI grip center'), 0), [n.set('UI grip residual', mul(-1, v('UI spring v')))]),
        iff(eq(v('UI grip center'), 0), [n.set('UI grip residual', abs_(v('UI spring v')))]),
    ]


def held(n):
    o = arg('owner')
    get = lambda name: n.item(name, o)
    put = lambda name, value: n.replace(name, o, value)
    path = n.v('UI captured path')
    face_changed = NOT(eq(path, get('UI contact path')))
    reset = [put('UI '+field+' '+a, 0) for a in 'xy' for field in ('contact', 'contact velocity',
                                                                      'grip reach', 'reach velocity')]
    begin = [iff(face_changed, reset), put('UI contact path', path), put(GESTURE, 1)]
    for a in 'xy':
        begin += [put('UI grip guide '+a, get('UI contact '+a)), put('UI grip target '+a, 0)]
    body = [n.set('UI captured path', ''),
            iff(gt(n.v('UI pressed layer'), 0), [n.set('UI captured path', li(n,'path',n.v('UI pressed layer')))]),
            iff(OR(eq(get(GESTURE), 0), face_changed), begin)]
    for a, limit in [('x', 28), ('y', 20)]:
        center, velocity = 'UI contact '+a, 'UI contact velocity '+a
        guide, previous = 'UI grip guide '+a, 'UI grip target '+a
        body += [n.call(TRACK, o, sub(n.v('UI pointer '+a), n.v('UI down '+a)), limit,
                        get(center), get(velocity), get(guide), get(previous)),
                 put(guide, n.v('UI grip destination')), put(previous, n.v('UI grip target')),
                 put(center, n.v('UI grip center')), put(velocity, n.v('UI spring v')),
                 put('UI grip reach '+a, abs_(n.v('UI grip center'))), put('UI reach velocity '+a, n.v('UI grip residual'))]
    return body


def soften_limit(n):
    # On short axes the former 38% clamp made many distinct long pulls
    # render at one size. Preserve the original slope through 25%, then
    # approach 38% with a matching tangent and no flat interval.
    seq = n.sequence(n.definition(STRETCH))
    for a, extent, limit in [('x', 'width', 28), ('y', 'height', 20)]:
        lane = 'UI stretch '+a
        start, = [k for k in seq if n.blocks[k]['fields'].get('VARIABLE', [None])[0] == lane]
        s = n.v(lane)
        excess = sub(s, .25)
        eligible = AND(gt(s, .25), lt(arg(extent), 1.35*limit/.38))
        ceiling = n.v('UI grip ratio limit')
        curvature = div(sub(ceiling, .38), mul(.13, sub(ceiling, .25)))
        n.attach(start, [iff(eligible, [
            # The signed contact asymptotically approaches limit. Map that
            # maximum to 38%; as the axis gets longer the correction tends
            # continuously to zero. Use the scale block's minimum extent.
            n.set('UI grip ratio limit', arg(extent)),
            iff(lt(ceiling, 8), [n.set('UI grip ratio limit', 8)]),
            n.set('UI grip ratio limit', div(1.35*limit, ceiling)),
            n.set(lane, add(.25, div(excess, add(1, mul(excess, curvature))))),
        ])], n.blocks[start]['next'])


def apply_reversible_grip(target, *, studio=True):
    n = UIProgram(target, exporting=not studio)
    root, = n.sequence(n.definition(PULL))
    block = n.blocks[root]
    if block['opcode'] != 'control_if_else' or FOLLOW not in n.procs:
        raise ValueError('Expected the spring-driven grip with separate held and release branches')
    n.declare(TRACK, FIELDS)
    n.define(TRACK, track(n), (218000, 9000))
    # Replace only the captured branch. The click routing, private-layer
    # transform, and first-release-frame handoff keep their original blocks.
    old = block['inputs']['SUBSTACK'][1]
    block['inputs']['SUBSTACK'] = [2, n.chain(held(n), root)[0]]
    while old:
        following = n.blocks[old]['next']
        n.remove(old)
        old = following
    soften_limit(n)
    return target
