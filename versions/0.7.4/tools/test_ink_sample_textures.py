"""Check native subpixel stamp colors and placement in a packaged Studio or sprite."""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

from .stable_pen import opaque_png_rows


def unpack(filename):
    with zipfile.ZipFile(filename) as packet:
        key = 'project.json' if 'project.json' in packet.namelist() else 'sprite.json'
        doc = json.loads(packet.read(key))
        targets = doc.get('targets', [doc])
        costumes = next(t['costumes'] for t in targets if t['name'] == 'Liquid Glass')
        return costumes, {f: packet.read(f) for f in packet.namelist() if f != key}, targets


def verify(original, updated):
    before, old_assets, _ = unpack(original)
    after, new_assets, targets = unpack(updated)
    assert [c['name'] for c in before] == [c['name'] for c in after]
    old_samples, new_samples = set(), set()
    for old, new in zip(before, after):
        if not old['name'].startswith('UI ink sample '):
            assert old == new
            continue
        svg = ET.fromstring(old_assets[old['md5ext']])
        assert svg.attrib['viewBox'] == '0 0 8 8' and len(svg) == 1
        rgb = bytes.fromhex(svg[0].attrib['fill'].removeprefix('#'))
        w, h, kind, rows = opaque_png_rows(new_assets[new['md5ext']])
        assert (w, h, kind, new['bitmapResolution']) == (16, 16, 2, 2)
        assert (new['rotationCenterX'], new['rotationCenterY']) == (0, h)
        # At 12.5%, with no drawable rotation, the integer hardware anchor
        # is the lower left of exactly the complete sampled stage pixel.
        assert w / new['bitmapResolution'] * .125 == h / new['bitmapResolution'] * .125 == 1
        assert set(rows) == {rgb * w} and len(rows) == h
        old_samples.add(old['md5ext'])
        new_samples.add(new['md5ext'])
    assert len(old_samples) == len(new_samples) == 66
    refs = {a['md5ext'] for t in targets for a in t['costumes'] + t['sounds']}
    removed, added = old_assets.keys() - new_assets.keys(), new_assets.keys() - old_assets.keys()
    assert removed == old_samples - refs and added == new_samples
    assert all(old_assets[f] == new_assets[f] for f in old_assets.keys() & new_assets.keys())
    assert refs <= new_assets.keys()
    return {'source': str(original), 'candidate': str(updated),
            'sha256': hashlib.sha256(updated.read_bytes()).hexdigest(), 'checkedColors': len(new_samples),
            'unchangedCostumeNamesAndIndices': len(before), 'unreferencedGeneratedTexturesRemoved': len(removed),
            'otherAssetsIdentical': len(old_assets) - len(removed), 'passed': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'updated', 'report'):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    report = verify(args.original, args.updated)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
