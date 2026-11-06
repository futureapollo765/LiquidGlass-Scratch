"""Rotate the original row chevron about its center throughout the handoff."""
from . import ui_labels
from .body_ink import PASS, PATH, VECTORS
from .menu_layers import procs
from .stable_pen import arg, iff
from .ui_components import UIProgram, add, eq, math, mul, sub

DISCLOSURE = 'UI disclosure facing %s'


def apply_disclosure(target, *, studio=True):
    n = UIProgram(target, exporting=not studio)
    v = n.v
    n.declare(DISCLOSURE, ('angle',))
    n.define(DISCLOSURE, [
        ui_labels.costume('UI icon next'),
        n.set('UI path index', ui_labels.costume_info('number')),
        n.set('UI path data', n.item(VECTORS, v('UI path index'))),
        n.set('UI letter world x', v('UI cx')),
        n.set('UI letter world y', v('UI cy')),
        n.set('UI chevron cos', math('cos', arg('angle'))),
        n.set('UI chevron sin', math('sin', arg('angle'))),
        n.set('UI rotating chevron', 1), n.call(PATH), n.set('UI rotating chevron', 0),
    ], (147000,35000))

    # Apply the rotation to each original local vertex before the existing
    # affine stroke renderer computes stretch, outline thickness, and coverage.
    # This uses precisely the same source contour at every angle.
    statements = procs(n, n.definition(PASS), 'data_setvariableto')
    set_y = [k for k in statements if n.blocks[k]['fields']['VARIABLE'][0] == 'UI local y']
    if len(set_y) != 1:
        raise ValueError('Expected one local vertex decoder in the native path pass.')
    vertex = set_y[0]
    x,y = v('UI local x'), v('UI local y')
    c,s = v('UI chevron cos'), v('UI chevron sin')
    n.attach(vertex, [iff(eq(v('UI rotating chevron'),1), [
        n.set('UI rotated x',add(mul(x,c),mul(y,s))),
        n.set('UI local y',sub(mul(y,c),mul(x,s))),
        n.set('UI local x',v('UI rotated x')),
    ])], n.blocks[vertex]['next'])
    foreground = n.definition('UI foreground')
    n.attach(foreground,[n.set('UI rotating chevron',0)],n.blocks[foreground]['next'])
    return target
