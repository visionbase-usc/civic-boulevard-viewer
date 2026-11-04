import json, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'docs/data/inventory.js').read_text().split(' = ',1)[1].rstrip(';\n'))
class FollowupTests(unittest.TestCase):
 def test_baseline_and_positions_are_reconciled(self):
  f=D['followup'];rs={r['id']:r for r in D['records']}
  self.assertEqual(f['baselineCount'],77)
  self.assertEqual(len({r['id'] for r in f['records']}),77)
  located=[r for r in f['records'] if r['resultPosition']]
  self.assertEqual(len(located),f['locatedCount'])
  self.assertEqual(f['remainingCount'],77-len(located))
  for r in located:
   self.assertEqual(r['resultPosition'],rs[r['id']]['geometry'])
   self.assertIn('positionReview',rs[r['id']])
  self.assertEqual(sum(not r['geometry'] for r in D['records']),f['remainingCount'])
 def test_conflicting_park_coordinate_is_preserved_not_adopted(self):
  p=next(r for r in D['records'] if r['id']=='F-PARK-CL')['positionReview']
  src=json.loads((ROOT/'source/parks-position-evidence.json').read_text())['row']
  raw=[float(src['pm_Longitude']),float(src['pm_Latitude'])]
  self.assertNotEqual(p['geometry']['coordinates'],raw)
  self.assertEqual(p['originalOfficialPosition'],raw)
  self.assertEqual(p['quality'],'approximate-image-intersection')
  self.assertEqual(len(p['rays']),2)
  self.assertIn('不是公園邊界',p['limitations'])
 def test_charging_source_checks_keep_unlocated(self):
  rs={r['id']:r for r in D['records']}
  for f in D['followup']['records']:
   if 'ChargingStation' not in f['id']:continue
   self.assertIsNone(rs[f['id']]['geometry'])
   self.assertIn('沒有逐支充電設備座標',f['observed'])
   self.assertEqual(f['status'],'source-reviewed-no-individual-coordinate')
