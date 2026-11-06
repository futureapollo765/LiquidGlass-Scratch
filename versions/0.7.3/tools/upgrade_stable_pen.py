#!/usr/bin/env python3
"""Apply retained Pen presentation to an existing native Studio or sprite archive.

Run once per input. For example, from a release containing the original inputs:
  python3 tools/upgrade_stable_pen.py inputs/Studio_before_upgrade.sb3 upgraded.sb3
  python3 tools/upgrade_stable_pen.py inputs/Component_before_upgrade.sprite3 upgraded.sprite3
"""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile

if __package__:
    from .stable_pen import apply_target
else:
    from stable_pen import apply_target


def upgrade_archive(source, output, *, overwrite=False, json_output=None, transform=None):
    source, output = Path(source), Path(output)
    destinations = [output] + ([Path(json_output)] if json_output else [])
    if len({p.resolve() for p in [source, *destinations]}) != 1 + len(destinations):
        raise ValueError('The input archive, output archive, and optional JSON must have distinct paths.')
    for path in destinations:
        if path.exists() and not overwrite:
            raise FileExistsError(f'{path} already exists. Select a new path or explicitly use --overwrite.')

    source_bytes = source.read_bytes()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as original:
        entries = original.namelist()
        if len(entries) != len(set(entries)):
            raise ValueError('Duplicate archive entry names')
        json_entries = set(entries) & {'project.json', 'sprite.json'}
        if len(json_entries) != 1:
            raise ValueError('Expected one project.json or sprite.json entry')
        entry = json_entries.pop()
        document = json.loads(original.read(entry))
        targets = document['targets'] if entry == 'project.json' else [document]
        renderers = [target for target in targets if any(
            isinstance(block, dict) and block.get('opcode') == 'procedures_prototype'
            and block.get('mutation', {}).get('proccode') == 'LG render'
            for block in target.get('blocks', {}).values())]
        if len(renderers) != 1:
            raise ValueError('Expected exactly one Liquid Glass renderer with an LG render definition')
        assets = {name: original.read(name) for name in entries if name != entry}
        # An update may replace the renderer's generated sample textures.
        # Never drop artwork, a shared asset, or any still-referenced file.
        sample_textures = {c['md5ext'] for t in renderers for c in t.get('costumes', [])
                           if c['name'].startswith('UI ink sample ') and c['dataFormat'] == 'svg'}
        if transform is None:
            apply_target(renderers[0], assets)
        else:
            transform(renderers[0], assets, document, entry == 'project.json')
        retired = set(entries) - {entry} - set(assets)
        still_used = {a['md5ext'] for t in targets for a in t.get('costumes', []) + t.get('sounds', [])}
        if retired - sample_textures or retired & still_used:
            raise ValueError('The upgrade attempted to retire a protected or referenced asset')
        encoded = json.dumps(document, separators=(',', ':'), allow_nan=False).encode('utf-8')
        if len(encoded) >= 5_000_000:
            raise ValueError(f'{entry} would be {len(encoded):,} bytes. Compact the saved frame buffers first.')

        result = io.BytesIO()
        with zipfile.ZipFile(result, 'w') as destination:
            destination.comment = original.comment
            for info in original.infolist():
                if info.filename in retired:
                    continue
                data = encoded if info.filename == entry else assets[info.filename]
                destination.writestr(copy.copy(info), data)
            for name in sorted(assets.keys() - set(entries)):
                # A fixed timestamp makes repeated upgrades byte-identical.
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                destination.writestr(info, assets[name])
        payload = result.getvalue()
        with zipfile.ZipFile(io.BytesIO(payload)) as check:
            if check.testzip() is not None or check.read(entry) != encoded:
                raise ValueError('Upgraded archive failed verification')
            for name in entries:
                if name != entry and name not in retired and check.read(name) != original.read(name):
                    raise ValueError(f'Original asset changed: {name}')

    for path, data in zip(destinations, [payload, encoded]):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('wb' if overwrite else 'xb') as stream:
            stream.write(data)
    return {'source': str(source.resolve()), 'output': str(output.resolve()),
            'sourceSHA256': hashlib.sha256(source_bytes).hexdigest(),
            'outputSHA256': hashlib.sha256(payload).hexdigest(), 'jsonBytes': len(encoded),
            'newAssets': len(assets.keys() - set(entries)), 'originalAssetsPreserved': not bool(retired),
            'retiredGeneratedSampleTextures': len(retired)}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--json-output', type=Path, help='Write the exact upgraded JSON beside the archive.')
    parser.add_argument('--overwrite', action='store_true', help='Permit replacement of existing outputs.')
    args = parser.parse_args()
    print(json.dumps(upgrade_archive(args.source, args.output, overwrite=args.overwrite,
                                    json_output=args.json_output), indent=2))
