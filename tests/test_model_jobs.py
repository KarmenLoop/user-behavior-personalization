"""Real HTTP jobs with an injected provider: opt-in, replay and in-flight edits."""
import http.client
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from host import dispatch
from host_support import stamp
from workspace import make_server
import model_workflows


class ModelJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.args=SimpleNamespace(root=self.tmp.name,subject='alice',enable_conversations=True,
                                 enable_models=True,model='test-model',model_timeout=30,system_proxy=False,port=0)
        self.server=make_server(self.args)
        self.thread=threading.Thread(target=self.server.serve_forever,kwargs={'poll_interval':.01},daemon=True)
        self.thread.start()
        result=dispatch('conversation_import',{'expected_revision':0,'conversation':{'session_id':'s','context':'work','messages':[
            {'id':'m','role':'user','text':'In future drafts, put the decision first.','at':stamp()}]}},self.args)
        self.key=next(iter(result['profile']['conversation_messages']))
        self.body={'kind':'learn','request_id':'learn-one','expected_revision':1,'context':'work','source_keys':[self.key]}
        self.release=threading.Event()
        self.entered=threading.Event()
    def tearDown(self):
        self.release.set()
        self.server.shutdown();self.server.server_close();self.thread.join(3)
        self.tmp.cleanup()
    def request(self,method,path,body=None,token=True):
        conn=http.client.HTTPConnection('127.0.0.1',self.server.server_port,timeout=5)
        headers={'Content-Type':'application/json'}
        if token: headers['X-Workspace-Token']=self.server.token
        conn.request(method,path,json.dumps(body) if body is not None else None,headers)
        response=conn.getresponse();result=json.loads(response.read());status=response.status;conn.close()
        return status,result
    def wait_job(self,job='learn-one'):
        until=time.monotonic()+5
        while time.monotonic()<until:
            row=self.request('GET','/api/model-jobs/'+job)[1]
            if row['status']!='running': return row
            time.sleep(.01)
        self.fail('job did not finish within five seconds')
    def provider(self,*_a,**kw):
        self.entered.set()
        if not self.release.wait(4): raise RuntimeError('test provider timed out')
        kw['check_current']()
        return {'text':'{"proposals":[]}','metadata':{'requested_model':'test-model'}}

    def test_async_replay_busy_private_status_and_empty_abstention(self):
        with patch.object(model_workflows,'call_model',side_effect=self.provider) as provider:
            self.assertEqual(self.request('POST','/api/model-jobs',self.body)[0],202)
            self.assertTrue(self.entered.wait(3))
            self.assertEqual(self.request('POST','/api/model-jobs',self.body)[1]['job_id'],'learn-one')
            status,conflict=self.request('POST','/api/model-jobs',{**self.body,'context':'elsewhere'})
            self.assertEqual((status,conflict['code']),(400,'REQUEST_CONFLICT'))
            self.assertEqual(self.request('POST','/api/model-jobs',{**self.body,'request_id':'another'})[1]['code'],'MODEL_JOB_BUSY')
            pending=self.request('GET','/api/model-jobs/learn-one')[1]
            self.assertNotIn(self.key,str(pending));self.assertNotIn('decision',str(pending))
            self.release.set();done=self.wait_job()
        self.assertEqual(provider.call_count,1)
        self.assertEqual(done['status'],'completed');self.assertTrue(done['result']['abstained'])

    def test_pause_while_pending_discards_result_and_writes_are_responsive(self):
        with patch.object(model_workflows,'call_model',side_effect=self.provider):
            self.request('POST','/api/model-jobs',self.body)
            self.assertTrue(self.entered.wait(3))
            status,pause=self.request('POST','/api/call',{'name':'profile_pause','arguments':{'expected_revision':1,'paused':True}})
            self.assertEqual(status,200)
            self.assertEqual(set(pause['profile']),{'revision','paused'})
            self.release.set();done=self.wait_job()
        self.assertEqual((done['status'],done['error']['code']),('failed','MEMORY_PAUSED'))
        self.assertEqual(self.request('GET','/api/bootstrap')[1]['sources'],[])

    def test_opt_in_schema_subject_boundary_and_token_apply_to_both_routes(self):
        with patch.object(model_workflows,'call_model') as provider:
            for body in [{**self.body,'subject':'bob'},{**self.body,'source_keys':[]},
                         {**self.body,'request_id':'../x'},{**self.body,'expected_revision':True}]:
                self.assertEqual(self.request('POST','/api/model-jobs',body)[0],400)
            self.assertEqual(self.request('POST','/api/model-jobs',self.body,token=False)[0],403)
            self.assertEqual(self.request('GET','/api/model-jobs/learn-one',token=False)[0],403)
            self.args.enable_models=False
            self.assertEqual(self.request('POST','/api/model-jobs',self.body)[1]['code'],'MODELS_DISABLED')
            self.assertFalse(self.request('GET','/api/bootstrap')[1]['model_enabled'])
            self.args.enable_models=True
            self.assertEqual(self.request('POST','/api/model-jobs',{**self.body,'expected_revision':0})[0],409)
        provider.assert_not_called()

    def test_comparison_route_returns_only_identifier_and_live_read_is_blinded(self):
        dispatch('profile_correct',{'expected_revision':1,'rule':{'id':'r','statement':'Keep it concise.','scope':'work',
                 'source_id':'rule','source_summary':'Explicit request.','kind':'explicit'}},self.args)
        body={'kind':'compare','request_id':'compare-one','expected_revision':2,'context':'work','task':'Explain caching.',
              'task_conditions':{'stage':'draft'}}
        with patch.object(model_workflows,'call_model',return_value={'text':'synthetic protocol response','metadata':{'requested_model':'test-model'}}) as provider:
            self.assertEqual(self.request('POST','/api/model-jobs',body)[0],202)
            done=self.wait_job('compare-one')
        self.assertEqual(provider.call_count,2)
        self.assertEqual(done['status'],'completed')
        self.assertNotIn('synthetic protocol response',json.dumps(done))
        cid=done['result']['comparison_id']
        actual=self.request('POST','/api/call',{'name':'profile_comparison_read','arguments':{'comparison_id':cid}})[1]
        self.assertNotIn('mapping',actual)
        self.assertEqual(actual['answers']['a'],'synthetic protocol response')

    def test_enabled_server_requires_explicit_model(self):
        self.args.model=None
        from host_support import Problem
        with self.assertRaises(Problem): make_server(self.args)


if __name__=='__main__': unittest.main()
