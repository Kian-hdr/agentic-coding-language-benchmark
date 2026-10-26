import importlib.util,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from scripts.analyze import derive
from scripts.verify import equal
from lib.oracle import solve
class IntegrityTests(unittest.TestCase):
 def test_bool_is_not_integer(self):
  self.assertFalse(equal({'value':True},{'value':1}))
 def test_array_order_is_significant(self):
  self.assertFalse(equal([1,2],[2,1]))
 def test_nonfinite_is_rejected(self):
  self.assertFalse(equal(float('inf'),float('inf')))
 def test_fee_rounding_and_schema_isolation(self):
  req={'op':'invoice','events':[{'id':'a','customer':' aa ','amount_cents':50,'status':'paid'}]}
  self.assertNotIn('fee_cents',solve(req,True))
  req['fee_bps']=100
  self.assertEqual(solve(req,True)['fee_cents'],1)
  req['fee_bps']=0
  self.assertIn('fee_cents',solve(req,True))
  del req['fee_bps'];self.assertNotIn('fee_cents',solve(req,True))
 def test_invalid_first_id_still_deduplicates(self):
  req={'op':'invoice','events':[{'id':'x','customer':'a','amount_cents':-1,'status':'paid'},{'id':'x','customer':'a','amount_cents':10,'status':'paid'}]}
  got=solve(req);self.assertEqual((got['rejected'],got['duplicates'],got['accepted']),(1,1,0))
 def test_signed_integer_telemetry(self):
  self.assertEqual(solve({'op':'telemetry','samples':[-5,-4],'window':2,'threshold':0})['min'],-4)
 def test_eligibility_and_resource_exclusions(self):
  rows=derive()['long'];by={(r['language'],r['workload']):r for r in rows}
  self.assertTrue(all(by['zero',k]['resource_n']==0 for k in ['invoice','access_log','telemetry']))
  self.assertEqual(by['baml','invoice']['resource_n'],1)
  self.assertEqual(by['kotlin','telemetry']['resource_n'],1)
  self.assertEqual(sum(r['resource_n'] for r in rows),46)
if __name__=='__main__':unittest.main()
