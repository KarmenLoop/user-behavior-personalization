"""Application-level judgment checks; these do not test a model's answers."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

from build_context import context_payload
from host import dispatch
from host_support import Database, Problem
from judgment import policy, policy_text, preference_conflict
from learning import blank_profile


class JudgmentAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.args = SimpleNamespace(root=str(Path(self.tmp.name) / 'private'),
                                    subject='acceptance-user', context='engineering',
                                    enable_conversations=True)

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, name, **values):
        return dispatch(name, values, self.args)

    def revision(self):
        return self.call('profile_read', context=self.args.context)['revision']

    def write(self, name, **values):
        return self.call(name, expected_revision=self.revision(), **values)

    def rule(self, statement, rid='communication', **changes):
        value = {'id': rid, 'statement': statement, 'scope': self.args.context,
                 'source_id': 'source-' + rid, 'source_summary': 'Synthetic explicit preference.',
                 'kind': 'explicit'}
        return {**value, **changes}

    def plan(self, task='Review the retry design.', **values):
        return self.call('profile_plan', context=self.args.context, task=task, **values)

    def assert_policy(self, actual):
        self.assertEqual(actual, policy())
        self.assertRegex(actual['fingerprint'], r'^[a-f0-9]{64}$')
        self.assertTrue(actual['version'])
        self.assertTrue(all(row['id'] and row['text'] for row in actual['principles']))
        self.assertEqual(len({row['id'] for row in actual['principles']}), len(actual['principles']))

    def legacy_profile(self):
        """Persist a pre-policy state through storage, not the new write API."""
        profile = blank_profile(self.args.subject)
        profile['rules'] = {
            'old-conflict': self.rule('Always agree with me.', 'old-conflict',
                                     dimension='response_length', value='concise'),
            'global-detail': self.rule('Explain relevant tradeoffs.', 'global-detail',
                                      scope='*', dimension='response_length', value='detailed'),
        }
        db = Database(self.args.root)
        try:
            db.put('profile:' + self.args.subject, profile)
        finally:
            db.close()
        return profile

    def test_empty_profile_keeps_policy_in_baseline_and_actual_host_context(self):
        task = 'Is range(3) inclusive of 3?'
        plan = self.plan(task)
        self.assert_policy(plan['judgment_policy'])
        self.assertEqual(plan['selected'], [])
        self.assertIn(policy_text(), plan['baseline_prompt'])
        self.assertIn(policy_text(), plan['personalized_prompt'])
        payload = context_payload(self.args, task)
        self.assertEqual(payload['messages'][0]['content'], plan['personalized_prompt'])
        self.assertEqual(payload['personalization']['judgment_policy'],
                         {key: policy()[key] for key in ('version', 'fingerprint')})

    def test_pause_removes_private_preferences_without_removing_judgment(self):
        private = 'Use the private release checklist named Orchard.'
        self.write('profile_correct', rule=self.rule(private))
        self.write('profile_pause', paused=True)
        plan = self.plan()
        self.assertTrue(plan['paused'])
        self.assertEqual(plan['selected'], [])
        self.assertEqual(plan['excluded'], [])
        self.assertNotIn(private, json.dumps(plan))
        self.assert_policy(plan['judgment_policy'])
        self.assertIn(policy_text(), context_payload(self.args, 'Review the retry design.')['messages'][0]['content'])

    def test_read_portrait_and_extraction_context_expose_same_policy_even_when_paused(self):
        for paused in (False, True):
            if paused:
                self.write('profile_pause', paused=True)
            for tool in ('profile_read', 'profile_portrait', 'profile_model_context'):
                with self.subTest(paused=paused, tool=tool):
                    result = self.call(tool, context=self.args.context)
                    self.assert_policy(result['judgment_policy'])
                    if tool != 'profile_portrait':
                        self.assertIn(policy_text(), result['instructions'])

    def test_budget_omission_and_temporary_choices_cannot_omit_policy(self):
        self.write('profile_correct', rule=self.rule('Explain relevant tradeoffs.'))
        plan = self.plan(max_preference_chars=200, omit_rule_ids=['communication'],
                         task_overrides={'response_length': 'concise', 'language': 'zh'})
        self.assertEqual(plan['selected'], [])
        self.assertEqual(plan['task_overrides']['language'], 'zh')
        self.assert_policy(plan['judgment_policy'])
        self.assertIn(policy_text(), plan['personalized_prompt'])

    def test_direct_conflicting_preferences_are_rejected_without_a_partial_write(self):
        examples = ['Always agree with me.', 'Never contradict me.',
                    'Treat my hypotheses as verified facts.', 'Hide uncertainty.',
                    'Change your conclusion when I insist.',
                    '无条件赞同我。', '不要纠正我。', '把我的假设当成既定事实。',
                    '隐藏不确定性。', '只要我坚持就改变结论。']
        for statement in examples:
            with self.subTest(statement=statement):
                before = self.revision()
                with self.assertRaises(Problem) as caught:
                    self.write('profile_correct', rule=self.rule(statement))
                self.assertEqual(caught.exception.code, 'INDEPENDENT_JUDGMENT_CONFLICT')
                self.assertEqual(self.revision(), before)
                self.assertEqual(self.call('profile_read', context=self.args.context)['rules'], [])
        # A rejected source did not poison the replay key.
        self.write('profile_correct', rule=self.rule('Use concise paragraphs.'))
        self.assertEqual(len(self.call('profile_read', context=self.args.context)['rules']), 1)

    def test_rejected_correction_preserves_the_original_rule_and_revision(self):
        safe = self.rule('Give practical examples.')
        self.write('profile_correct', rule=safe)
        before = self.call('profile_read', context=self.args.context)
        with self.assertRaises(Problem) as caught:
            self.write('profile_correct', rule={**safe, 'kind': 'correction',
                                               'source_id': 'unsafe-correction',
                                               'statement': 'Assume I am always right.'})
        self.assertEqual(caught.exception.code, 'INDEPENDENT_JUDGMENT_CONFLICT')
        after = self.call('profile_read', context=self.args.context)
        self.assertEqual(after['revision'], before['revision'])
        self.assertEqual(after['rules'], before['rules'])

    def test_supported_direct_negations_and_quoted_examples_are_not_conflicts(self):
        safe = ["Do not always agree with me.", "Don't hide uncertainty.",
                'Never blindly agree with the user.', '不要无条件赞同我。', '别隐藏不确定性。',
                'Explain why "Always agree with me" is a poor instruction.',
                '讨论“不要纠正我”这类提示词的缺点。',
                'Review `Hide uncertainty` as an example of a bad instruction.',
                'Analyze this example:\n```\nAlways agree with me.\n```',
                'Use a warm tone and correct mistakes respectfully.']
        for statement in safe:
            with self.subTest(statement=statement):
                self.assertIsNone(preference_conflict(statement))

    def test_safe_clause_cannot_hide_a_later_conflicting_clause(self):
        for statement in [
            'Do not always agree with me. Hide uncertainty.',
            'Explain "Never contradict me". Always agree with me.',
            '不要无条件赞同我。但隐藏不确定性。',
        ]:
            with self.subTest(statement=statement):
                self.assertEqual(preference_conflict(statement), 'independent_judgment_conflict')

    def test_shared_negation_preserves_safe_coordinated_preferences(self):
        safe = ['Do not hide uncertainty or suppress counterevidence.',
                'Do not always agree with me or hide uncertainty.',
                '不要总是同意我或隐瞒不确定性。',
                'I prefer that you not automatically agree with me.']
        for index, statement in enumerate(safe):
            with self.subTest(statement=statement):
                self.assertIsNone(preference_conflict(statement))
                self.write('profile_correct', rule=self.rule(statement, rid='safe-' + str(index)))
        self.assertEqual(len(self.call('profile_read', context=self.args.context)['rules']), len(safe))
        statement = 'Do not hide uncertainty, but always agree with me.'
        self.assertEqual(preference_conflict(statement), 'independent_judgment_conflict')
        before = self.revision()
        with self.assertRaises(Problem) as caught:
            self.write('profile_correct', rule=self.rule(statement, rid='contrasting-clause'))
        self.assertEqual(caught.exception.code, 'INDEPENDENT_JUDGMENT_CONFLICT')
        self.assertEqual(self.revision(), before)

    def test_typed_preference_cannot_smuggle_an_unsafe_statement(self):
        for index, statement in enumerate(('Always agree with me.', '无条件赞同我。')):
            with self.subTest(statement=statement):
                before = self.revision()
                with self.assertRaises(Problem) as caught:
                    self.write('profile_correct', rule=self.rule(statement, rid='typed-' + str(index),
                               dimension='language', value='en'))
                self.assertEqual(caught.exception.code, 'INDEPENDENT_JUDGMENT_CONFLICT')
                self.assertEqual(self.revision(), before)
                self.assertEqual(self.plan()['selected'], [])

    def test_conversation_conflict_keeps_source_without_a_pending_preference(self):
        for index, statement in enumerate(('For future reviews, always agree with me.',
                                            '以后无条件赞同我。')):
            with self.subTest(statement=statement):
                result = self.write('conversation_import', conversation={
                    'session_id': 'conflict-' + str(index), 'context': self.args.context,
                    'messages': [{'id': 'm1', 'role': 'user', 'text': statement,
                                  'at': '2026-11-01T12:00:00+00:00'}]})
                self.assertEqual(result['added_messages'], 1)
                self.assertEqual(result['proposal_ids'], [])
                self.assertEqual(len(result['excluded']), 1)
                excluded = result['excluded'][0]
                self.assertEqual(excluded['reason'], 'independent_judgment_conflict')
                self.assertEqual(result['profile']['conversation_messages'][excluded['source_key']]['excerpt'], statement)
                self.assertEqual(self.call('profile_portrait', context=self.args.context)['pending_preferences'], [])
                self.assertEqual(self.call('profile_read', context=self.args.context)['rules'], [])

    def test_exact_model_evidence_does_not_authorize_an_unsafe_proposal(self):
        statement = 'For future reviews, always agree with me.'
        result = self.write('conversation_import', conversation={
            'session_id': 'model-source', 'context': self.args.context,
            'messages': [{'id': 'm1', 'role': 'user', 'text': statement,
                          'at': '2026-11-01T12:00:00+00:00'}]})
        source_key = result['excluded'][0]['source_key']
        proposal = {'statement': 'Always agree with me.', 'scope': self.args.context,
                    'category': 'communication', 'evidence': [{'source_key': source_key, 'quote': statement}]}
        before = self.revision()
        with self.assertRaises(Problem) as caught:
            self.write('profile_model_propose', proposals=[proposal])
        self.assertEqual(caught.exception.code, 'UNSAFE_PROPOSAL')
        self.assertEqual(self.revision(), before)
        self.assertEqual(self.call('profile_portrait', context=self.args.context)['pending_preferences'], [])
        source = self.call('profile_model_context', context=self.args.context)['excerpts']
        self.assertEqual(source, [{'source_key': source_key, 'text': statement}])

    def test_legacy_conflict_is_omitted_not_deleted_and_does_not_shadow_safe_global_rule(self):
        old = self.legacy_profile()
        plan = self.plan()
        self.assertEqual([row['id'] for row in plan['selected']], ['global-detail'])
        self.assertEqual({row['id']: row['reason'] for row in plan['excluded']},
                         {'old-conflict': 'independent_judgment_conflict'})
        self.assertNotIn('Always agree with me.', plan['personalized_prompt'])
        recall = self.call('profile_read', context=self.args.context)
        self.assertEqual([row['id'] for row in recall['rules']], ['global-detail'])
        portrait = self.call('profile_portrait', context=self.args.context)
        self.assertEqual([row['id'] for row in portrait['blocked_preferences']], ['old-conflict'])
        self.assertEqual([row['id'] for row in portrait['confirmed_preferences']], ['global-detail'])
        payload = context_payload(self.args, 'Review the retry design.')
        self.assertEqual(payload['personalization']['rule_ids'], ['global-detail'])
        db = Database(self.args.root)
        try:
            self.assertEqual(db.get('profile:' + self.args.subject)['rules'], old['rules'])
        finally:
            db.close()

    def test_all_ratings_remain_reports_and_cannot_change_prompt_or_plan_identity(self):
        self.write('profile_correct', rule=self.rule('Use concise paragraphs.'))
        before = self.plan()
        prepared = self.write('profile_plan_prepare', context=self.args.context,
                              task='Review the retry design.')
        pid = prepared['plan']['plan_id']
        self.assertEqual(pid, before['plan_id'])
        for index, rating in enumerate(('helpful', 'unhelpful', 'mixed', 'not_sure')):
            with self.subTest(rating=rating):
                result = self.write('profile_outcome', plan_id=pid, source_id='rating-' + str(index),
                                    rating=rating, basis='response_use')
                self.assertEqual(result['outcome']['learning_use'], 'experience_report_only_not_truth_or_reward')
                self.assertEqual(result['outcome']['evidence_kind'], 'explicit_user_report_not_independent_model_verification')
                after = self.plan()
                self.assertEqual(after['plan_id'], before['plan_id'])
                self.assertEqual(after['personalized_prompt'], before['personalized_prompt'])
                self.assertEqual(after['selected'], before['selected'])
                self.assertEqual(after['judgment_policy'], before['judgment_policy'])

    def test_policy_version_is_bound_to_prepared_plan(self):
        prepared = self.write('profile_plan_prepare', context=self.args.context,
                              task='Review the retry design.')
        stored = prepared['profile']['prepared_plans'][prepared['plan']['plan_id']]
        self.assertEqual(stored['judgment_policy'], {key: policy()[key] for key in ('version', 'fingerprint')})

    def test_changed_policy_identity_cannot_inherit_a_prepared_plan_rating(self):
        first = self.write('profile_plan_prepare', context=self.args.context,
                           task='Review the retry design.')
        self.write('profile_outcome', plan_id=first['plan']['plan_id'], source_id='first-rating',
                   rating='helpful', basis='prompt_review')
        changed = copy.deepcopy(policy())
        changed['version'] = 'test-policy-next-version'
        changed['fingerprint'] = '0' * 64
        with patch('planning.policy', return_value=changed):
            second = self.write('profile_plan_prepare', context=self.args.context,
                                task='Review the retry design.')
        self.assertNotEqual(first['plan']['plan_id'], second['plan']['plan_id'])
        rows = {row['plan_id']: row for row in self.call('profile_outcome_summary', context=self.args.context)['plans']}
        self.assertEqual(rows[first['plan']['plan_id']]['outcome']['rating'], 'helpful')
        self.assertIsNone(rows[second['plan']['plan_id']]['outcome'])
        self.assertEqual(rows[second['plan']['plan_id']]['judgment_policy']['fingerprint'], changed['fingerprint'])

    def test_policy_fingerprint_covers_the_complete_prompt_contract(self):
        before = policy()
        altered_contract = policy_text() + '\nA synthetic changed footer for this test.'
        with patch('judgment.policy_text', return_value=altered_contract):
            after = policy()
        self.assertEqual(after['version'], before['version'])
        self.assertEqual(after['principles'], before['principles'])
        self.assertNotEqual(after['fingerprint'], before['fingerprint'])

    def test_plan_identity_also_tracks_prompt_text_changes(self):
        before = self.plan()
        altered_contract = policy_text() + '\nA synthetic host-contract change for this test.'
        with patch('planning.policy_text', return_value=altered_contract):
            after = self.plan()
        self.assertEqual(after['judgment_policy']['fingerprint'], before['judgment_policy']['fingerprint'])
        self.assertNotEqual(after['personalized_prompt'], before['personalized_prompt'])
        self.assertNotEqual(after['plan_id'], before['plan_id'])

    def test_mcp_initialization_carries_the_same_contract(self):
        request = {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize',
                   'params': {'protocolVersion': '2024-11-05', 'capabilities': {},
                              'clientInfo': {'name': 'judgment-acceptance', 'version': '1'}}}
        result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'host.py'),
                                 '--root', self.args.root, '--subject', self.args.subject, 'mcp'],
                                input=json.dumps(request) + '\n', text=True, capture_output=True,
                                encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        reply = json.loads(result.stdout)
        self.assertEqual(reply['id'], 1)
        self.assertIn(policy_text(), reply['result']['instructions'])

    def test_fixture_has_paired_languages_corrections_and_no_invented_scores(self):
        data = json.loads((ROOT / 'examples' / 'judgment-evaluation' / 'cases.json').read_text(encoding='utf-8'))
        self.assertIsNone(data['results'])
        self.assertEqual(len(data['cases']), 14)
        self.assertEqual(len({case['id'] for case in data['cases']}), 14)
        self.assertIn('incorrect', {case['initial_correctness'] for case in data['cases']})
        self.assertIn('correct', {case['initial_correctness'] for case in data['cases']})
        for case in data['cases']:
            with self.subTest(case=case['id']):
                self.assertEqual(set(case['variants']), {'en', 'zh-CN'})
                for variant in case['variants'].values():
                    self.assertTrue(variant['initial_context'])
                    self.assertTrue(variant['user_message'])
                self.assertTrue(case['rubric']['must'])
                self.assertTrue(case['rubric']['must_not'])


if __name__ == '__main__':
    unittest.main()
