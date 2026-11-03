"""Actual profile transactions from authored feedback through use and deletion."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from host import dispatch
from host_support import Problem


class HabitIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.args = SimpleNamespace(root=self.tmp.name,subject='alice',enable_conversations=True)
        self.now = dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=1)

    def tearDown(self): self.tmp.cleanup()
    def call(self, name, args): return dispatch(name,args,self.args)
    def revision(self): return self.call('profile_read',{'context':'writing'})['revision']
    def write(self, name, args): return self.call(name,{'expected_revision':self.revision(),**args})
    def add(self, session, text='Too long. Please keep it brief.', context='writing'):
        return self.write('conversation_import',{'conversation':{'session_id':session,'context':context,'messages':[{'id':'m1','role':'user','text':text,'at':self.now.isoformat()}]}})
    def seed(self):
        for index in range(3):self.add('session-'+str(index))
    def candidate(self):return self.call('profile_habits',{'context':'writing'})['candidates'][0]

    def test_repeated_feedback_becomes_reviewable_and_changes_actual_plan(self):
        self.seed()
        candidate = self.candidate()
        self.assertEqual(candidate['status'],'ready_to_review')
        self.assertEqual(candidate['supporting_sessions'],3)
        self.assertEqual(len(candidate['source_keys']),3)
        before = self.call('profile_plan',{'context':'writing','task':'Explain caching.'})
        self.assertEqual(before['selected'],[])
        accepted = self.write('profile_habit_review',{'context':'writing','candidate_id':candidate['candidate_id'],'decision':'accept','source_id':'real-fixture-review'})
        after = self.call('profile_plan',{'context':'writing','task':'Explain caching.'})
        self.assertEqual(after['selected'][0]['id'],accepted['rule_id'])
        self.assertIn('Keep responses concise.',after['personalized_prompt'])

    def test_single_session_and_rejected_candidate_cannot_auto_adopt(self):
        self.add('session-1')
        c = self.candidate()
        with self.assertRaises(Problem):self.write('profile_habit_review',{'context':'writing','candidate_id':c['candidate_id'],'decision':'accept','source_id':'early'})
        self.add('session-2');self.add('session-3')
        self.write('profile_habit_review',{'context':'writing','candidate_id':self.candidate()['candidate_id'],'decision':'reject','source_id':'reject'})
        self.assertEqual(self.call('profile_habits',{'context':'writing'})['candidates'],[])
        self.assertEqual(self.call('profile_read',{'context':'writing'})['rules'],[])

    def test_source_forgetting_removes_habit_plan_and_outcomes(self):
        self.seed()
        self.write('profile_habit_review',{'context':'writing','candidate_id':self.candidate()['candidate_id'],'decision':'accept','source_id':'review'})
        plan = self.write('profile_plan_prepare',{'context':'writing','task':'Explain caching.'})['plan']
        self.write('profile_outcome',{'plan_id':plan['plan_id'],'source_id':'vote','rating':'helpful','basis':'prompt_review'})
        result = self.write('profile_forget_conversation',{'session_id':'session-0'})
        self.assertFalse(result['profile']['rules'])
        self.assertFalse(result['profile']['prepared_plans'])
        self.assertFalse(result['profile']['plan_outcomes'])
        self.assertFalse(self.call('profile_habits',{'context':'writing'})['candidates'])

    def test_forgetting_explicit_typed_rule_cannot_revive_unconfirmed_old_habit(self):
        self.seed();self.add('other-session',context='coding')
        self.write('profile_correct',{'rule':{'id':'explicit','scope':'writing','statement':'Please explain fully.','dimension':'response_length','value':'detailed','source_id':'explicit','source_summary':'Fixture user correction','kind':'correction'}})
        self.assertEqual(self.candidate()['status'],'confirmed_preference_exists')
        self.write('profile_forget',{'rule_id':'explicit'})
        self.assertFalse(self.call('profile_habits',{'context':'writing'})['candidates'])
        self.assertEqual(len(self.call('profile_habits',{'context':'coding'})['candidates']),1)

    def test_pause_blocks_review_and_ordinary_discovery(self):
        self.seed();cid=self.candidate()['candidate_id']
        self.write('profile_pause',{'paused':True})
        self.assertFalse(self.call('profile_habits',{'context':'writing'})['candidates'])
        with self.assertRaises(Problem):self.write('profile_habit_review',{'context':'writing','candidate_id':cid,'decision':'accept','source_id':'paused'})


if __name__ == '__main__':unittest.main()
