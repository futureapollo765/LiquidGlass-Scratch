#!/usr/bin/env python3
"""Check that ScratchBlocks import/save preserved native source structure."""
import collections
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from validate_sb3 import validate, prototype_argument_reporter_ids


def inspect(path):
    with zipfile.ZipFile(path) as archive:
        project = json.loads(archive.read('project.json'))
    result = {}
    # These blocks are serialized as inline primitives by the native VM.
    primitives = {'math_number', 'math_positive_number', 'math_whole_number',
                  'math_integer', 'math_angle', 'colour_picker', 'text',
                  'event_broadcast_menu', 'data_variable', 'data_listcontents'}
    for target in project['targets']:
        display_reporters = prototype_argument_reporter_ids(target['blocks'])
        blocks = [b for identifier, b in target['blocks'].items()
                  if isinstance(b, dict) and identifier not in display_reporters]
        signatures = {}
        for block in blocks:
            if block['opcode'] == 'procedures_prototype':
                mutation = block['mutation']
                signatures[mutation['proccode']] = {
                    'arguments': json.loads(mutation['argumentnames']),
                    'defaults': json.loads(mutation['argumentdefaults']),
                    'warp': mutation['warp'],
                }
        result[target['name']] = {
            'definitions': sum(b['opcode'] == 'procedures_definition' for b in blocks),
            'signatures': signatures,
            'nonprimitive_opcode_counts': dict(collections.Counter(b['opcode'] for b in blocks if b['opcode'] not in primitives)),
            'body_argument_reporters': sorted(
                (opcode, name, count) for (opcode, name), count in collections.Counter(
                    (b['opcode'], b.get('fields', {}).get('VALUE', [None])[0])
                    for b in blocks if b['opcode'] in (
                        'argument_reporter_string_number', 'argument_reporter_boolean')
                ).items()),
        }
    return result

source, native = map(Path, sys.argv[1:3])
report = {'source': str(source.resolve()), 'native': str(native.resolve()),
          'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
          'native_sha256': hashlib.sha256(native.read_bytes()).hexdigest(),
          'source_structure': validate(source),
          'native_structure': validate(native), 'source_code': inspect(source),
          'native_code': inspect(native)}
report['normalization'] = ('Only directly owned prototype argument display reporters are excluded. '
                           'Modern Scratch rebuilds these from mutation metadata; all body '
                           'argument reporters, names, signatures and other opcodes remain compared.')
report['preserved'] = report['source_code'] == report['native_code']
report['passed'] = report['preserved'] and report['source_structure']['passed'] and report['native_structure']['passed']
output = Path(sys.argv[3] if len(sys.argv) > 3 else 'research/native_editor_structure.json')
output.write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'passed': report['passed'], 'preserved': report['preserved'],
                  'native_procedures': {k: v['definitions'] for k, v in report['native_code'].items()},
                  'report': str(output.resolve())}, indent=2))
raise SystemExit(not report['passed'])
