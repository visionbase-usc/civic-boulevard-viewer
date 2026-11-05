import csv,json,unittest
from collections import Counter
from pathlib import Path
R=Path(__file__).resolve().parents[1]
D=json.loads((R/'docs/data/inventory.js').read_text()[len('window.CIVIC_DATA = '):].rstrip(';\n'))
class CrosswayTests(unittest.TestCase):
 def test_units_and_source_fragments_not_double_counted(self):
  c=D['crossways'];self.assertEqual(c['count'],39);self.assertEqual(c['siteCount'],18)
  self.assertEqual(len(c['records']),39)
  self.assertEqual(len({r['id'] for r in c['records']}),39)
  ids=[s for r in c['records'] for s in r['crossway']['sourceIds']]
  duplicates={s:n for s,n in Counter(ids).items() if n>1}
  self.assertEqual(duplicates,{'C-A8-7702':2,'C-A8-11935':2})
  for sid in duplicates:
   parts=[r for r in c['records'] if sid in r['crossway']['sourceIds']]
   self.assertEqual({r['crossway']['splitPart'] for r in parts},{'北側車道','南側車道'})
   self.assertNotEqual(parts[0]['geometry'],parts[1]['geometry'])
   self.assertEqual(parts[0]['crossway']['sourceGeometry'],parts[1]['crossway']['sourceGeometry'])
  self.assertNotIn('C-18-9266',ids);self.assertNotIn('C-A8-9138',ids)
  groups=[set(r['crossway']['sourceIds']) for r in c['records']]
  self.assertIn({'C-A8-11987','C-A8-11927'},groups)
  self.assertIn({'C-A8-13288','C-A8-13333'},groups)
 def test_points_preserve_limits_and_source_provenance(self):
  pts=[r for r in D['crossways']['records'] if r['geometry']['type']=='Point']
  self.assertEqual(len(pts),12)
  for r in pts:
   self.assertEqual(r['crossway']['count'],1)
   self.assertGreaterEqual(len(r['crossway']['observations']),2)
   self.assertIn('概略',r['crossway']['precision'])
   self.assertIn('誤差',r['crossway']['positionLimitations'])
   if not r['crossway']['sourceIds']:
    self.assertTrue(any('#page=' in s for s in r['verification']['sources']))
 def test_all_sites_reviewed_and_counts_reconciled(self):
  review=D['crosswayReview'];self.assertEqual(len(review['sites']),29)
  counts=Counter(r['crossway']['site'] for r in D['crossways']['records'])
  self.assertEqual(sum(s['confirmedCount'] for s in review['sites']),review['verifiedTotal'])
  self.assertEqual(review['verifiedTotal'],D['crossways']['count'])
  self.assertEqual(sum(s['confirmedCount']==0 for s in review['sites']),11)
  for s in review['sites']:
   self.assertEqual(s['status'],'ground-reviewed');self.assertEqual(s['confirmedCount'],counts[s['groupId']])
   self.assertTrue(s['observations']);self.assertTrue(s['finding'])
   for o in s['observations']:self.assertRegex(o['date'],r'^20\d\d-\d\d$');self.assertIn('pano=',o['url'])
  for r in D['crossways']['records']:
   self.assertTrue(r['crossway']['observations']);self.assertEqual(r['original']['查核日期'],'2026-11-05')
  with (R/'docs/data/crossways.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
  self.assertEqual(len(rows),39);self.assertTrue(all(r['幾何'] and r['影像日期'] for r in rows))
  with (R/'docs/data/crossway-site-review.csv').open(encoding='utf-8-sig') as f: self.assertEqual(len(list(csv.DictReader(f))),29)
 def test_original_audit_and_geometry_remain_intact(self):
  by={r['id']:r for r in D['records']}
  self.assertEqual(len(by),385)
  self.assertEqual(sum(r['table']=='行穿線圖形' for r in by.values()),137)
  for r in D['crossways']['records']:
   self.assertNotIn(r['id'],by);self.assertTrue(r['segments']);self.assertTrue(r['verification']['sources'])
   ids=r['crossway']['sourceIds'];geom=r['crossway'].get('sourceGeometry',r['geometry'])
   if len(ids)==1:self.assertEqual(geom,by[ids[0]]['geometry'])
   if len(ids)>1:self.assertEqual(geom['geometries'],[by[s]['geometry'] for s in ids])
