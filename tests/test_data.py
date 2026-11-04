"""Source/transform integrity checks; no third-party packages required."""
import json, unittest, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
raw=(ROOT/'docs/data/inventory.js').read_text()
d=json.loads(raw[len('window.CIVIC_DATA = '):].rstrip(';\n'))
s=json.loads((ROOT/'source/inventory.json').read_text())
r={v['id']:v for v in d['records']}
class InventoryTests(unittest.TestCase):
 def test_preserves_in_scope_original_rows(self):
  source={x['編號']:x for k,rows in s['datasets'].items() if k not in ['路段範圍','補件清單'] for x in rows}
  self.assertEqual(len(r),370);self.assertEqual(len(source),710)
  for key in set(source)&set(r): self.assertEqual(r[key]['original'],source[key])
 def test_six_categories_and_indexes(self):
  self.assertEqual(len(d['categories']),6)
  self.assertEqual(sum(x['isIndex'] for x in r.values()),29)
  self.assertEqual(sum(d['meta']['categoryCounts'].values()),341)
  self.assertEqual(len([x for x in r.values() if x['table']=='行穿線圖形']),137)
  members=[child for x in r.values() if x['isIndex'] for child in x['members']]
  self.assertEqual(len(members),137);self.assertEqual(len(set(members)),137)
 def test_missing_coordinates_not_invented(self):
  for x in r.values():
   if x['original']['經度'] is None:self.assertIsNone(x['geometry'],x['id'])
 def test_relationships_and_history(self):
  for x in r.values():
   if x['parent']:self.assertIn(x['parent'],r)
   if x['group']:self.assertIn(x['group'],r)
   if x['table']=='歷史圖說設備' and not x.get('access'):
    self.assertFalse(x['historical']);self.assertTrue(x['pending']);self.assertIsNone(x['geometry'])
    self.assertIn('2026-10-05',x['verification']['sourceDate'])
  stairs=[x for x in r.values() if x['subtype']=='地下樓梯（非地面口）']
  self.assertEqual(len(stairs),3)
 def test_demo_source_coordinates(self):
  for key in ['P-TPE0155','P-TPE0263','P-TPE0057','P-TPE1598']:
   self.assertEqual(r[key]['geometry']['coordinates'],[r[key]['original']['經度'],r[key]['original']['緯度']])
   children=[x for x in r.values() if x['parent']==key and x['table']=='車輛入口'];self.assertEqual(len(children),1)
 def test_all_segments_and_elevated(self):
  self.assertEqual([x['id'] for x in d['segments']],['S2','S3','S4'])
  self.assertEqual(len(d['elevated']),9)
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
  self.assertEqual(sum(d['meta']['categoryCounts'].values()),341)
 def test_pedestrian_entrance_evidence_and_no_fake_coordinates(self):
  access=[x for x in r.values() if x.get('access')]
  self.assertEqual(len(access),23)
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
  self.assertEqual(len(d['accessAudit']),7)
  for a in d['accessAudit']:
   self.assertFalse(a['complete']);self.assertEqual(a['locatedCount'],0)
   self.assertTrue(all(r[i]['parent']==a['parent'] for i in a['recordIds']))
   self.assertEqual(a['groundImageReviewed'],sum(bool(r[i]['access']['groundReview']) for i in a['recordIds']))
 def test_study_scope_excludes_outside_and_preserves_boundary_groups(self):
  self.assertNotIn('X-YMALL',r);self.assertNotIn('X-C076',r)
  for x in r.values():
   self.assertTrue(x['segments']);self.assertTrue(set(x['segments'])<=set(['S2','S3','S4']))
   if not set(re.findall(r'S[234]',x['original'].get('分段',''))):self.assertIn('scopeNote',x)
  for rid in ['C-A8-7732','C-A8-13289']:
   self.assertEqual(r[rid]['geometry'],s['crossGeoms'][rid]);self.assertIn('scopeNote',r[rid])
  for w in d['roads']:self.assertIn(w['seg'],['S2','S3','S4'])
  for w in d['elevated']:
   for p in w['coords']:self.assertTrue(d['scope']['west']-1e-10<=p[0]<=d['scope']['east']+1e-10)
  self.assertIsNone(r['E-TPE1871-01']['geometry']);self.assertTrue(r['E-TPE1871-01']['pending'])
  self.assertEqual(r['E-TPE1871-01']['original']['經度'],0)
  self.assertIsNone(r['E-TPE1871-01']['currentSource']['經度'])
 def test_every_record_has_field_level_audit(self):
  self.assertEqual(d['audit']['recordCount'],len(r))
  self.assertEqual(d['audit']['issueCount'],12)
  for x in r.values():
   a=x['verification'];self.assertEqual(a['id'],x['id']);self.assertTrue(a['checks']);self.assertTrue(a['sources'])
   self.assertTrue(all(c['result']=='match' for c in a['checks']),x['id'])
   self.assertNotEqual(a['result'],'unresolved')
  self.assertEqual(d['audit']['summary'],{'official':252,'official-with-issue':8,'index':29,'document':77,'document-with-issue':4})
 def test_source_exceptions_are_visible_without_changing_original(self):
  for key in ['B-1222','B-1501','B-1001120']:
   self.assertTrue(r[key]['pending']);self.assertTrue(r[key]['verification']['issues'])
   self.assertIn('疑有誤',r[key]['currentSource']['地址或鄰近路口'])
   self.assertNotEqual(r[key]['currentSource']['地址或鄰近路口'],r[key]['original']['地址或鄰近路口'])
  self.assertFalse(r['C-A8-7732']['pending'])
  self.assertTrue(r['C-08-7698']['pending'])
 def test_official_supplemental_equipment(self):
  supplements=[x for x in r.values() if x['table']=='官方圖說補充設備']
  self.assertEqual(len(supplements),35)
  for x in supplements:
   self.assertIsNone(x['geometry']);self.assertIn(x['parent'],r)
   self.assertEqual(x['verification']['result'],'document')
   self.assertIn('#page=',x['original']['來源連結'])
 def test_audit_csv_has_every_id_once(self):
  import csv
  with (ROOT/'docs/data/record-audit.csv').open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
  self.assertEqual(len(rows),len(r));self.assertEqual(set(x['編號'] for x in rows),set(r))
 def test_sports_official_positions_counts_and_unknowns(self):
  proof=json.loads((ROOT/'source/sports-sources.json').read_text())
  for key in ['261','262']:
   x=r['F-SPORT-VBS'+key];lat,lon=map(float,proof['venues'][key]['LatLon'].split(','))
   self.assertEqual(x['geometry']['coordinates'],[lon,lat]);self.assertEqual(x['category'],'public')
   self.assertTrue(x['verification']['issues'])
  self.assertIn('2面',r['F-SPORT-VBS261']['original']['場地數量'])
  for key in ['F-SPORT-VBS1115','F-SPORT-HUASHAN-BASKET','F-SPACE-HUASHAN-RINK']:
   self.assertIsNone(r[key]['geometry']);self.assertTrue(r[key]['pending'])
  self.assertIn('安東街40巷',r['F-SPORT-VBS1115']['original']['地址或鄰近路口'])
  self.assertNotIn('南京東路',r['F-SPORT-VBS1115']['original']['地址或鄰近路口'])
  self.assertIn('待核',r['F-SPACE-HUASHAN-RINK']['original']['使用性質'])
  self.assertEqual(sum(x['table']=='官方運動與活動場地' for x in r.values()),5)
if __name__=='__main__':unittest.main(verbosity=2)
