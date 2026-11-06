"""Animate each private sheet to and from its row with the same two springs.

A Back fold is the reverse of a push. Only dismissing the public Menu selects
its close durations. Per-sheet signed velocity survives input interruptions,
including the interval after the optical face has merged into the source row.
"""
from .handoff_settle import TAIL, append, bind_condition, lookup, only
from .menu_handoff import GEOMETRY, OWNER
from .menu_layers import BEGIN, KEY, POSE, PUSH, RESET, TOP, insert_before, li, mix, procs, put
from .menu_timing import CLOCK, SOLVE, TIMING_DEFAULTS
from .motion_layout import set_socket
from .stable_pen import arg, iff
from .ui_components import UIProgram, AND, NOT, OR, div, eq, join, repeat, sub


STEP = 'UI step sheet travel %s owner %s'
FIELDS = ('travel p', 'travel v', 'dismissing')
SLOT = {'UI open travel seconds': TIMING_DEFAULTS[0],
        'UI close travel seconds': TIMING_DEFAULTS[2]}


def travel_active(n, index):
    return OR(NOT(eq(li(n, 'travel p', index), 0)), NOT(eq(li(n, 'travel v', index), 0)))


def extend_boolean(n, parent, slot, combine, extra):
    """Attach a condition to the existing reporter without rebuilding its inputs."""
    old = n.blocks[parent]['inputs'][slot][1]
    wrapper = n.emit(combine(eq(0, 0), extra), parent)
    operand = n.blocks[wrapper]['inputs']['OPERAND1']
    n.remove(operand[1])
    operand[1] = old
    n.blocks[old]['parent'] = wrapper
    n.blocks[parent]['inputs'][slot] = [2, wrapper]


def install_clock(n):
    # The public clock already clamps these settings, once per owner and frame.
    clock = n.definition(CLOCK)
    select = next(k for k in n.sequence(clock)
                  if n.blocks[k]['fields'].get('VARIABLE', [None])[0] == 'UI selected seconds')
    insert_before(n, select, [n.replace('UI open travel seconds', arg('owner'), n.v('UI opening seconds')),
                              n.replace('UI close travel seconds', arg('owner'), n.v('UI closing seconds'))])
    reset = n.definition('UI reset')
    append(n, n.sequence(reset)[-1], [cmd for field, value in SLOT.items()
                                      for cmd in (n.clear(field), repeat(8, [n.add(field, value)]))])
    for field, value in SLOT.items():
        n.target['lists'][n.storage(field, True)[1]][1] = [value] * 8


def install_records(n):
    records = n.target['lists']
    def values(name):
        return records[n.storage(name, True)[1]][1]
    for field, old in (('travel p', 'ink p'), ('travel v', 'ink v')):
        records[n.storage('UI layer ' + field, True)[1]][1] = list(values('UI layer ' + old))
    records[n.storage('UI layer dismissing', True)[1]][1] = [0] * len(values('UI layer owner'))
    reset = n.definition(RESET)
    append(n, n.sequence(reset)[-1], [n.clear('UI layer ' + field) for field in FIELDS])
    push = n.definition(PUSH)
    birth = only([k for k in lookup(n, push, 'data_addtolist', 'LIST', 'UI layer p')
                  if isinstance(n.blocks[k]['inputs']['ITEM'][1], list)], 'private sheet birth')
    append(n, birth, [n.add('UI layer ' + field, 0) for field in FIELDS])
    rerank = only(lookup(n, push, 'data_deleteoflist', 'LIST', 'UI layer p'), 'private sheet reorder')
    match = n.v('UI push match')
    append(n, rerank, [cmd for field in FIELDS for cmd in (
        n.add('UI layer ' + field, li(n, field, match)), n.list_op('data_deleteoflist', 'UI layer ' + field, INDEX=match))])
    prune = only(lookup(n, n.definition(BEGIN), 'data_deleteoflist', 'LIST', 'UI layer p'), 'private sheet removal')
    index = n.v('UI prune')
    append(n, prune, [n.list_op('data_deleteoflist', 'UI layer ' + field, INDEX=index) for field in FIELDS])
    gate = prune
    while n.blocks[gate]['opcode'] != 'control_if':
        gate = n.blocks[gate]['parent']
    extend_boolean(n, gate, 'CONDITION', AND, NOT(travel_active(n, index)))
    cleanup = only(lookup(n, n.definition('UI input'), 'data_replaceitemoflist', 'LIST', 'UI layer p'),
                   'removed public owner')
    append(n, cleanup, [put(n, field, n.v('UI private hit index'), 0) for field in FIELDS])


def step_travel(n):
    i, owner = arg('layer'), arg('owner')
    # A full dismissal stays in the close family while its old sheets withdraw,
    # even if the root opens again first. A fresh push/reversal clears the latch.
    return [iff(eq(li(n, 'goal', i), 1), [put(n, 'dismissing', i, 0)]),
            iff(eq(n.item('UI open', owner), 0), [put(n, 'dismissing', i, 1)]),
            n.set('UI sheet travel duration', n.item('UI open travel seconds', owner)),
            iff(eq(li(n, 'dismissing', i), 1), [n.set('UI sheet travel duration', n.item('UI close travel seconds', owner))]),
            n.call(SOLVE, li(n, 'travel p', i), li(n, 'travel v', i), li(n, 'goal', i),
                   n.v('UI sheet travel duration'), n.item('UI menu bounce', owner), n.item('UI frame seconds', owner)),
            put(n, 'travel p', i, n.v('UI spring p')), put(n, 'travel v', i, n.v('UI spring v'))]


def install_pose(n):
    pose = n.definition(POSE)
    timing = lookup(n, pose, 'data_setvariableto', 'VARIABLE', 'UI layer duration')
    close = only([k for k in timing if n.blocks[n.blocks[k]['parent']]['opcode'] == 'control_if'],
                 'private close growth setting')
    opening = only([k for k in timing if k != close], 'private open growth setting')
    i = n.v('UI panel step')
    insert_before(n, opening, [n.call(STEP, i, arg('owner'))])
    bind_condition(n, n.blocks[close]['parent'], eq(li(n, 'dismissing', i), 1))

    geometry = n.definition(GEOMETRY)
    i = arg('layer')
    # Width, height and corner radius use visible growth, while the center follows
    # signed travel. Keep the existing final alignment and stage-bound clamps.
    for axis in ('x', 'y'):
        positions = lookup(n, geometry, 'data_replaceitemoflist', 'LIST', 'UI layer ' + axis)
        interpolation = only([k for k in positions
                              if n.blocks[n.blocks[k]['inputs']['ITEM'][1]]['opcode'] == 'operator_add'],
                             'private center ' + axis)
        set_socket(n, interpolation, 'ITEM', mix(n.v('UI origin ' + axis), n.v('UI finish ' + axis), li(n, 'travel p', i)))
    # The center already includes signed travel, even when growth has crossed
    # zero. Only the half-extents need correcting to recover virtual ink edges.
    half_width = div(sub(n.v('UI finish w'), n.v('UI origin w')), 2)
    half_height = div(sub(n.v('UI finish h'), n.v('UI origin h')), 2)
    for field, delta in (('ink left travel', sub(0, half_width)), ('ink right travel', half_width),
                         ('ink top travel', half_height)):
        setter = only(lookup(n, geometry, 'data_replaceitemoflist', 'LIST', 'UI layer ' + field), field)
        set_socket(n, setter, 'ITEM', delta)


def install_paint(n):
    # The outgoing sheet alone owns the title until both springs finish. This also
    # covers zero growth with slow travel and zero travel with slow growth.
    gate = only(procs(n, n.definition(OWNER), 'control_if'), 'row ownership gate')
    both = n.blocks[gate]['inputs']['CONDITION'][1]
    if n.blocks[both]['opcode'] != 'operator_and':
        raise ValueError('Missing source-row path filter')
    extend_boolean(n, both, 'OPERAND1', OR, travel_active(n, n.v('UI source owner scan')))
    tail = only([k for k in procs(n, n.definition(TOP), 'procedures_call')
                 if n.blocks[k]['mutation']['proccode'] == TAIL], 'settling ink painter')
    extend_boolean(n, n.blocks[tail]['parent'], 'CONDITION', OR, travel_active(n, n.v('UI replay panel')))
    change = only(lookup(n, n.definition('LG render'), 'data_changevariableby', 'VARIABLE', 'UI damage slot'),
                  'private damage iterator')
    gate = n.blocks[change]['parent']
    condition = n.blocks[gate]['inputs']['CONDITION'][1]
    if n.blocks[gate]['opcode'] != 'control_if' or n.blocks[condition]['opcode'] != 'operator_and':
        raise ValueError('Missing settling ink damage branch')
    extend_boolean(n, condition, 'OPERAND1', OR, travel_active(n, n.v('UI damage slot')))
    key = only(lookup(n, n.definition(KEY), 'data_changevariableby', 'VARIABLE', 'UI key panel'), 'private scene key')
    insert_before(n, key, [n.set('preparedScene', join(n.v('preparedScene'), join('/', li(n, field, n.v('UI key panel')))))
                           for field in ('travel p', 'travel v')])


def apply_submenu_timing(target, *, studio=True):
    n = UIProgram(target, exporting=not studio)
    if STEP in n.procs:
        raise ValueError('Private submenu timing already installed')
    n.declare(STEP, ('layer', 'owner'))
    n.define(STEP, step_travel(n), (201500, 19800))
    install_clock(n)
    install_records(n)
    install_pose(n)
    install_paint(n)
    return target
