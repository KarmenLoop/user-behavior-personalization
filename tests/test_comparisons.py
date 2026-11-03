"""Private A/B boundaries, durable reveal and dependent deletion."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from host import dispatch, load, subject_key
from host_support import Database, Problem
from planning import response_plan
from outcomes import prepare
from comparisons import store_comparison


class ComparisonTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.args = SimpleNamespace(root=self.tmp.name, subject='alice', enable_conversations=True)
        self.write('conversation_import', conversation={'session_id':'source','context':'work','messages':[
            {'id':'m1','role':'user','text':'I prefer concise answers.','at':dt.datetime.now(dt.timezone.utc).isoformat()}]})
        proposal = self.call('profile_portrait',context='work')['pending_preferences'][0]
        self.write('profile_proposal_review',proposal_id=proposal['id'],decision='accept',source_id='approval')
        db = Database(self.args.root)
        try:
            p = load(db,self.args)
            plan = response_plan(p,'work','Explain caching.')
            prepare(p,plan)
            store_comparison(p,plan,{arm:{'text':arm+' answer','metadata':{'requested_model':'configured','prompt_sha256':arm+'-hash'}}
                                    for arm in ('baseline','personalized')},'comparison-one')
            p['revision'] += 1
            db.put(subject_key(self.args),p)
            self.plan_id = plan['plan_id']
        finally: db.close()

    def tearDown(self): self.tmp.cleanup()
    def call(self,name,**v): return dispatch(name,v,self.args)
    def write(self,name,**v):
        return self.call(name,expected_revision=self.call('profile_read',context='work')['revision'],**v)
    def read(self): return self.call('profile_comparison_read',comparison_id='comparison-one')
    def vote(self,source='vote',choice='tie'):
        return self.write('profile_comparison_vote',comparison_id='comparison-one',source_id=source,choice=choice,
                          accuracy_a='not_checked',accuracy_b='reported_incorrect')

    def test_blinding_vote_and_revealed_revision_preserve_first_blind_vote(self):
        first = self.read()
        self.assertEqual(set(first['answers']),{'a','b'})
        for field in ('mapping','selected_preferences','execution_metadata'): self.assertNotIn(field,first)
        self.assertNotIn('baseline-hash',str(first))
        before = self.call('profile_read',context='work')['rules']
        self.assertTrue(self.vote()['feedback']['blinded'])
        self.assertIn('mapping',self.read())
        self.assertFalse(self.vote('revised-vote','neither')['feedback']['blinded'])
        self.assertTrue(self.vote('revised-vote','neither')['replayed'])
        profile = self.call('profile_export')['profile']
        self.assertEqual([v['blinded'] for v in profile['response_comparisons']['comparison-one']['feedback_history']],[True,False])
        self.assertEqual(self.call('profile_read',context='work')['rules'],before)
        self.assertEqual(self.call('profile_outcome_summary',context='work')['counts']['helpful'],0)

    def test_explicit_reveal_is_persistent_and_feedback_is_not_blind(self):
        self.write('profile_comparison_reveal',comparison_id='comparison-one')
        self.assertTrue(self.read()['revealed'])
        self.assertTrue(self.write('profile_comparison_reveal',comparison_id='comparison-one')['replayed'])
        self.assertFalse(self.vote()['feedback']['blinded'])

    def test_pause_hides_answers_but_allows_forget(self):
        self.write('profile_pause',paused=True)
        self.assertFalse(self.call('profile_comparison_list',context='work')['comparisons'])
        for name,fields in [('profile_comparison_read',{'comparison_id':'comparison-one'}),
                            ('profile_comparison_reveal',{'comparison_id':'comparison-one'})]:
            with self.assertRaises(Problem) as e:
                self.call(name,**fields) if name.endswith('_read') else self.write(name,**fields)
            self.assertEqual(e.exception.code,'MEMORY_PAUSED')
        self.write('profile_comparison_forget',comparison_id='comparison-one')
        self.assertFalse(self.call('profile_export')['profile']['response_comparisons'])

    def test_forget_source_removes_plan_answers_feedback_and_blocks_replay(self):
        self.vote()
        source = next(iter(self.call('profile_export')['profile']['conversation_messages']))
        self.write('profile_forget_messages',source_keys=[source])
        profile = self.call('profile_export')['profile']
        self.assertFalse(profile['response_comparisons'])
        self.assertNotIn(self.plan_id,profile['prepared_plans'])
        self.assertNotIn('baseline answer',str(profile))
        from learning import check_source
        with self.assertRaises(Problem) as e: check_source(profile,'vote',{})
        self.assertEqual(e.exception.code,'SOURCE_FORGOTTEN')

    def test_forget_plan_and_reset_remove_comparisons(self):
        self.write('profile_plan_forget',plan_id=self.plan_id)
        self.assertFalse(self.call('profile_export')['profile']['response_comparisons'])
        self.write('profile_reset')
        self.assertEqual(self.call('profile_export')['profile']['response_comparisons'],{})

    def test_read_has_no_stateless_reveal_switch_and_stale_vote_fails(self):
        with self.assertRaises(Problem): self.call('profile_comparison_read',comparison_id='comparison-one',reveal=True)
        with self.assertRaises(Problem) as e:
            self.call('profile_comparison_vote',expected_revision=0,comparison_id='comparison-one',source_id='v',choice='a',accuracy_a='not_checked',accuracy_b='not_checked')
        self.assertEqual(e.exception.code,'STALE_REVISION')
        self.assertFalse(self.read()['revealed'])


if __name__ == '__main__': unittest.main()
