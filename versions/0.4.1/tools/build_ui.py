"""Build a Scratch UI kit from a saved 0.3.0 Studio or component.

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


def add_ui(target, assets, document, studio):
    from .ui_components import apply_target
    from .ui_labels import apply_labels, patch_washes

    has_ui = any(isinstance(block, dict) and block.get('opcode') == 'procedures_prototype'
                 and block['mutation']['proccode'] == 'UI foreground'
                 for block in target['blocks'].values())
    if has_ui:
        patch_washes(target)
        return

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
