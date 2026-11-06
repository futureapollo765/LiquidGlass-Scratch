#!/usr/bin/env python3
"""Clear only the Liquid Glass renderer's reloadable saved frame buffers.

No Scratch blocks, scalar variables, component settings, lookup pixels, fixed
cache slots, assets, or list definitions are removed or changed. Run after
exporting a project that has accumulated runtime buffers.
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import zipfile

FRAME_BUFFERS = frozenset((
    'field', 'pixelBand', 'pixelDistortion', 'pixelEdge', 'pixelHighlight',
    'pixelLightX', 'pixelLightY', 'pixelTint',
))
COMMAND_LISTS = frozenset(('frameX', 'frameY', 'frameRGB', 'frameTransparency'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def procedure_nodes(blocks, code):
    """Inspect a procedure's own block tree without following custom calls."""
    definitions = []
    for block in blocks.values():
        if not isinstance(block, dict) or block.get('opcode') != 'procedures_definition':
            continue
        proto = blocks[block['inputs']['custom_block'][1]]
        if proto['mutation']['proccode'] == code:
            definitions.append(block)
    if len(definitions) != 1:
        raise ValueError(f'Expected exactly one {code} definition')
    pending, seen = [definitions[0].get('next')], set()
    while pending:
        ident = pending.pop()
        if not ident or ident in seen:
            continue
        seen.add(ident)
        block = blocks.get(ident)
        if not isinstance(block, dict):
            continue
        yield block
        pending.append(block.get('next'))
        for value in block.get('inputs', {}).values():
            pending.extend(x for x in value[1:] if isinstance(x, str))


def compact(source, destination, overwrite=False):
    source, destination = Path(source), Path(destination)
    if source.resolve() == destination.resolve():
        raise ValueError('Use a separate output file; preserve the input archive.')
    if destination.exists() and not overwrite:
        raise FileExistsError(f'{destination} already exists; choose a new filename.')
    source_bytes = source.read_bytes()
    with zipfile.ZipFile(source) as archive:
        entries = [(copy.copy(info), archive.read(info.filename)) for info in archive.infolist()]
    raw = dict((info.filename, data) for info, data in entries)['project.json']
    original = json.loads(raw)
    result = copy.deepcopy(original)
    changes = []
    for target_index, target in enumerate(result['targets']):
        names = {value[0]: ident for ident, value in target['lists'].items()}
        if not FRAME_BUFFERS.issubset(names):
            continue
        buffers = FRAME_BUFFERS
        if COMMAND_LISTS.intersection(names):
            if not COMMAND_LISTS.issubset(names):
                raise ValueError('Incomplete presentation buffer schema; input left intact')
            buffers = buffers | COMMAND_LISTS
        for procedure in ('LG initialize', 'LG render'):
            clears = {
                block['fields']['LIST'][1]
                for block in procedure_nodes(target['blocks'], procedure)
                if block.get('opcode') == 'data_deletealloflist'
            }
            if not all(names[name] in clears for name in buffers):
                raise ValueError(f'{procedure} does not clear every expected frame buffer')
        for name in sorted(buffers):
            ident = names[name]
            values = target['lists'][ident][1]
            changes.append({'targetIndex': target_index, 'target': target['name'],
                            'id': ident, 'list': name, 'removedItems': len(values),
                            'savedBytesRemoved': len(json.dumps(values, separators=(',', ':')).encode()) - 2})
            target['lists'][ident][1] = []
    if not changes:
        raise ValueError('No matching Liquid Glass frame-buffer schema found')
    # Only the explicitly listed, rebuildable buffer contents may differ.
    restored = copy.deepcopy(result)
    for change in changes:
        i, ident = change['targetIndex'], change['id']
        restored['targets'][i]['lists'][ident][1] = original['targets'][i]['lists'][ident][1]
    assert restored == original, 'Unexpected change outside frame-buffer contents'
    cleaned = json.dumps(result, separators=(',', ':'), ensure_ascii=True).encode()
    if len(cleaned) >= 5_000_000:
        raise ValueError(f'Cleanup still leaves {len(cleaned):,} JSON bytes; do not remove required data automatically.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w') as archive:
        for info, data in entries:
            archive.writestr(info, cleaned if info.filename == 'project.json' else data)
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        for info, data in entries:
            if info.filename != 'project.json':
                assert archive.read(info.filename) == data, info.filename
    assert source.read_bytes() == source_bytes, 'Input changed during cleanup'
    return {'source': str(source.resolve()), 'output': str(destination.resolve()),
            'sourceSHA256': digest(source_bytes), 'outputSHA256': digest(destination.read_bytes()),
            'projectJsonBytesBefore': len(raw), 'projectJsonBytesAfter': len(cleaned),
            'bytesRemoved': len(raw) - len(cleaned), 'buffers': changes,
            'onlyFrameBufferContentsChanged': True, 'allOtherArchiveEntriesIdentical': True,
            'sourcePreserved': True, 'underFiveMillionBytes': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source')
    parser.add_argument('output')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--overwrite', action='store_true', help='Replace an existing output only; input is always preserved.')
    args = parser.parse_args()
    report = compact(args.source, args.output, args.overwrite)
    text = json.dumps(report, indent=2) + '\n'
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text)
    print(text)
