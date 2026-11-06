#!/usr/bin/env python3
"""Validate Scratch 3 archive graph and native block/procedure structure.

Based on Scratch VM src/serialization/sb3.js and supplied native SB3 references.
This deliberately rejects unknown extension IDs in this Scratch-only project.
The real-VM loader in vm_harness.cjs provides independent schema validation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

# Hexagonal sockets accept Boolean-shaped blocks in Scratch's editor. The VM
# tolerates arbitrary reporters here, which is not enough for GUI compatibility.
BOOLEAN_REPORTERS = {
    'operator_lt', 'operator_gt', 'operator_equals', 'operator_and',
    'operator_or', 'operator_not', 'operator_contains',
    'argument_reporter_boolean', 'data_listcontainsitem',
    'sensing_touchingobject', 'sensing_touchingcolor',
    'sensing_coloristouchingcolor', 'sensing_keypressed', 'sensing_mousedown',
}
BOOLEAN_SOCKETS = {
    'control_if': ('CONDITION',),
    'control_if_else': ('CONDITION',),
    'control_repeat_until': ('CONDITION',),
    'control_wait_until': ('CONDITION',),
    'control_while': ('CONDITION',),
    'operator_and': ('OPERAND1', 'OPERAND2'),
    'operator_or': ('OPERAND1', 'OPERAND2'),
    'operator_not': ('OPERAND',),
}


def validate(path):
    errors, warnings = [], []
    def check(ok, message):
        if not ok:
            errors.append(message)
    with zipfile.ZipFile(path) as archive:
        check(archive.testzip() is None, 'ZIP CRC failure')
        check('project.json' in archive.namelist(), 'Missing project.json')
        project = json.loads(archive.read('project.json'))
        check(project.get('meta', {}).get('semver') == '3.0.0', 'Expected Scratch 3 semver')
        check(set(project.get('extensions', [])) <= {'pen'}, 'Only native Pen extension is allowed')
        targets = project.get('targets', [])
        check(sum(t.get('isStage', False) for t in targets) == 1, 'Expected exactly one Stage')
        stage = next((t for t in targets if t.get('isStage')), {})
        all_assets = set()
        total_blocks = 0
        for target in targets:
            name = target.get('name', '?')
            blocks = target.get('blocks', {})
            # Blockly reserves this substring in focusable block IDs. Scratch's
            # palette uses variable/list IDs as reporter block IDs as well.
            for kind in ('blocks', 'variables', 'lists'):
                for ident in target.get(kind, {}):
                    for reserved in ('_field', '_connection'):
                        check(reserved not in ident,
                              f'{name}: {kind} ID {ident!r} contains Blockly reserved {reserved}')
            total_blocks += len(blocks)
            prototypes = {}
            variables = dict(stage.get('variables', {})) | target.get('variables', {})
            lists = dict(stage.get('lists', {})) | target.get('lists', {})
            for ident, block in blocks.items():
                if isinstance(block, list):
                    continue  # Compact top-level reporters are legal in SB3.
                op = block.get('opcode')
                if op == 'procedures_prototype':
                    m = block.get('mutation', {})
                    code = m.get('proccode')
                    check(code not in prototypes, f'{name}: duplicate procedure {code}')
                    prototypes[code] = m
                    try:
                        ids = json.loads(m['argumentids'])
                        names = json.loads(m['argumentnames'])
                        defaults = json.loads(m['argumentdefaults'])
                        check(len(ids) == len(names) == len(defaults), f'{name}: procedure argument counts differ: {code}')
                        check(len(ids) == code.count('%s') + code.count('%b') + code.count('%n'), f'{name}: procedure placeholders differ: {code}')
                        check(set(ids) == set(block.get('inputs', {})), f'{name}: prototype input IDs differ: {code}')
                    except (KeyError, TypeError, ValueError) as exc:
                        errors.append(f'{name}: malformed procedure mutation: {code}: {exc}')
            parents = {}
            for ident, block in blocks.items():
                if isinstance(block, list):
                    continue
                prefix = f'{name}/{ident} ({block.get("opcode")})'
                check(isinstance(block.get('opcode'), str), f'{prefix}: missing opcode')
                check(isinstance(block.get('topLevel'), bool), f'{prefix}: missing topLevel')
                check(isinstance(block.get('shadow'), bool), f'{prefix}: missing shadow')
                parent = block.get('parent')
                check(parent is None or parent in blocks, f'{prefix}: missing parent {parent}')
                if block.get('topLevel'):
                    check(parent is None, f'{prefix}: top-level block has parent')
                for input_name in BOOLEAN_SOCKETS.get(block.get('opcode'), ()):
                    inp = block.get('inputs', {}).get(input_name)
                    if not inp or len(inp) < 2 or inp[1] is None:
                        continue  # An empty Boolean socket is valid and means false.
                    child = blocks.get(inp[1]) if isinstance(inp[1], str) else None
                    if isinstance(child, dict):
                        check(child.get('opcode') in BOOLEAN_REPORTERS,
                              f'{prefix}: Boolean socket {input_name} contains non-Boolean {child.get("opcode")}')
                    elif isinstance(inp[1], list):
                        errors.append(f'{prefix}: Boolean socket {input_name} contains a round primitive reporter')
                refs = []
                if block.get('next') is not None:
                    refs.append(('next', block['next']))
                for input_name, inp in block.get('inputs', {}).items():
                    check(isinstance(inp, list) and 2 <= len(inp) <= 3 and inp[0] in (1, 2, 3), f'{prefix}: invalid input {input_name}: {inp}')
                    if not isinstance(inp, list):
                        continue
                    for value in inp[1:]:
                        if isinstance(value, str):
                            refs.append((input_name, value))
                        elif isinstance(value, list):
                            check(4 <= value[0] <= 13, f'{prefix}: invalid primitive input {value}')
                            if value[0] == 12:
                                check(len(value) >= 3 and value[2] in variables, f'{prefix}: unknown variable primitive {value}')
                            if value[0] == 13:
                                check(len(value) >= 3 and value[2] in lists, f'{prefix}: unknown list primitive {value}')
                        else:
                            check(value is None, f'{prefix}: invalid input reference {value}')
                for input_name, ref in refs:
                    check(ref in blocks, f'{prefix}: {input_name} points to missing block {ref}')
                    if ref in blocks and isinstance(blocks[ref], dict):
                        check(blocks[ref].get('parent') == ident, f'{prefix}: child {ref} has parent {blocks[ref].get("parent")}')
                    parents.setdefault(ref, set()).add(ident)
                for field_name, field in block.get('fields', {}).items():
                    if field_name in ('VARIABLE', 'LIST'):
                        expected = variables if field_name == 'VARIABLE' else lists
                        check(len(field) >= 2 and field[1] in expected, f'{prefix}: missing {field_name} ID {field}')
                if block.get('opcode') == 'procedures_call':
                    m = block.get('mutation', {})
                    code = m.get('proccode')
                    check(code in prototypes, f'{prefix}: undefined procedure {code}')
                    if code in prototypes:
                        p = prototypes[code]
                        check(m.get('warp') == p.get('warp'), f'{prefix}: warp disagrees for {code}')
                        try:
                            check(json.loads(m.get('argumentids', '[]')) == json.loads(p['argumentids']), f'{prefix}: argument IDs disagree for {code}')
                            check(set(block.get('inputs', {})) == set(json.loads(p['argumentids'])), f'{prefix}: missing/extra procedure inputs for {code}')
                        except (KeyError, ValueError):
                            pass
            for ident, parent_ids in parents.items():
                check(len(parent_ids) == 1, f'{name}/{ident}: shared block has multiple parents {parent_ids}')
            for ident, block in blocks.items():
                if isinstance(block, dict) and not block.get('topLevel'):
                    check(ident in parents, f'{name}/{ident}: detached non-top-level block')
            for asset in target.get('costumes', []) + target.get('sounds', []):
                filename = asset.get('md5ext', asset.get('assetId', '') + '.' + asset.get('dataFormat', ''))
                all_assets.add(filename)
                check(filename in archive.namelist(), f'{name}: missing asset {filename}')
                if filename in archive.namelist():
                    check(hashlib.md5(archive.read(filename)).hexdigest() == asset.get('assetId'), f'{name}: asset MD5 mismatch {filename}')
            costumes = target.get('costumes', [])
            check(bool(costumes), f'{name}: no costumes')
            check(0 <= target.get('currentCostume', 0) < len(costumes), f'{name}: currentCostume outside range')
        report = {'path': str(Path(path).resolve()), 'targets': len(targets), 'blocks': total_blocks, 'assets': len(all_assets), 'extensions': project.get('extensions', []), 'errors': errors, 'warnings': warnings, 'passed': not errors}
        return report

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--output')
    args = parser.parse_args()
    result = validate(args.project)
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        Path(args.output).write_text(text + '\n')
    raise SystemExit(not result['passed'])
