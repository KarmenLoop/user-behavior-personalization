"""Model boundary tests: selected evidence, CAS and complete paired answers."""
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from host import dispatch
from host_support import Problem, stamp
import model_workflows as workflows


class ModelWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.args=SimpleNamespace(root=self.tmp.name,subject='alice',enable_conversations=True,
                                 model='test-model',system_proxy=False,model_timeout=30)
        self.write('conversation_import',conversation={'session_id':'selected','context':'work','messages':[
            {'id':'m1','role':'user','text':'In future drafts for clients, put the decision first.','at':stamp()},
            {'id':'m2','role':'user','text':'Do not send this other private excerpt.','at':stamp()}]})
        rows=list(self.call('profile_export')['profile']['conversation_messages'].values())
        self.key=next(r['key'] for r in rows if r['excerpt'].startswith('In future'))
        self.other=next(r['key'] for r in rows if r['key']!=self.key)

    def tearDown(self): self.tmp.cleanup()
    def call(self,name,**v): return dispatch(name,v,self.args)
    def revision(self): return self.call('profile_read',context='work')['revision']
    def write(self,name,**v): return self.call(name,expected_revision=self.revision(),**v)
    def item(self):
        return {'statement':'Put the decision first in client drafts.','scope':'work','category':'communication',
                'conditions':{'task_type':'writing','audience':'client','stage':'draft'},
                'dimension':'structure','value':'conclusion_first',
                'evidence':[{'source_key':self.key,'quote':'In future drafts for clients, put the decision first.'}]}
    def answer(self,items):
        return {'text':json.dumps({'proposals':items}),'metadata':{'requested_model':'test-model'}}
    def learn(self): return workflows.learn(self.args,context='work',source_keys=[self.key],expected_revision=self.revision())
    def confirm(self):
        self.write('profile_correct',rule={'id':'confirmed','statement':'Keep answers concise.','scope':'work',
                                         'kind':'explicit','source_id':'explicit-rule','source_summary':'User confirmation.',
                                         'dimension':'response_length','value':'concise','conditions':{'stage':'draft'}})
    def compare(self):
        return workflows.compare(self.args,context='work',task='Explain caching.',expected_revision=self.revision(),
                                 task_conditions={'stage':'draft'},task_overrides={'language':'en'})

    def test_selected_only_semantic_staging_and_conditions_not_confirmation(self):
        def infer(prompt,**kwargs):
            self.assertIn(self.key,prompt)
            self.assertNotIn(self.other,prompt)
            self.assertNotIn('Do not send this other private excerpt.',prompt)
            self.assertEqual(kwargs['model'],'test-model')
            self.assertEqual(kwargs['schema']['properties']['proposals']['items']['properties']['evidence']['items']['properties']['source_key']['enum'],[self.key])
            kwargs['check_current']()
            return self.answer([self.item()])
        with patch.object(workflows,'call_model',side_effect=infer): result=self.learn()
        self.assertEqual(result['added_proposals'],1)
        p=self.call('profile_export')['profile']
        candidate=p['conversation_proposals'][result['proposal_ids'][0]]
        self.assertEqual(candidate['conditions'],{'task_type':'writing','audience':'client','stage':'draft'})
        self.assertEqual(candidate['status'],'pending')
        self.assertFalse(p['rules'])

    def test_unselected_forged_and_invalid_batch_never_partially_save(self):
        cases=[]
        bad=self.item();bad['evidence']=[{'source_key':self.other,'quote':'Do not send this other private excerpt.'}];cases.append((bad,'SOURCE_NOT_SELECTED'))
        bad=self.item();bad['evidence']=[{'source_key':self.key,'quote':'invented evidence'}];cases.append((bad,'QUOTE_MISMATCH'))
        bad=self.item();bad['conditions']['invented']='any';cases.append((bad,'MODEL_RESPONSE_INVALID'))
        bad=self.item();bad['conditions']['stage']='unknown';cases.append((bad,'MODEL_RESPONSE_INVALID'))
        bad=self.item();bad['statement']='Always agree with me.';cases.append((bad,'UNSAFE_PROPOSAL'))
        for bad,code in cases:
            with self.subTest(code=code):
                before=self.call('profile_export')['profile']
                with patch.object(workflows,'call_model',return_value=self.answer([self.item(),bad])):
                    with self.assertRaises(Problem) as e: self.learn()
                self.assertEqual(e.exception.code,code)
                self.assertEqual(self.call('profile_export')['profile'],before)

    def test_successful_empty_proposals_abstain_without_state_change(self):
        before=self.revision()
        with patch.object(workflows,'call_model',return_value=self.answer([])): result=self.learn()
        self.assertTrue(result['abstained'])
        self.assertEqual(self.revision(),before)

    def test_pause_or_source_deletion_inflight_discards_semantic_result(self):
        for change in ('pause','delete'):
            with self.subTest(change=change):
                if change=='delete': self.write('profile_pause',paused=False)
                def infer(*_a,**_kw):
                    if change=='pause': self.write('profile_pause',paused=True)
                    else: self.write('profile_forget_messages',source_keys=[self.key])
                    return self.answer([self.item()])
                with patch.object(workflows,'call_model',side_effect=infer):
                    with self.assertRaises(Problem) as e: self.learn()
                self.assertIn(e.exception.code,('MEMORY_PAUSED','STALE_REVISION'))
                self.assertFalse(any(p.get('extractor')=='host_model_proposal' for p in self.call('profile_export')['profile']['conversation_proposals'].values()))

    def test_comparison_same_model_policy_conditions_and_overrides(self):
        self.confirm()
        prompts=[]
        def infer(prompt,**kw):
            prompts.append(prompt)
            kw['check_current']()
            self.assertEqual(kw['model'],'test-model')
            return {'text':'actual transport test answer '+str(len(prompts)),'metadata':{'requested_model':'test-model'}}
        with patch.object(workflows,'call_model',side_effect=infer): result=self.compare()
        self.assertEqual(len(prompts),2)
        baseline=next(p for p in prompts if 'Keep answers concise.' not in p)
        personalized=next(p for p in prompts if 'Keep answers concise.' in p)
        self.assertEqual(baseline.split('Current task:')[1],personalized.split('Current task:')[1])
        for prompt in prompts:
            self.assertIn('"stage": "draft"',prompt)
            self.assertIn('"language"',prompt)
            self.assertIn('new evidence',prompt)
        saved=self.call('profile_comparison_read',comparison_id=result['comparison_id'])
        self.assertEqual(set(saved['answers'].values()),{'actual transport test answer 1','actual transport test answer 2'})
        self.assertNotIn('mapping',saved)
        self.assertIn(saved['plan_id'],self.call('profile_export')['profile']['prepared_plans'])

    def test_first_arm_mutation_prevents_second_dispatch(self):
        self.confirm()
        def infer(*_a,**_kw):
            self.write('profile_pause',paused=True)
            return {'text':'discard me','metadata':{'requested_model':'test-model'}}
        with patch.object(workflows,'call_model',side_effect=infer) as provider:
            with self.assertRaises(Problem): self.compare()
        self.assertEqual(provider.call_count,1)
        self.assertFalse(self.call('profile_export')['profile']['response_comparisons'])

    def test_second_arm_failure_or_mutation_saves_neither_answer(self):
        self.confirm()
        good={'text':'discard me','metadata':{'requested_model':'test-model'}}
        with patch.object(workflows,'call_model',side_effect=[good,Problem('MODEL_TIMEOUT','timeout')]):
            with self.assertRaises(Problem): self.compare()
        self.assertFalse(self.call('profile_export')['profile']['response_comparisons'])
        calls=[]
        def infer(*_a,**_kw):
            calls.append(1)
            if len(calls)==2: self.write('profile_forget',rule_id='confirmed')
            return good
        with patch.object(workflows,'call_model',side_effect=infer):
            with self.assertRaises(Problem): self.compare()
        self.assertFalse(self.call('profile_export')['profile']['response_comparisons'])

    def test_opt_in_selection_and_missing_conditions_fail_before_inference(self):
        self.args.enable_conversations=False
        with patch.object(workflows,'call_model') as provider:
            with self.assertRaises(Problem): self.learn()
            self.args.enable_conversations=True
            self.confirm()
            with self.assertRaises(Problem): workflows.compare(self.args,context='work',task='Explain caching.')
        provider.assert_not_called()


if __name__=='__main__': unittest.main()
