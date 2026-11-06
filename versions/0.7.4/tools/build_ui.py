"""Build the Scratch UI kit from a native 0.3.x through 0.7.4 Studio or component.

The source archive stays intact. Run from a workspace or release directory:
    python3 -m tools.build_ui base.sb3 ui.sb3 --json-output project.json
    python3 -m tools.build_ui base.sprite3 ui.sprite3
"""
import argparse
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from .compact_project import compact
from .stable_pen import Native, Node, iff, op
from .upgrade_stable_pen import upgrade_archive


def block_writer(target):
    writer = Native(target)
    writer.next_id = max((int(key[9:]) for key in target['blocks']
                          if key.startswith('lgpresent') and key[9:].isdigit()), default=0)
    return writer


def studio_actions(target):
    """Wire the published demo events to their visible effects using native blocks."""
    writer = block_writer(target)
    action = writer.v('UI action')
    effects = [iff(op('equals', action, 'Switch background'), [
        writer.set('Background', op('subtract', 3, writer.v('Background')))])]
    for path, setting, value in (
        ('Background>Photo', 'Background', 1), ('Background>Grid', 'Background', 2),
        ('Detail>Fine', 'Quality', 1), ('Detail>Balanced', 'Quality', 2), ('Detail>Fast', 'Quality', 3),
    ):
        effects.append(iff(op('equals', action, path), [writer.set(setting, value)]))
    code = writer.definition('UI demo action')
    describe = [
        iff(op('equals', writer.v('Background'), 2), [writer.set('UI photo name', 'Grid')],
            [writer.set('UI photo name', 'Photo')]),
        writer.set('UI quality name', 'Fast'),
        iff(op('equals', writer.v('Quality'), 1), [writer.set('UI quality name', 'Fine')]),
        iff(op('equals', writer.v('Quality'), 2), [writer.set('UI quality name', 'Balanced')]),
        writer.set('UI sidebar caption', op('join', 'Workspace|', op('join', writer.v('UI photo name'),
            op('join', '|', writer.v('UI quality name'))))),
    ]
    # A separate button can change the wallpaper with the options menu closed.
    # When that submenu reopens its checkmark should describe the current setting.
    for page, setting_name in [('Background', 'UI photo name'), ('Detail', 'UI quality name')]:
        describe.append(iff(op('equals', writer.item('UI page', 3), page), [
            writer.list_op('data_replaceitemoflist', 'UI selected path', INDEX=3,
                           ITEM=op('join', page + '>', writer.v(setting_name)))]))
    writer.attach(code, [iff(op('equals', writer.v('UI fired'), 1), effects), *describe],
                  writer.blocks[code]['next'])
    init = writer.definition('LG initialize')
    writer.attach(writer.sequence(init)[-1], [writer.set('UI sidebar caption', 'Workspace|Photo|Balanced')], None)

    for block in writer.blocks.values():
        if not isinstance(block, dict) or block.get('opcode') != 'procedures_call':
            continue
        if not block['mutation']['proccode'].startswith('Background '):
            continue
        for key, binding in block['inputs'].items():
            if binding == [1, [10, 'Library']]:
                block['inputs'][key] = [3, writer.v('UI sidebar caption'), [10, 'Workspace']]


def pointer_bridge(stage, message, message_id):
    """A native Stage press starts a hat even if the render script is still busy."""
    stage['broadcasts'][message_id] = message
    writer = block_writer(stage)
    hat = writer.emit(Node('event_whenstageclicked'), None)
    writer.blocks[hat].update(topLevel=True, x=48, y=40)
    sender = writer.emit(Node('event_broadcast'), hat)
    writer.blocks[sender]['inputs'] = {'BROADCAST_INPUT': [1, [11, message, message_id]]}
    writer.blocks[hat]['next'] = sender


def reserve_entry_space(target):
    # The two branches of the new main loop are taller than the old Glass demo.
    # Keep the user's existing stacks aligned below it, including attached notes.
    blocks = target['blocks']
    moved = set()
    for key, block in blocks.items():
        if not isinstance(block, dict) or not block.get('topLevel'):
            continue
        if block['opcode'] == 'event_whenflagclicked' or block['x'] >= 24000 or block['y'] >= 30000:
            continue
        block['y'] += 1100
        moved.add(key)
    for note in target['comments'].values():
        if note.get('blockId') in moved and isinstance(note.get('y'), (float, int)):
            note['y'] += 1100


def shorten_new_block_ids(target, original_ids, *, compact_sprite=False):
    """Shorten builder-only IDs the way the native editor does on save.

    Keep existing Studio IDs and all public calls/definition/argument IDs.
    In the reusable sprite also shorten older generated private block IDs to
    leave space for the receiving project. The native VM reassigns local IDs
    when adding a sprite to a host. Never rewrite user text or list values.
    """
    blocks=target['blocks']
    reserved=original_ids | set(blocks) | set(target['variables']) | set(target['lists']) | set(target['comments'])
    alphabet='0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
    next_id=0
    ids={}
    for key in blocks:
        if not key.startswith('lgpresent'):continue
        if key in original_ids:
            b=blocks[key]
            if not compact_sprite or not isinstance(b,dict) or b.get('topLevel') or b.get('comment') or b['opcode'].startswith('procedures_'):continue
        while True:
            i=next_id; next_id+=1
            s=alphabet[i%62]; i//=62
            while i:
                s=alphabet[i%62]+s; i//=62
            candidate='~'+s
            if candidate not in reserved:break
        ids[key]=candidate
    for b in blocks.values():
        if not isinstance(b,dict):continue
        for edge in ('next','parent'):
            if b.get(edge) in ids:b[edge]=ids[b[edge]]
        for binding in b.get('inputs',{}).values():
            for j,val in enumerate(binding[1:],1):
                if isinstance(val,str) and val in ids:binding[j]=ids[val]
    for note in target['comments'].values():
        if note.get('blockId') in ids:note['blockId']=ids[note['blockId']]
    target['blocks']={ids.get(k,k):v for k,v in blocks.items()}


def shorten_new_storage_ids(target, original_ids, document):
    """Keep the new sprite import small without removing pixel or editing data.

    Native scalar/list reporters repeat their storage ID at every use. Give
    only *new* private storage compact IDs; visible names and values stay intact.
    """
    targets=document.get('targets',[target])
    reserved={ident for t in targets for table in ('variables','lists','blocks','comments','broadcasts')
              for ident in t.get(table,{})}
    ids={}
    j=0
    for table in ('variables','lists'):
        for ident in target[table]:
            if ident in original_ids or not ident.startswith('lgframe'):continue
            while True:
                j+=1; new='m~'+format(j,'x')
                if new not in reserved:break
            ids[ident]=new
    for b in target['blocks'].values():
        if not isinstance(b,dict):continue
        for key,value in b.get('fields',{}).items():
            if key in ('VARIABLE','LIST') and len(value)>=2 and value[1] in ids:value[1]=ids[value[1]]
        for binding in b['inputs'].values():
            for ref in binding[1:]:
                if isinstance(ref,list) and ref[0] in (12,13) and ref[2] in ids:ref[2]=ids[ref[2]]
    for table in ('variables','lists'):
        target[table]={ids.get(k,k):v for k,v in target[table].items()}


def install_050(target, assets, document, studio):
    from .ui_components import apply_target
    from .ui_labels import apply_labels, patch_washes

    has_ui = any(isinstance(block, dict) and block.get('opcode') == 'procedures_prototype'
                 and block['mutation']['proccode'] == 'UI foreground'
                 for block in target['blocks'].values())
    if has_ui:
        patch_washes(target)
    else:
        apply_target(target, studio=studio)
        apply_labels(target, assets)
        if studio:
            studio_actions(target)
            stage = next(t for t in document['targets'] if t.get('isStage'))
            for block in target['blocks'].values():
                if not isinstance(block, dict) or block.get('opcode') != 'event_whenbroadcastreceived':
                    continue
                name, ident = block['fields']['BROADCAST_OPTION'][:2]
                if name == 'LG UI pointer down':
                    pointer_bridge(stage, name, ident)
            for bid, name in target.get('broadcasts', {}).items():
                stage['broadcasts'].setdefault(bid, name)
        reserve_entry_space(target)

    from .menu_layers import apply_menu_layers
    from .glass_material import apply_material
    from .material_api import public_inputs
    apply_menu_layers(target, assets, studio=studio)
    apply_material(target)
    public_inputs(target, studio=studio)


def add_ui(target, assets, document, studio):
    from .grid_rows import apply_grid_rows
    from .panel_optics import apply_panel_optics
    from .motion_layout import apply_motion_layout
    from .body_ink import apply_body_ink
    from .menu_timing import apply_menu_timing
    from .disclosure import apply_disclosure
    from .menu_handoff import apply_menu_handoff
    from .stretch_gesture import apply_stretch_gesture
    from .reference_refraction import apply_reference_refraction
    from .button_feedback import apply_button_feedback
    from .gesture_spring import apply_gesture_spring
    from .handoff_settle import apply_handoff_settle
    from .ink_opacity import apply_ink_opacity
    from .menu_padding import apply_menu_padding
    from .submenu_timing import apply_submenu_timing
    from .submenu_curve import SUFFIX as SUBMENU_CURVE_SUFFIX, apply_submenu_curve
    from .reversible_grip import TRACK, apply_reversible_grip
    from .ink_sample_textures import apply_ink_sample_textures
    original_ids = set(target['blocks'])
    original_storage = set(target['variables']) | set(target['lists'])
    codes={b['mutation']['proccode'] for b in target['blocks'].values()
           if isinstance(b,dict) and b['opcode']=='procedures_prototype'}
    if 'LG expand grid for editing' not in codes:
        if 'LG rebuild blur %s' not in codes:
            install_050(target,assets,document,studio)
        apply_grid_rows(target,studio=studio)
        apply_motion_layout(target,studio=studio)
        apply_body_ink(target,assets,studio=studio)
        apply_panel_optics(target,studio=studio)
    if 'LG blend source texels' not in codes:
        apply_menu_timing(target,studio=studio)
        apply_disclosure(target,studio=studio)
        apply_menu_handoff(target,studio=studio)
        apply_stretch_gesture(target,studio=studio)
        apply_reference_refraction(target,studio=studio)
    if 'UI inset menu highlight x %s y %s width %s height %s tone %s' not in codes:
        apply_gesture_spring(target,studio=studio)
        apply_handoff_settle(target,studio=studio)
        apply_button_feedback(target,studio=studio)
        apply_menu_padding(target,studio=studio)
        apply_ink_opacity(target,assets,studio=studio)
    if 'UI step sheet travel %s owner %s' not in codes:
        apply_submenu_timing(target,studio=studio)
    apply_ink_sample_textures(target,assets,document=document)
    if not any(code.startswith('Menu %s x ') and code.endswith(SUBMENU_CURVE_SUFFIX) for code in codes):
        apply_submenu_curve(target,studio=studio)
    if TRACK not in codes:
        apply_reversible_grip(target,studio=studio)
    shorten_new_block_ids(target,original_ids,compact_sprite=not studio)
    shorten_new_storage_ids(target,original_storage,document)


def build(source, output, json_output=None, overwrite=False):
    source = Path(source)
    with TemporaryDirectory() as scratch:
        base = source
        if source.suffix == '.sb3':
            base = Path(scratch) / 'compacted.sb3'
            compact(source, base)
        result = upgrade_archive(base, output, json_output=json_output, overwrite=overwrite, transform=add_ui)
        result['source'] = str(source.resolve())
        result['sourceSHA256'] = hashlib.sha256(source.read_bytes()).hexdigest()
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--json-output', type=Path)
    parser.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.output, args.json_output, args.overwrite), indent=2))
