#!/usr/bin/env python3
"""Focused tests for storage-ID repair; no renderer or builder modifications."""
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from repair_editor_ids import (repair_archive, repair_document, safe_storage_id)


def sprite_fixture():
    return {
        'name': 'Liquid Glass',
        'variables': {'v_connectionCache': ['cache', 123], 'safe': ['l_field', 'l_field']},
        'lists': {'l_field': ['field', [1, 2, 3]], 'l_keep': ['keep', ['l_field']]},
        'blocks': {
            'call': {'fields': {'LIST': ['field', 'l_field']},
                     'inputs': {'VALUE': [3, [13, 'field', 'l_field'], [10, 'l_field']]},
                     'mutation': {'proccode': 'label l_field'}},
            'var': {'fields': {'VARIABLE': ['cache', 'v_connectionCache']},
                    'inputs': {'VALUE': [3, [12, 'cache', 'v_connectionCache'], [10, '']] }},
            'listReporter': [13, 'field', 'l_field', 10, 20],
        },
        'comments': {'comment': {'text': 'l_field must remain literal here'}},
    }


class RepairTests(unittest.TestCase):
    def test_helper_is_stable_case_sensitive_and_leaves_safe_ids(self):
        for value in ['l_field', 'v_connectionCache', 'x_field_middle']:
            self.assertTrue(safe_storage_id(value).startswith('lgid'))
            self.assertEqual(safe_storage_id(safe_storage_id(value)), safe_storage_id(value))
        for value in ['l_pixelBand', 'Field', 'x_FIELD', 'safe']:
            self.assertEqual(safe_storage_id(value), value)

    def test_typed_references_only_and_full_inverse_equivalence(self):
        original = sprite_fixture()
        before = copy.deepcopy(original)
        fixed, mapping, counts = repair_document(original, 'sprite.json')
        self.assertEqual(original, before)
        self.assertEqual(counts, {'declarations': 2, 'blockFields': 2,
                                  'compactReporters': 3, 'monitors': 0})
        self.assertEqual(fixed['lists'][mapping['l_field']], ['field', [1, 2, 3]])
        self.assertEqual(fixed['variables']['safe'], ['l_field', 'l_field'])
        self.assertEqual(fixed['lists']['l_keep'], ['keep', ['l_field']])
        self.assertEqual(fixed['comments'], before['comments'])
        self.assertEqual(fixed['blocks']['call']['mutation'], before['blocks']['call']['mutation'])
        self.assertEqual(fixed['blocks']['call']['inputs']['VALUE'][2], [10, 'l_field'])

    def test_project_monitor_ids_follow_storage_ids(self):
        original = {'targets': [sprite_fixture()], 'monitors': [
            {'id': 'l_field', 'params': {'LIST': 'field'}, 'value': ['l_field']},
            {'id': 'safe', 'params': {'VARIABLE': 'l_field'}}]}
        fixed, mapping, counts = repair_document(original, 'project.json')
        self.assertEqual(counts['monitors'], 1)
        self.assertEqual(fixed['monitors'][0]['id'], mapping['l_field'])
        self.assertEqual(fixed['monitors'][0]['value'], ['l_field'])
        self.assertEqual(fixed['monitors'][1], original['monitors'][1])

    def test_destination_collision_is_rejected(self):
        original = sprite_fixture()
        original['lists'][safe_storage_id('l_field')] = ['existing', []]
        with self.assertRaisesRegex(ValueError, 'already exists'):
            repair_document(original, 'sprite.json')

    def test_sb3_and_sprite3_preserve_assets_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            for entry, suffix in [('project.json', 'sb3'), ('sprite.json', 'sprite3')]:
                source, output = Path(directory)/f'original.{suffix}', Path(directory)/f'fixed.{suffix}'
                data = sprite_fixture()
                if entry == 'project.json':
                    data = {'targets': [data], 'monitors': []}
                with zipfile.ZipFile(source, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                    archive.writestr(entry, json.dumps(data))
                    archive.writestr('asset.png', b'unchanged asset bytes')
                before = source.read_bytes()
                report = repair_archive(source, output)
                self.assertEqual(source.read_bytes(), before)
                self.assertTrue(report['inverseMappingRestoresEntireDocument'])
                self.assertTrue(report['allOtherArchiveEntriesIdentical'])
                with self.assertRaises(FileExistsError):
                    repair_archive(source, output)
                repair_archive(source, output, overwrite=True)

    def test_oversize_json_does_not_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory)/'large.sprite3', Path(directory)/'fixed.sprite3'
            data = sprite_fixture()
            data['large'] = 'x' * 5_000_000
            with zipfile.ZipFile(source, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr('sprite.json', json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'must be below'):
                repair_archive(source, output)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
