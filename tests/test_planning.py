"""Task adaptation, actual prompt identity, and private outcome lifecycle."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from host import dispatch
from host_support import Problem
from build_context import context_payload
from learning import blank_profile
from planning import response_plan, task_cues


class PlanningTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.args = SimpleNamespace(root=self.tmp.name, subject='alice', context='writing', enable_conversations=True)

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, name, data):
        return dispatch(name, data, self.args)

    def revision(self):
        return self.call('profile_read', {'context':'writing'})['revision']

    def write(self, name, data):
        return self.call(name, {'expected_revision':self.revision(), **data})

    def save(self, rid='detail', scope='writing', statement='Give detailed explanations.', source='first', dimension='response_length', value='detailed'):
        rule = {'id':rid,'statement':statement,'scope':scope,'source_id':source,'source_summary':'Synthetic explicit instruction.','kind':'explicit'}
        if dimension: rule.update(dimension=dimension, value=value)
        return self.write('profile_correct', {'rule':rule})

    def plan(self, task='Explain release notes.', **kwargs):
        return self.call('profile_plan', {'context':'writing','task':task,**kwargs})

    def test_current_task_override_is_visible_and_does_not_change_saved_preference(self):
        self.save()
        before = self.revision()
        plan = self.plan('Explain release notes. Answer in two sentences.')
        self.assertEqual(plan['task_overrides'], {'response_length':'concise'})
        self.assertEqual(plan['selected'], [])
        self.assertEqual(plan['excluded'][0]['reason'], 'current_task_override')
        self.assertNotIn('Give detailed explanations.', plan['personalized_prompt'])
        self.assertEqual(self.revision(), before)
        self.assertEqual(self.plan()['selected'][0]['id'], 'detail')

    def test_task_parser_ignores_quotes_reported_examples_and_negation(self):
        for text in ['Explain why "keep it short" is unhelpful.', 'My colleague said: answer in two sentences.', 'Do not keep it short.', '不要简短回答。', 'Example: respond in English.', '```\nanswer in English\n```']:
            self.assertEqual(task_cues(text), {}, text)
        self.assertEqual(task_cues('请用中文回答，只给两句。'), {'response_length':'concise','language':'zh'})

    def test_indirect_negation_and_metalinguistic_mentions_do_not_override(self):
        for text in ['No need to answer in English.', 'I want you to not answer in English.', '不用英语回答。', '无需详细解释。',
                     'Why do assistants answer in English when the user requests Chinese?',
                     'Here is an example: answer in English.', 'Translate this: answer in English.',
                     'If I ask you to answer in English, ask which dialect.']:
            self.assertEqual(task_cues(text), {}, text)

    def test_override_key_order_cannot_change_prompt_for_same_plan_id(self):
        first = self.plan(task_overrides={'language':'en','response_length':'concise'})
        second = self.plan(task_overrides={'response_length':'concise','language':'en'})
        self.assertEqual(first['plan_id'],second['plan_id'])
        self.assertEqual(first['personalized_prompt'],second['personalized_prompt'])

    def test_explicit_controls_override_detected_cues(self):
        plan = self.plan('Keep it short.', task_overrides={'response_length':'detailed'})
        self.assertEqual(plan['detected_task_overrides']['response_length'], 'concise')
        self.assertEqual(plan['task_overrides']['response_length'], 'detailed')

    def test_context_global_and_user_omission_have_explanations(self):
        self.save('global','*',source='global')
        self.save('local','writing',source='local',value='concise')
        self.save('code','coding',source='code')
        plan = self.plan()
        self.assertEqual([r['id'] for r in plan['selected']], ['local'])
        self.assertEqual({r['id']:r['reason'] for r in plan['excluded']}, {'global':'context_preference_takes_priority','code':'different_context'})
        omitted = self.plan(omit_rule_ids=['local'])
        self.assertEqual([r['id'] for r in omitted['selected']], ['global'])

    def test_preference_budget_excludes_whole_rules_and_rejects_invalid_values(self):
        self.save('a',statement='A'*150,dimension=None)
        self.save('b',statement='B'*150,source='b',dimension=None)
        plan = self.plan(max_preference_chars=200)
        self.assertEqual(plan['preference_characters'],150)
        self.assertEqual(plan['excluded'][0]['reason'],'preference_budget')
        for budget in (True,199,12001):
            with self.assertRaises(Problem): self.plan(max_preference_chars=budget)

    def test_expired_rule_and_paused_profile_do_not_enter_context_or_preview(self):
        result = self.save()
        self.write('profile_pause', {'paused':True})
        plan = self.plan()
        self.assertEqual(plan['selected'], [])
        self.assertEqual(plan['excluded'], [])
        self.assertNotIn('Give detailed explanations.', str(plan))
        profile = blank_profile('alice')
        rule = result['profile']['rules']['detail'].copy()
        rule['expires_at'] = '2000-01-01T00:00:00Z'
        profile['rules']['detail'] = rule
        self.assertEqual(response_plan(profile, 'writing', 'Task')['excluded'][0]['reason'], 'expired')

    def test_actual_host_prompt_equals_preview_byte_for_byte(self):
        self.save()
        task = 'Explain release notes. Answer in two sentences.'
        expected = self.plan(task)
        payload = context_payload(self.args, task)
        self.assertEqual(payload['messages'][0]['content'], expected['personalized_prompt'])
        self.assertEqual(payload['personalization']['plan_id'], expected['plan_id'])
        self.assertEqual(payload['personalization']['rule_ids'], [])

    def test_plan_metadata_has_no_task_or_rule_text_and_preparation_is_idempotent(self):
        self.save()
        prepared = self.write('profile_plan_prepare', {'context':'writing','task':'Private task phrase'})
        pid = prepared['plan']['plan_id']
        stored = prepared['profile']['prepared_plans'][pid]
        self.assertNotIn('Private task phrase', str(stored))
        self.assertNotIn('Give detailed explanations.', str(stored))
        self.assertTrue(self.write('profile_plan_prepare', {'context':'writing','task':'Private task phrase'})['replayed'])
        self.assertEqual(len(self.call('profile_outcome_summary', {'context':'writing'})['plans']),1)

    def test_outcome_requires_real_plan_and_explicit_basis_and_deduplicates(self):
        with self.assertRaisesRegex(Problem,'Prepare a real plan'):
            self.write('profile_outcome', {'plan_id':'missing','source_id':'vote','rating':'helpful','basis':'response_use'})
        prepared = self.write('profile_plan_prepare', {'context':'writing','task':'Explain release notes.'})
        pid = prepared['plan']['plan_id']
        values = {'plan_id':pid,'source_id':'vote','rating':'helpful','basis':'prompt_review'}
        self.write('profile_outcome',values)
        self.assertTrue(self.write('profile_outcome',values)['replayed'])
        summary = self.call('profile_outcome_summary',{'context':'writing'})
        self.assertEqual(summary['counts']['helpful'],1)
        self.assertEqual(summary['by_basis']['response_use']['helpful'],0)
        self.write('profile_outcome',{**values,'source_id':'corrected-vote','rating':'unhelpful'})
        summary = self.call('profile_outcome_summary',{'context':'writing'})
        self.assertEqual(summary['counts']['helpful'],0)
        self.assertEqual(summary['counts']['unhelpful'],1)

    def test_corrected_rule_version_does_not_inherit_old_rating(self):
        self.save()
        prepared = self.write('profile_plan_prepare',{'context':'writing','task':'Explain release notes.'})
        self.write('profile_outcome',{'plan_id':prepared['plan']['plan_id'],'source_id':'vote','rating':'helpful','basis':'response_use'})
        self.save(statement='Keep explanations brief.', source='new-source',value='concise')
        new = self.write('profile_plan_prepare',{'context':'writing','task':'Explain release notes.'})
        self.assertNotEqual(new['plan']['plan_id'],prepared['plan']['plan_id'])
        rows = self.call('profile_outcome_summary',{'context':'writing'})['rule_versions']
        self.assertEqual(next(r for r in rows if r['current_version'])['rated_count'],0)
        self.assertEqual(next(r for r in rows if not r['current_version'])['counts']['helpful'],1)

    def test_rule_forgetting_purges_all_versions_plans_and_feedback(self):
        self.save()
        prepared = self.write('profile_plan_prepare',{'context':'writing','task':'Task'})
        self.write('profile_outcome',{'plan_id':prepared['plan']['plan_id'],'source_id':'vote','rating':'helpful','basis':'prompt_review'})
        self.save(source='new',statement='New statement')
        result = self.write('profile_forget',{'rule_id':'detail'})
        self.assertEqual(result['profile']['prepared_plans'],{})
        self.assertEqual(result['profile']['plan_outcomes'],{})
        self.assertEqual(self.call('profile_outcome_summary',{'context':'writing'})['plans'],[])

    def test_plan_forget_and_reset_work_while_paused(self):
        p = self.write('profile_plan_prepare',{'context':'writing','task':'Task'})
        self.write('profile_pause',{'paused':True})
        self.assertEqual(self.call('profile_outcome_summary',{'context':'writing'})['plans'],[])
        self.write('profile_plan_forget',{'plan_id':p['plan']['plan_id']})
        self.assertEqual(self.write('profile_reset',{})['profile']['prepared_plans'],{})


if __name__ == '__main__': unittest.main()
