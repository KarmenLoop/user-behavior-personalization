"""Actual loopback HTTP requests across the workspace's storage boundary."""
import datetime as dt
import http.client
import json
from pathlib import Path
import re
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from workspace import make_server, MAX_BODY


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.args = SimpleNamespace(root=Path(self.tmp.name)/'private', subject='alice',
                                    enable_conversations=True, enable_observations=False,
                                    workspace=str(ROOT), host_id='workspace-test', port=0)
        self.server = make_server(self.args)
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={'poll_interval':.01}, daemon=True)
        self.thread.start()
        self.host = '127.0.0.1:' + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.tmp.cleanup()

    def request(self, method='GET', path='/api/bootstrap', value=None, headers=None, token=True):
        connection = http.client.HTTPConnection('127.0.0.1', self.server.server_port, timeout=8)
        outgoing = {'Host':self.host}
        if token:
            outgoing['X-Workspace-Token'] = self.server.token
        if value is not None:
            outgoing['Content-Type'] = 'application/json'
        outgoing.update(headers or {})
        body = json.dumps(value).encode() if value is not None else None
        connection.request(method, path, body=body, headers=outgoing)
        response = connection.getresponse()
        raw = response.read()
        result = json.loads(raw) if response.getheader('Content-Type','').startswith('application/json') else raw.decode()
        status, returned_headers = response.status, dict(response.getheaders())
        connection.close()
        return status, result, returned_headers

    def tool(self, name, arguments):
        return self.request('POST','/api/call',{'name':name,'arguments':arguments})

    def revision(self):
        return self.request()[1]['revision']

    def conversation(self, text='I prefer concise explanations.'):
        return {'session_id':'web-1','context':'writing','messages':[
            {'id':'m1','role':'user','text':text,'at':dt.datetime.now(dt.timezone.utc).isoformat()}]}

    def test_html_assets_and_token_use_local_origin_without_cache(self):
        status, html, headers = self.request(path='/',token=False)
        self.assertEqual(status,200)
        self.assertIn(self.server.token,html)
        self.assertIn('name="workspace-token"',html)
        self.assertEqual(headers['Cache-Control'],'no-store')
        self.assertIn("frame-ancestors 'none'",headers['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin',headers)
        for name in ('app.js','style.css'):
            self.assertEqual(self.request(path='/'+name,token=False)[0],200)
        script = self.request(path='/app.js',token=False)[1]
        self.assertNotIn('innerHTML',script)
        self.assertNotIn('insertAdjacentHTML',script)

    def test_api_reads_and_writes_require_token(self):
        for method,path,value in [('GET','/api/bootstrap',None),('POST','/api/call',{'name':'profile_pause','arguments':{'expected_revision':0,'paused':True}})]:
            status, result, _ = self.request(method,path,value,token=False)
            self.assertEqual((status,result['code']),(403,'TOKEN_REQUIRED'))
        self.assertEqual(self.revision(),0)

    def test_invalid_host_origin_and_fetch_site_cannot_read_or_write(self):
        value={'name':'profile_pause','arguments':{'expected_revision':0,'paused':True}}
        for headers in [{'Host':'attacker.invalid'},{'Host':'127.0.0.1'},{'Origin':'https://attacker.invalid'},
                        {'Origin':'null'},{'Origin':'http://localhost:'+str(self.server.server_port)},
                        {'Sec-Fetch-Site':'cross-site'},{'Sec-Fetch-Site':'same-site'}]:
            with self.subTest(headers=headers):
                self.assertEqual(self.request(headers=headers)[0],403)
                self.assertEqual(self.request('POST','/api/call',value,headers)[0],403)
        self.assertEqual(self.revision(),0)

    def test_same_origin_accepted_and_arbitrary_paths_tools_subject_rejected(self):
        self.assertEqual(self.request(headers={'Origin':'http://'+self.host,'Sec-Fetch-Site':'same-origin'})[0],200)
        for path in ['/../scripts/host.py','/%2e%2e/scripts/host.py','/api/bootstrap?subject=bob','/web/app.js','/api/nope']:
            self.assertEqual(self.request(path=path)[0],404)
        self.assertEqual(self.tool('profile_export',{})[0],403)
        self.assertEqual(self.tool('shell',{'command':'anything'})[0],403)
        status,result,_ = self.tool('profile_read',{'context':'writing','subject':'bob'})
        self.assertEqual((status,result['code']),(400,'INVALID_INPUT'))
        self.assertEqual(self.revision(),0)

    def test_actual_import_review_pause_and_delete_through_http(self):
        conversation=self.conversation()
        self.assertEqual(self.tool('conversation_import',{'expected_revision':0,'conversation':conversation})[0],200)
        portrait=self.tool('profile_portrait',{'context':'writing'})[1]
        proposal=portrait['pending_preferences'][0]
        self.assertFalse(portrait['confirmed_preferences'])
        status, result, _ = self.tool('profile_proposal_review',{'expected_revision':self.revision(),'proposal_id':proposal['id'],'decision':'accept','source_id':'actual-http-test-review'})
        self.assertEqual(status,200)
        self.assertEqual(len(self.tool('profile_read',{'context':'writing'})[1]['rules']),1)
        boot=self.request()[1]
        self.assertEqual(len(boot['sources']),1)
        status,pause_result,_=self.tool('profile_pause',{'expected_revision':self.revision(),'paused':True})
        self.assertEqual(status,200)
        self.assertEqual(set(pause_result['profile']),{'revision','paused'})
        self.assertNotIn('I prefer concise explanations.',json.dumps(pause_result))
        paused=self.request()[1]
        self.assertTrue(paused['paused'])
        self.assertEqual((paused['rules'],paused['sources'],paused['contexts']),([],[],[]))
        status,result,_=self.tool('conversation_import',{'expected_revision':self.revision(),'conversation':self.conversation('I prefer short answers.')})
        self.assertEqual((status,result['code']),(400,'MEMORY_PAUSED'))
        self.assertEqual(self.tool('profile_forget_messages',{'expected_revision':self.revision(),'source_keys':[boot['sources'][0]['key']]})[0],200)
        self.tool('profile_pause',{'expected_revision':self.revision(),'paused':False})
        self.assertFalse(self.request()[1]['sources'])
        self.assertFalse(self.tool('profile_read',{'context':'writing'})[1]['rules'])

    def test_html_user_text_remains_json_data_and_not_in_page(self):
        text='<img src=x onerror=alert(1)> <script>window.pwned=1</script>'
        self.assertEqual(self.tool('conversation_import',{'expected_revision':0,'conversation':self.conversation(text)})[0],200)
        self.assertEqual(self.request()[1]['sources'][0]['excerpt'],text)
        self.assertNotIn(text,self.request(path='/')[1])
        # Browser rendering remains a separate check; every user-content DOM write
        # in the shipped client uses textContent, never an HTML interpretation sink.
        self.assertIn('node.textContent=text',(ROOT/'web/app.js').read_text())

    def test_disabled_import_and_stale_revision_preserve_state(self):
        self.args.enable_conversations=False
        status,result,_=self.tool('conversation_import',{'expected_revision':0,'conversation':self.conversation()})
        self.assertEqual((status,result['code']),(400,'CONVERSATIONS_DISABLED'))
        self.assertEqual(self.revision(),0)
        self.tool('profile_pause',{'expected_revision':0,'paused':True})
        status,result,_=self.tool('profile_pause',{'expected_revision':0,'paused':False})
        self.assertEqual((status,result['code']),(409,'STALE_REVISION'))
        self.assertTrue(self.request()[1]['paused'])

    def test_limits_invalid_json_and_content_type_have_no_mutation(self):
        for headers, expected in [({'Content-Length':str(MAX_BODY+1)},413),
                                  ({'Content-Length':'0'},413),
                                  ({'Content-Type':'text/plain'},415),
                                  ({'Transfer-Encoding':'chunked'},400)]:
            self.assertEqual(self.request('POST','/api/call',{'name':'profile_pause','arguments':{}},headers)[0],expected)
        self.assertEqual(self.request('POST','/api/call',[])[0],400)
        self.assertEqual(self.request('POST','/api/call',{'name':[], 'arguments':{}})[0],403)
        self.assertEqual(self.request('OPTIONS','/api/call')[0],405)
        self.assertEqual(self.revision(),0)

    def test_tokens_are_unique_per_server_start(self):
        other=make_server(self.args)
        try:
            self.assertNotEqual(self.server.token,other.token)
            self.assertEqual(self.server.server_address[0],'127.0.0.1')
        finally:other.server_close()

    def test_habit_to_plan_outcome_and_source_deletion_over_real_http(self):
        for index in range(3):
            conversation=self.conversation('Too long. Please keep it brief.')
            conversation['session_id']='repeated-'+str(index)
            self.assertEqual(self.tool('conversation_import',{'expected_revision':self.revision(),'conversation':conversation})[0],200)
        habits=self.tool('profile_habits',{'context':'writing'})[1]['candidates']
        candidate=next(item for item in habits if item['dimension']=='response_length')
        self.assertEqual(candidate['status'],'ready_to_review')
        self.assertEqual(self.tool('profile_habit_review',{'expected_revision':self.revision(),'context':'writing','candidate_id':candidate['candidate_id'],'decision':'accept','source_id':'real-workspace-review'})[0],200)
        task={'context':'writing','task':'Explain the release plan.'}
        preview=self.tool('profile_plan',task)[1]
        self.assertEqual(preview['selected'][0]['value'],'concise')
        override=self.tool('profile_plan',{**task,'task_overrides':{'response_length':'detailed'}})[1]
        self.assertFalse(override['selected'])
        self.assertEqual(override['excluded'][0]['reason'],'current_task_override')
        self.assertEqual(self.tool('profile_read',{'context':'writing'})[1]['rules'][0]['value'],'concise')
        status, prepared, _=self.tool('profile_plan_prepare',{'expected_revision':self.revision(),**task})
        self.assertEqual(status,200)
        plan_id=prepared['plan']['plan_id']
        self.assertEqual(prepared['plan']['personalized_prompt'],preview['personalized_prompt'])
        self.assertEqual(self.tool('profile_outcome',{'expected_revision':self.revision(),'plan_id':plan_id,'source_id':'real-workspace-feedback','rating':'helpful','basis':'prompt_review'})[0],200)
        summary=self.tool('profile_outcome_summary',{'context':'writing'})[1]
        self.assertEqual(summary['by_basis']['prompt_review']['helpful'],1)
        self.assertEqual(summary['by_basis']['response_use']['helpful'],0)
        source=self.request()[1]['sources'][0]['key']
        self.assertEqual(self.tool('profile_forget_messages',{'expected_revision':self.revision(),'source_keys':[source]})[0],200)
        self.assertEqual(self.tool('profile_outcome_summary',{'context':'writing'})[1]['plans'],[])
        self.assertFalse(self.tool('profile_plan',task)[1]['selected'])


if __name__ == '__main__':
    unittest.main()
