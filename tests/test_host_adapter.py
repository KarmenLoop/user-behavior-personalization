import json,subprocess,sys,tempfile,unittest,time,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/'scripts/host.py'
class HostTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name);self.workspace=self.base/'workspace';self.workspace.mkdir();self.data=self.base/'private'
 def tearDown(self):self.tmp.cleanup()
 def argv(self,host='codex',subject=None):return [sys.executable,str(SCRIPT),'--root',str(self.data),'--workspace',str(self.workspace),'--host-id',host]+(['--subject',subject] if subject else [])
 def call(self,name,value,host='codex',subject=None,code=0):
  p=subprocess.run(self.argv(host,subject)+['call',name],input=json.dumps(value),text=True,capture_output=True,timeout=80)
  self.assertEqual(p.returncode,code,p.stdout+p.stderr);return json.loads(p.stdout if code==0 else p.stderr)

 def test_correction_isolation_pause_delete_and_replay(self):
  rule={'id':'units','statement':'Use metric units.','scope':'engineering','source_id':'explicit-1','source_summary':'The user requested metric units.','kind':'explicit'}
  self.call('profile_correct',{'expected_revision':0,'rule':rule},subject='alice')
  self.assertEqual(self.call('profile_read',{'context':'engineering'},subject='bob')['rules'],[])
  self.assertEqual(self.call('profile_read',{'context':'writing'},subject='alice')['rules'],[])
  self.assertEqual(self.call('profile_correct',{'expected_revision':0,'rule':rule},subject='alice',code=2)['code'],'STALE_REVISION')
  corrected={**rule,'statement':'Use millimeters.','source_id':'correction-2','kind':'correction'};self.call('profile_correct',{'expected_revision':1,'rule':corrected},subject='alice')
  self.call('profile_pause',{'expected_revision':2,'paused':True},subject='alice');self.assertEqual(self.call('profile_read',{'context':'engineering'},subject='alice')['rules'],[])
  export=self.call('profile_export',{},subject='alice');self.assertTrue(Path(export['path']).is_file())
  self.call('profile_forget',{'expected_revision':3,'rule_id':'units'},subject='alice');self.assertFalse(Path(export['path']).exists())
  self.call('profile_pause',{'expected_revision':4,'paused':False},subject='alice');self.assertEqual(self.call('profile_correct',{'expected_revision':5,'rule':rule},subject='alice',code=2)['code'],'SOURCE_FORGOTTEN')
  self.assertEqual(self.call('profile_export',{},subject='alice')['profile']['history'],[])

if __name__=='__main__':unittest.main()
