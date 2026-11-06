#!/usr/bin/env python3
"""Repair reserved Blockly storage IDs without changing Scratch programs/data.

The modern editor uses storage IDs for palette reporter block IDs. Blockly
reserves `_field` and `_connection` inside those IDs for its focus machinery.
This utility changes only storage declarations and their typed references.
"""
import argparse
import copy
import hashlib
import io
import json
from pathlib import Path
import zipfile

RESERVED_ID_MARKERS = ('_field', '_connection')
JSON_BYTE_LIMIT = 5_000_000


def safe_storage_id(identifier):
    """Return a stable opaque replacement only when an ID uses a reserved marker."""
    if any(marker in identifier for marker in RESERVED_ID_MARKERS):
        return 'lgid' + hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:24]
    return identifier


def targets_of(document, entry):
    return document['targets'] if entry == 'project.json' else [document]


def remap_storage(document, entry, mapping):
    """Mutate typed ID positions only; return counts of changed references."""
    counts = {'declarations': 0, 'blockFields': 0,
              'compactReporters': 0, 'monitors': 0}

    def compact(value):
        if not isinstance(value, list):
            return
        if (len(value) >= 3 and value[0] in (12, 13)
                and isinstance(value[2], str) and value[2] in mapping):
            value[2] = mapping[value[2]]
            counts['compactReporters'] += 1
            return
        for child in value:
            compact(child)

    for target in targets_of(document, entry):
        for category in ('variables', 'lists'):
            original = target.get(category, {})
            replacement = {}
            for identifier, value in original.items():
                replacement[mapping.get(identifier, identifier)] = value
                counts['declarations'] += int(identifier in mapping)
            if category in target:
                target[category] = replacement
        for block in target.get('blocks', {}).values():
            if isinstance(block, list):
                compact(block)
                continue
            for kind in ('VARIABLE', 'LIST'):
                field = block.get('fields', {}).get(kind)
                if (isinstance(field, list) and len(field) >= 2
                        and field[1] in mapping):
                    field[1] = mapping[field[1]]
                    counts['blockFields'] += 1
            for value in block.get('inputs', {}).values():
                compact(value)
    for monitor in document.get('monitors', []):
        if monitor.get('id') in mapping:
            monitor['id'] = mapping[monitor['id']]
            counts['monitors'] += 1
    return counts


def repair_document(document, entry):
    declarations = {
        identifier
        for target in targets_of(document, entry)
        for category in ('variables', 'lists')
        for identifier in target.get(category, {})
    }
    mapping = {identifier: safe_storage_id(identifier)
               for identifier in sorted(declarations)
               if safe_storage_id(identifier) != identifier}
    # Never merge an existing storage object or ambiguously invert a mapping.
    if len(set(mapping.values())) != len(mapping):
        raise ValueError('Replacement storage IDs collide with each other')
    if set(mapping.values()) & declarations:
        raise ValueError('Replacement storage ID already exists')
    repaired = copy.deepcopy(document)
    counts = remap_storage(repaired, entry, mapping)
    restored = copy.deepcopy(repaired)
    inverse_counts = remap_storage(restored, entry,
                                   {new: old for old, new in mapping.items()})
    if restored != document or inverse_counts != counts:
        raise ValueError('Inverse mapping did not restore the complete input document')
    return repaired, mapping, counts


def repair_archive(source, output, *, overwrite=False):
    source, output = Path(source), Path(output)
    if output.exists() and not overwrite:
        raise FileExistsError(f'Refusing to overwrite {output}; use --overwrite explicitly')
    source_bytes = source.read_bytes()
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError('Archive contains duplicate entry names')
        entries = [name for name in ('project.json', 'sprite.json') if name in names]
        if len(entries) != 1:
            raise ValueError('Expected exactly one project.json or sprite.json')
        entry = entries[0]
        original_json = archive.read(entry)
        original = json.loads(original_json)
        repaired, mapping, counts = repair_document(original, entry)
        encoded = json.dumps(repaired, ensure_ascii=False,
                             separators=(',', ':'), allow_nan=False).encode('utf-8')
        if len(encoded) >= JSON_BYTE_LIMIT:
            raise ValueError(f'{entry} is {len(encoded):,} bytes; must be below {JSON_BYTE_LIMIT:,}')
        result_bytes = io.BytesIO()
        with zipfile.ZipFile(result_bytes, 'w') as destination:
            destination.comment = archive.comment
            for info in archive.infolist():
                destination.writestr(info, encoded if info.filename == entry
                                     else archive.read(info.filename))
        payload = result_bytes.getvalue()
        with zipfile.ZipFile(io.BytesIO(payload)) as check:
            if check.testzip() is not None:
                raise ValueError('Output archive CRC check failed')
            if check.namelist() != names:
                raise ValueError('Output archive entries changed')
            if any(check.read(name) != archive.read(name)
                   for name in names if name != entry):
                raise ValueError('A non-JSON archive entry changed')
            if json.loads(check.read(entry)) != repaired:
                raise ValueError('Output JSON verification failed')
    # Build and verify in memory before touching the requested destination.
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('wb' if overwrite else 'xb') as destination:
        destination.write(payload)
    return {
        'source': str(source.resolve()), 'output': str(output.resolve()),
        'sourceSHA256': hashlib.sha256(source_bytes).hexdigest(),
        'outputSHA256': hashlib.sha256(payload).hexdigest(),
        'jsonEntry': entry, 'jsonBytesBefore': len(original_json),
        'jsonBytesAfter': len(encoded), 'mapping': mapping, 'counts': counts,
        'inverseMappingRestoresEntireDocument': True,
        'allOtherArchiveEntriesIdentical': True,
        'underFiveMillionBytes': True,
        'sourcePreserved': source.read_bytes() == source_bytes,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    report = repair_archive(args.source, args.output, overwrite=args.overwrite)
    text = json.dumps(report, indent=2) + '\n'
    if args.report:
        if args.report.resolve() in (args.source.resolve(), args.output.resolve()):
            raise ValueError('Report path must differ from both archive paths')
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(text)
    print(text, end='')


if __name__ == '__main__':
    main()
