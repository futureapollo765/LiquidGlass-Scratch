"""Align the menu highlight and the capsule used as the submenu's origin."""
from . import ui_labels
from .body_ink import WASH, affine
from .handoff_settle import lookup, only
from .menu_handoff import SOURCE, TITLE
from .menu_layers import LAUNCH, procs, replace_body
from .button_feedback import unlink_next
from .motion_layout import set_socket
from .stable_pen import arg
from .ui_components import UIProgram, maximum, mul, sub

INSET = 'UI inset menu highlight x %s y %s width %s height %s tone %s'
SHIFT_LEFT = 1
VERTICAL_INSET = 2


def update_title_padding(n, name, previous, updated):
    # Keep the row's actual label/chevron still when its optical capsule
    # shifts left. The resulting left and right source ink insets are equal.
    setter = only(lookup(n, n.definition(TITLE), 'data_setvariableto', 'VARIABLE', name), name)
    pending = [n.blocks[setter]['inputs']['VALUE'][1]]
    matches = []
    while pending:
        block = n.blocks[pending.pop()]
        for binding in block['inputs'].values():
            value = binding[1]
            if isinstance(value, str):
                pending.append(value)
            elif (block['opcode'] == 'operator_multiply' and str(value[1]) == str(previous)
                  and any(inp[1] == n.v('UI origin sx') for inp in block['inputs'].values())):
                matches.append(binding)
    if len(matches) != 2:
        raise ValueError('Both terms of the shared title interpolation must use the source padding')
    for match in matches:
        match[1][1] = str(updated)


def apply_menu_padding(target, *, studio=True):
    n = UIProgram(target, exporting=not studio)
    fields = ('x', 'y', 'width', 'height', 'tone')
    # The closed Menu launcher is also a button. Its hover and press are
    # already represented by its surface spring. Only open menu rows paint.
    launcher = n.sequence(n.definition(LAUNCH))
    hover = launcher[1]
    if n.blocks[hover]['opcode'] != 'control_if_else' or len(launcher) != 3:
        raise ValueError('Could not identify the collapsed launcher wash')
    unlink_next(n, hover)

    n.declare(INSET, fields)
    n.define(INSET, [n.call(ui_labels.WASH,
        affine(n, sub(arg('x'), SHIFT_LEFT), 'x'), affine(n, arg('y'), 'y'),
        mul(arg('width'), n.v('UI ink scale x')),
        mul(maximum(0, sub(arg('height'), 2*VERTICAL_INSET)), n.v('UI ink scale y')), arg('tone'))],
        (197000, 19200))
    replace_body(n, WASH, [n.call(INSET, *[arg(field) for field in fields])])

    source = n.definition(SOURCE)
    height = only(lookup(n, source, 'data_setvariableto', 'VARIABLE', 'UI origin h'), 'source height')
    set_socket(n, height, 'VALUE', maximum(.01, mul(sub(n.v('UI origin pitch'), 4+2*VERTICAL_INSET),
                                                 n.v('UI origin sy'))))
    n.attach(height, [n.change('UI origin x', mul(-SHIFT_LEFT, n.v('UI origin sx')))], n.blocks[height]['next'])
    update_title_padding(n, 'UI carried x', 9, 9+SHIFT_LEFT)
    update_title_padding(n, 'UI carried arrow x', 11, 11-SHIFT_LEFT)
