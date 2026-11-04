"""Source/transform integrity checks; no third-party packages required."""
import json, unittest, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
raw=(ROOT/'docs/data/inventory.js').read_text()
d=json.loads(raw[len('window.CIVIC_DATA = '):].rstrip(';\n'))
s=json.loads((ROOT/'source/inventory.json').read_text())
r={v['id']:v for v in d['records']}
class InventoryTests(unittest.TestCase):
 def test_preserves_all_source_rows(self):
  source={x['編號']:x for k,rows in s['datasets'].items() if k not in ['路段範圍','補件清單'] for x in rows}
  self.assertEqual(len(r),710);self.assertEqual(set(r),set(source))
  for key, original in source.items(): self.assertEqual(r[key]['original'],original)
 def test_six_categories_and_indexes(self):
  self.assertEqual(len(d['categories']),6)
  self.assertEqual(sum(x['isIndex'] for x in r.values()),76)
  self.assertEqual(sum(d['meta']['categoryCounts'].values()),634)
  self.assertEqual(len([x for x in r.values() if x['table']=='行穿線圖形']),319)
  members=[child for x in r.values() if x['isIndex'] for child in x['members']]
  self.assertEqual(len(members),319);self.assertEqual(len(set(members)),319)
 def test_missing_coordinates_not_invented(self):
  for x in r.values():
   if x['original']['經度'] is None:self.assertIsNone(x['geometry'],x['id'])
 def test_relationships_and_history(self):
  for x in r.values():
   if x['parent']:self.assertIn(x['parent'],r)
   if x['group']:self.assertIn(x['group'],r)
   if x['table']=='歷史圖說設備':self.assertTrue(x['historical'] and x['pending']);self.assertIsNone(x['geometry'])
  stairs=[x for x in r.values() if x['subtype']=='地下樓梯（非地面口）']
  self.assertEqual(len(stairs),3)
 def test_demo_source_coordinates(self):
  for key in ['P-TPE0155','P-TPE0263','P-TPE0057','P-TPE1598']:
   self.assertEqual(r[key]['geometry']['coordinates'],[r[key]['original']['經度'],r[key]['original']['緯度']])
   children=[x for x in r.values() if x['parent']==key and x['table']=='車輛入口'];self.assertEqual(len(children),1)
 def test_all_segments_and_elevated(self):
  self.assertEqual([x['id'] for x in d['segments']],[f'S{i}' for i in range(9)])
  self.assertEqual(len(d['elevated']),30)
  for seg in d['segments']:
   self.assertLess(seg['bounds'][0][0],seg['bounds'][1][0]);self.assertLess(seg['bounds'][0][1],seg['bounds'][1][1])
 def test_sources_are_public_http(self):
  for x in r.values():self.assertRegex(x['original']['來源連結'],r'^https://')
 def test_cross_segment_system_not_duplicated(self):
  self.assertEqual(r['X-YMALL']['segments'],['S0','S1']);self.assertIsNone(r['X-YMALL']['geometry'])
  self.assertEqual(r['X-C076']['geometry']['type'],'MultiLineString')
if __name__=='__main__':unittest.main(verbosity=2)
