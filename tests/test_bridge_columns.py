import json
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from bridge_columns import load_columns

class BridgeColumnTests(unittest.TestCase):
    def setUp(self):
        self.data=load_columns(ROOT)
    def test_same_mark_on_opposite_rows_remains_two_physical_columns(self):
        for mark in ('P140','P143'):
            rows=[r for r in self.data['records'] if r['bridgeColumn']['observedMark']==mark]
            self.assertEqual(len(rows),2)
            self.assertEqual({r['bridgeColumn']['side'] for r in rows},{'north','south'})
            self.assertEqual(len({r['id'] for r in rows}),2)
    def test_no_camera_position_becomes_a_column_position(self):
        self.assertIsNone(self.data['verifiedWholeScopeTotal'])
        for r in self.data['records']:
            self.assertIsNone(r['geometry'])
            self.assertNotIn('access',r)
            self.assertTrue(r['pending'])
            self.assertIn('pano=',r['original']['來源連結'])
    def test_counts_distinguish_marks_and_physical_objects(self):
        rows=self.data['records']
        self.assertEqual(self.data['physicalColumnsObserved'],len(rows))
        self.assertGreater(self.data['numberedPhysicalColumnsObserved'],self.data['readableDistinctMarks'])
        self.assertTrue(any(r['bridgeColumn']['observedMark'] is None for r in rows))
        for s in self.data['sections']:
            self.assertEqual(s['physicalColumnCount'],len(set(s['records'])))
            self.assertTrue(set(s['records']) <= {r['id'] for r in rows})
    def test_published_bundle_preserves_unlocated_records(self):
        raw=(ROOT/'docs/data/inventory.js').read_text()
        pack=json.loads(raw.removeprefix('window.CIVIC_DATA = ').strip().removesuffix(';'))
        self.assertEqual(pack['bridgeColumns'],self.data)
        self.assertTrue(all(r['category']=='bridge' for r in pack['bridgeColumns']['records']))

if __name__=='__main__': unittest.main()
