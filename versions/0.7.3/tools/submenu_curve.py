"""Expose four independent private sheet spring durations on the public Menu."""
import json

from .handoff_settle import append, only
from .menu_layers import POSE, insert_before, li, procs
from .menu_timing import MAX_DURATION, SOLVE
from .stable_pen import arg, iff
from .submenu_timing import STEP
from .ui_components import AND, NOT, OR, UIProgram, add, eq, gt, join, length, letter, lt, until


FIELD = 'submenu curve'
SUFFIX = ' ' + FIELD + ' %s'
DEFAULT = 'inherit'
READ = 'UI read submenu curve %s'
TIMES = 'UI submenu curve times'


def append_socket(n, code):
    proto_id = n.blocks[n.definition(code)]['inputs']['custom_block'][1]
    proto = n.blocks[proto_id]
    mutation = proto['mutation']
    argument_id = 'lgsubmenucurve'
    if argument_id in json.loads(mutation['argumentids']):
        raise ValueError('Menu already has an argument with the submenu curve ID')
    for key, value in (('argumentids', argument_id), ('argumentnames', FIELD), ('argumentdefaults', DEFAULT)):
        mutation[key] = json.dumps([*json.loads(mutation[key]), value], separators=(',', ':'))
    mutation['proccode'] = code + SUFFIX
    reporter = arg(FIELD)
    reporter.shadow = True
    proto['inputs'][argument_id] = [1, n.emit(reporter, proto_id)]
    for block in n.blocks.values():
        if isinstance(block, dict) and block['opcode'] == 'procedures_call' and block['mutation']['proccode'] == code:
            block['mutation'].update(proccode=mutation['proccode'], argumentids=mutation['argumentids'])
            block['inputs'][argument_id] = [1, [10, DEFAULT]]
    n.procs[mutation['proccode']] = mutation


def read_curve(n):
    """Accept exactly four comma-separated numbers, with an empty list for inheritance."""
    v = n.v
    curve = arg('curve')
    at = v('UI curve cursor')
    token = v('UI curve token')
    text = v('UI curve text')
    # A trailing delimiter flushes the final number, and also makes the cache
    # key unambiguously textual for Scratch's numeric-or-text comparison.
    source = join(curve, ',')
    numeric = add(token, 0)
    valid_token = AND(lt(n.length(TIMES), 4), AND(gt(length(token), 0), eq(token, numeric)))
    finish_token = [iff(valid_token, [n.set('UI curve seconds', numeric),
                        *n.clip('UI curve seconds', 0, MAX_DURATION), n.add(TIMES, v('UI curve seconds'))],
                        [n.set('UI curve valid', 0)]), n.set('UI curve token', '')]
    return [iff(NOT(eq(v('UI curve cache'), source)), [
        n.set('UI curve text', source), n.clear(TIMES), n.set('UI curve valid', 1),
        n.set('UI curve cursor', 1), n.set('UI curve token', ''),
        until(OR(gt(at, length(text)), eq(v('UI curve valid'), 0)), [
            n.set('UI curve character', letter(at, text)),
            iff(eq(v('UI curve character'), ','), finish_token,
                [n.set('UI curve token', join(token, v('UI curve character')))]),
            n.change('UI curve cursor', 1)]),
        iff(NOT(AND(eq(n.length(TIMES), 4), eq(v('UI curve valid'), 1))), [n.clear(TIMES)]),
        n.set('UI curve cache', text),
    ])]


def solver_call(n, definition):
    return only([k for k in procs(n, definition, 'procedures_call')
                 if n.blocks[k]['mutation']['proccode'] == SOLVE], 'private spring step')


def apply_submenu_curve(target, *, studio=True):
    n = UIProgram(target, exporting=not studio)
    menu = only([code for code in n.procs if code.startswith('Menu %s x ')], 'public Menu')
    if menu.endswith(SUFFIX) or STEP not in n.procs:
        raise ValueError('Expected the 0.7.2 private submenu springs and unextended Menu')
    pose = only([k for k in procs(n, n.definition(menu), 'procedures_call')
                 if n.blocks[k]['mutation']['proccode'] == POSE], 'private sheet simulation')

    # Read immediately before processing all private layers of this owner. Two
    # owners can alternate different curves without sharing any spring state.
    n.declare(READ, ('curve',))
    n.define(READ, read_curve(n), (208000, 19800))
    insert_before(n, pose, [n.call(READ, arg(FIELD))])
    reset = n.definition('UI reset')
    append(n, n.sequence(reset)[-1], [n.set('UI curve cache', ''), n.clear(TIMES)])

    # STEP has already latched a full dismissal before the travel solver.
    # Pick a private pair only for a push or a Back fold. The parent clock and
    # withdrawing sheets continue to use their original timing inputs.
    layer = arg('layer')
    index = n.v('UI curve index')
    growth = 'UI submenu growth override'
    insert_before(n, solver_call(n, n.definition(STEP)), [
        n.set(growth, -1),
        iff(AND(eq(li(n, 'dismissing', layer), 0), eq(n.length(TIMES), 4)), [
            n.set('UI curve index', 1), iff(eq(li(n, 'goal', layer), 0), [n.set('UI curve index', 3)]),
            n.set('UI sheet travel duration', n.item(TIMES, index)),
            n.set(growth, n.item(TIMES, add(index, 1))),
        ]),
    ])
    insert_before(n, solver_call(n, n.definition(POSE)), [
        iff(NOT(lt(n.v(growth), 0)), [n.set('UI layer duration', n.v(growth))])])
    append_socket(n, menu)
    return target
