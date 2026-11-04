import json,unittest
from pathlib import Path
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/data/inventory.js').read_text()[len('window.CIVIC_DATA = '):].rstrip(';\n'))
class CrosswayTests(unittest.TestCase):
 def test_units_and_source_fragments_not_double_counted(self):
  c=D['crossways'];self.assertEqual(c['count'],37);self.assertEqual(c['siteCount'],18)
  self.assertEqual(len(c['records']),37)
  ids=[s for r in c['records'] for s in r['crossway']['sourceIds']]
  self.assertEqual(len(ids),len(set(ids)))
  self.assertNotIn('C-18-9266',ids);self.assertNotIn('C-A8-9138',ids)
  groups=[set(r['crossway']['sourceIds']) for r in c['records']]
  self.assertIn({'C-A8-11987','C-A8-11927'},groups)
  self.assertIn({'C-A8-13288','C-A8-13333'},groups)
 def test_missing_official_geometry_uses_sourced_reference_points(self):
  pts=[r for r in D['crossways']['records'] if r['geometry']['type']=='Point']
  self.assertEqual(len(pts),6)
  for r in pts:
   self.assertEqual(r['crossway']['count'],1)
   self.assertGreaterEqual(len(r['crossway']['observations']),2)
   self.assertIn('概略',r['crossway']['precision'])
   self.assertTrue(any('#page=' in s for s in r['verification']['sources']))
 def test_original_audit_and_geometry_remain_intact(self):
  by={r['id']:r for r in D['records']}
  self.assertEqual(len(by),385)
  self.assertEqual(sum(r['table']=='行穿線圖形' for r in by.values()),137)
  for r in D['crossways']['records']:
   self.assertNotIn(r['id'],by);self.assertTrue(r['segments']);self.assertTrue(r['verification']['sources'])
   ids=r['crossway']['sourceIds']
   if len(ids)==1:self.assertEqual(r['geometry'],by[ids[0]]['geometry'])
   if len(ids)>1:self.assertEqual(r['geometry']['geometries'],[by[s]['geometry'] for s in ids])
