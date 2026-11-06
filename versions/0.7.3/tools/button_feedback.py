"""Keep the public Button's hover and press feedback in its motion."""
from .body_ink import FACE
from .menu_layers import procs
from .ui_components import UIProgram
from .ui_labels import FOREGROUND, TEXT


def unlink_next(n, key):
    block = n.blocks[key]
    parent, tail = block['parent'], block['next']
    if n.blocks[parent]['next'] != key:
        raise ValueError('Unexpected incoming edge in the Button feedback stack')
    n.blocks[parent]['next'] = tail
    if tail is not None:
        n.blocks[tail]['parent'] = parent
    n.remove(key)


def apply_button_feedback(target, *, studio=True):
    n = UIProgram(target, exporting=not studio)
    art = n.definition(FOREGROUND)
    button_face, = (
        k for k in procs(n, art, 'procedures_call')
        if n.blocks[k]['mutation']['proccode'] == FACE and
        next(iter(n.blocks[k]['inputs'].values()))[1] == [10, 'button']
    )
    wash = n.blocks[button_face]['next']
    text = n.blocks[wash]['next']
    if n.blocks[wash]['opcode'] != 'control_if_else' or n.blocks[text]['mutation']['proccode'] != TEXT:
        raise ValueError('Could not identify the inner Button wash before its label')
    unlink_next(n, wash)

    # The baseline optical highlight and tint are user inputs. Remove only
    # the temporary additions formerly layered on top of those values.
    code = next(code for code in n.procs if code.startswith('Button %s x '))
    changes = [k for k in procs(n, n.definition(code), 'data_changevariableby')
               if n.blocks[k]['fields']['VARIABLE'][0] in ('UI shine', 'UI tint')]
    if len(changes) != 4:
        raise ValueError('Unexpected number of Button hover and press accents')
    for k in changes:
        unlink_next(n, k)
