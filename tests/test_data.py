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
  self.assertEqual(len(r),734);self.assertTrue(set(source).issubset(r));self.assertEqual(len(source),710)
  for key, original in source.items(): self.assertEqual(r[key]['original'],original)
 def test_six_categories_and_indexes(self):
  self.assertEqual(len(d['categories']),6)
  self.assertEqual(sum(x['isIndex'] for x in r.values()),76)
  self.assertEqual(sum(d['meta']['categoryCounts'].values()),658)
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
   if x['table']=='歷史圖說設備' and not x.get('access'):self.assertTrue(x['historical'] and x['pending']);self.assertIsNone(x['geometry'])
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
 def test_image_review_preserves_original_geometry_and_counts(self):
  self.assertEqual(d['meta']['imageReviewCount'],2)
  group=r['G-017'];self.assertTrue(group['isIndex'])
  self.assertEqual(group['review']['originalEditDate'],'2023-06-21')
  self.assertEqual([x['imageDate'] for x in group['review']['references']],['2025-05','2024-09'])
  self.assertEqual(set(group['review']['recordIds']),{'G-017','C-08-7698','C-A8-7707'})
  for rid in ['C-08-7698','C-A8-7707']:
   self.assertEqual(r[rid]['geometry'],s['crossGeoms'][rid])
   self.assertTrue(r[rid]['pending'])
  self.assertEqual(sum(d['meta']['categoryCounts'].values()),658)
 def test_pedestrian_entrance_evidence_and_no_fake_coordinates(self):
  access=[x for x in r.values() if x.get('access')]
  self.assertEqual(len(access),28)
  self.assertEqual(sum(x['access']['groundDocumented'] for x in access),23)
  source_access=json.loads((ROOT/'source/pedestrian-access.json').read_text())['items']
  self.assertEqual(d['meta']['accessImageReviewCount'],sum(bool(x['groundReview']) for x in source_access))
  for x in access:
   g=x['access']['groundReview']
   if g:
    self.assertIn(g['imageDate'],x.get('currentSource',x['original'])['確認程度'])
    self.assertRegex(g['imageDate'],r'^20\d\d-\d\d$')
    self.assertIn('pano=',g['url'])
  for x in access:
   self.assertIsNone(x['geometry']);self.assertTrue(x['pending']);self.assertFalse(x['historical'])
   self.assertEqual(x['category'],'crossing');self.assertIn(x['parent'],r)
   self.assertGreater(x['access']['document']['page'],0)
  a=r['PA-TPE0110-3'];self.assertEqual(a['parent'],'P-TPE0110')
  self.assertEqual(a['access']['groundReview']['imageDate'],'2024-09')
  self.assertIn('G-017',a['access']['related'])
 def test_historical_stairs_keep_ids_and_source_history(self):
  for i in range(1,5):
   x=r[f'H-FD-{i:02}'];self.assertIn('currentSource',x)
   self.assertEqual(x['access']['document']['page'],14)
  self.assertFalse(any(x['id'].startswith('PA-TPE0155') for x in r.values()))
 def test_access_audits_do_not_claim_completion(self):
  self.assertEqual(len(d['accessAudit']),10)
  for a in d['accessAudit']:
   self.assertFalse(a['complete']);self.assertEqual(a['locatedCount'],0)
   self.assertTrue(all(r[i]['parent']==a['parent'] for i in a['recordIds']))
   self.assertEqual(a['groundImageReviewed'],sum(bool(r[i]['access']['groundReview']) for i in a['recordIds']))
 def test_cross_segment_system_not_duplicated(self):
  self.assertEqual(r['X-YMALL']['segments'],['S0','S1']);self.assertIsNone(r['X-YMALL']['geometry'])
  self.assertEqual(r['X-C076']['geometry']['type'],'MultiLineString')
if __name__=='__main__':unittest.main(verbosity=2)
