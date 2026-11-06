#!/usr/bin/env python3
"""Preserve an immutable version before a modified Scratch project is reloaded."""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(version=None, minor=False, note=""):
    marker = ROOT / 'VERSION'
    old = marker.read_text().strip() if marker.exists() else None
    if version is None:
        major, middle, patch = map(int, old.split('.')) if old else (0, 1, -1)
        version = f'0.{middle + 1}.0' if minor else f'0.{middle}.{patch + 1}'
    parts = version.split('.')
    if len(parts) != 3 or not all(p.isdigit() for p in parts) or int(parts[0]) != 0:
        raise ValueError('Use version 0.x.x; the first digit remains under user control.')
    folder = ROOT / 'versions' / version
    if folder.exists():
        raise FileExistsError(f'Version {version} already exists; snapshots are never overwritten.')
    files = {
        'LiquidGlass_Studio.sb3': f'LiquidGlass_Studio_{version}.sb3',
        'LiquidGlass_Component.sprite3': f'LiquidGlass_Component_{version}.sprite3',
        'LiquidGlass_Studio.project.json': 'project.json',
        'build_renderer.py': 'build_renderer.py',
        'README.md': 'README.md',
        'tools/snapshot_release.py': 'tools/snapshot_release.py',
        'tools/repair_editor_ids.py': 'tools/repair_editor_ids.py',
        'tools/validate_sb3.py': 'tools/validate_sb3.py',
    }
    if (ROOT / 'CHANGELOG.md').is_file():
        files['CHANGELOG.md'] = 'CHANGELOG.md'
    if (ROOT / 'tools/compact_project.py').is_file():
        files['tools/compact_project.py'] = 'tools/compact_project.py'
    manifest = {'version': version, 'previous': old, 'createdUTC': datetime.now(timezone.utc).isoformat(),
                'note': note, 'files': {}, 'validation': 'Build checkpoint; final verification recorded separately.'}
    for source in files:
        if not (ROOT / source).is_file():
            raise FileNotFoundError(source)
    folder.mkdir(parents=True)
    for source, name in files.items():
        target = folder / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, target)
        manifest['files'][name] = {'sha256': hashlib.sha256(target.read_bytes()).hexdigest(), 'bytes': target.stat().st_size}
    (folder / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    marker.write_text(version + '\n')
    print(f'Preserved {folder}')
    return folder


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version')
    parser.add_argument('--minor', action='store_true', help='Major framework change: increment middle digit and reset patch.')
    parser.add_argument('--note', default='')
    args = parser.parse_args()
    snapshot(args.version, args.minor, args.note)
