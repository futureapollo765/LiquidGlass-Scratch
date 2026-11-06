#!/usr/bin/env python3
"""Preserve an immutable version before a modified Scratch project is reloaded."""
import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def snapshot(version=None, minor=False, note="", input_studio=None, input_component=None, input_optics=None,
             prior_published_studio=None):
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
        'tools/stable_pen.py': 'tools/stable_pen.py',
        'tools/upgrade_stable_pen.py': 'tools/upgrade_stable_pen.py',
        'tools/test_frame_presentation.cjs': 'tools/test_frame_presentation.cjs',
        'tools/test_renderer.cjs': 'tools/test_renderer.cjs',
        'tools/test_editor_runtime.cjs': 'tools/test_editor_runtime.cjs',
        'tools/vm_harness.cjs': 'tools/vm_harness.cjs',
        'tools/verify_editor_roundtrip.py': 'tools/verify_editor_roundtrip.py',
        'research/nary_blend_audit.json': 'research/nary_blend_audit.json',
    }
    if bool(input_studio) != bool(input_component):
        raise ValueError('Supply both original upgrade inputs together.')
    if input_studio:
        files[str(Path(input_studio).resolve())] = 'inputs/Studio_before_upgrade.sb3'
        files[str(Path(input_component).resolve())] = 'inputs/Component_before_upgrade.sprite3'
    if input_optics:
        files[str(Path(input_optics).resolve())] = 'inputs/EffOnly_reference.sb3'
    if prior_published_studio:
        published = Path(prior_published_studio).resolve()
        previous_name = f'LiquidGlass_Studio_{old}.sb3'
        old_manifest = json.loads((ROOT / 'versions' / old / 'manifest.json').read_bytes())
        if hashlib.sha256(published.read_bytes()).hexdigest() != old_manifest['files'][previous_name]['sha256']:
            raise ValueError('Prior published Studio does not match its original manifest')
        files[str(published)] = f'inputs/Studio_{old}_as_released.sb3'
    if (ROOT / 'CHANGELOG.md').is_file():
        files['CHANGELOG.md'] = 'CHANGELOG.md'
    if (ROOT / 'tools/compact_project.py').is_file():
        files['tools/compact_project.py'] = 'tools/compact_project.py'
    for name in ('build_ui.py', 'ui_components.py', 'ui_labels.py', 'test_ui_components.cjs',
                 'test_ui_highlights.cjs', 'menu_layers.py', 'glass_material.py', 'material_api.py',
                 'test_ui_layers.cjs', 'test_materials.cjs', 'test_native_save.cjs',
                 'check_material_upgrade.py', 'test_layer_presentation.cjs','grid_rows.py',
                 'panel_optics.py','motion_layout.py','body_ink.py','body_ink_path.py',
                 'body_ink_atlas.py','body_ink_raster.cpp','check_motion_upgrade.py',
                 'test_grid_pixels.cjs','test_control_motion.cjs','test_panel_edges.cjs',
                 'test_body_ink.cjs', 'menu_timing.py', 'disclosure.py', 'menu_handoff.py',
                 'stretch_gesture.py', 'reference_refraction.py', 'test_menu_timing.cjs',
                 'test_disclosure.cjs', 'test_menu_handoff.cjs', 'test_stretch_gesture.cjs',
                 'test_reference_refraction.cjs', 'check_spring_upgrade.py',
                 'button_feedback.py', 'gesture_spring.py', 'handoff_settle.py', 'ink_opacity.py', 'menu_padding.py',
                 'test_gesture_spring.cjs', 'test_handoff_settle.cjs', 'test_ink_opacity.cjs'):
        source = 'tools/' + name
        if (ROOT / source).is_file():
            files[source] = source
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
    parser.add_argument('--input-studio', type=Path, help='Preserve the original native Studio used by upgrade_stable_pen.py.')
    parser.add_argument('--input-component', type=Path, help='Preserve the original importable sprite used by upgrade_stable_pen.py.')
    parser.add_argument('--input-optics', type=Path, help='Preserve the native EffOnly project used to check optical displacement.')
    parser.add_argument('--prior-published-studio', type=Path, help='Also keep the last published bytes when its numbered Studio was edited in Scratch.')
    args = parser.parse_args()
    snapshot(args.version, args.minor, args.note, args.input_studio, args.input_component, args.input_optics,
             args.prior_published_studio)
