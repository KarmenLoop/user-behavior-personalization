"""Behavioral evidence tests use synthetic signals and a controlled clock."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import host
import learning
from host_support import Database, Problem

NOW = dt.datetime(2026, 11, 3, 12, tzinfo=dt.timezone.utc)


class LearningTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / 'private'
        self.args = SimpleNamespace(root=str(self.root), subject='alice', enable_observations=True)
        self.clock = patch('learning.now_utc', return_value=NOW)
        self.clock.start()
        self.stamps = patch('host.stamp', return_value=NOW.isoformat())
        self.stamps.start()

    def tearDown(self):
        self.stamps.stop()
        self.clock.stop()
        self.tmp.cleanup()

    def call(self, name, **values):
        return host.dispatch(name, values, self.args)

    def revision(self):
        return self.call('profile_read', context='writing')['revision']

    def event(self, i, **updates):
        value = {'id': 'event-' + str(i), 'source_id': 'message-' + str(i), 'session_id': 'session-' + str(i), 'context': 'writing', 'dimension': 'response_length', 'value': 'concise', 'signal': 'positive', 'occurred_at': (NOW - dt.timedelta(days=1)).isoformat()}
        value.update(updates)
        return value

    def observe(self, i, **updates):
        return self.call('profile_observe', expected_revision=self.revision(), event=self.event(i, **updates))

    def candidate(self, value='concise'):
        return next(c for c in self.call('profile_insights', context='writing')['candidates'] if c['value'] == value)

    def three(self):
        for i in range(3):
            self.observe(i)
        return self.candidate()

    def accept(self):
        candidate = self.candidate()
        return self.call('profile_review', expected_revision=self.revision(), candidate_id=candidate['candidate_id'], decision='accept', source_id='user-confirmation')

    def rule(self, **updates):
        rule = {'id': 'short', 'statement': 'Keep it brief.', 'scope': 'writing', 'source_id': 'explicit-1', 'source_summary': 'The user requested concise writing.', 'kind': 'explicit'}
        rule.update(updates)
        return rule

    def correct(self, **updates):
        return self.call('profile_correct', expected_revision=self.revision(), rule=self.rule(**updates))

    def error(self, code, name, **values):
        with self.assertRaises(Problem) as caught:
            self.call(name, **values)
        self.assertEqual(caught.exception.code, code)

    def test_observations_need_owner_opt_in(self):
        self.args.enable_observations = False
        self.error('OBSERVATIONS_DISABLED', 'profile_observe', expected_revision=0, event=self.event(1))
        self.assertEqual(self.revision(), 0)

    def test_three_sessions_propose_but_never_apply_without_review(self):
        candidate = self.three()
        self.assertEqual(candidate['status'], 'ready_to_review')
        self.assertEqual(candidate['supporting_sessions'], 3)
        self.assertEqual(self.call('profile_read', context='writing')['rules'], [])
        accepted = self.accept()
        self.assertEqual(accepted['profile']['revision'], 4)
        rules = self.call('profile_read', context='writing')['rules']
        self.assertEqual(rules[0]['value'], 'concise')
        self.assertEqual(rules[0]['evidence_ids'], ['event-0', 'event-1', 'event-2'])
        self.assertEqual(self.candidate()['status'], 'confirmed_preference_exists')

    def test_replays_do_not_increase_support_or_revision(self):
        self.observe(1)
        result = self.observe(1)
        self.assertTrue(result['replayed'])
        self.assertEqual(self.revision(), 1)
        self.assertEqual(self.candidate()['supporting_sessions'], 1)
        self.error('SOURCE_CONFLICT', 'profile_observe', expected_revision=1, event=self.event(1, value='detailed'))

    def test_new_source_cannot_overwrite_observation_id(self):
        self.observe(1)
        self.error('OBSERVATION_CONFLICT', 'profile_observe', expected_revision=1, event=self.event(1, source_id='different-source'))

    def test_repeated_same_session_cannot_manufacture_threshold(self):
        for i in range(6):
            self.observe(i, session_id='same-session', occurred_at=(NOW - dt.timedelta(minutes=6-i)).isoformat())
        candidate = self.candidate()
        self.assertEqual(candidate['supporting_sessions'], 1)
        self.assertEqual(candidate['status'], 'insufficient_evidence')
        self.assertEqual(candidate['source_event_ids'], ['event-5'])

    def test_latest_same_session_negative_replaces_positive(self):
        self.observe(1, session_id='same')
        self.observe(2, session_id='same', signal='negative', occurred_at=NOW.isoformat())
        self.assertEqual(self.call('profile_insights', context='writing')['candidates'], [])

    def test_conflicting_feedback_is_visible(self):
        self.three()
        self.observe(3, value='detailed')
        self.observe(4, value='detailed')
        candidate = self.candidate()
        self.assertEqual(candidate['status'], 'conflicted')
        self.assertEqual(candidate['opposing_sessions'], 2)
        self.assertAlmostEqual(candidate['score'], .6)
        self.error('CANDIDATE_NOT_READY', 'profile_review', expected_revision=5, candidate_id=candidate['candidate_id'], decision='accept', source_id='review')

    def test_negative_feedback_counts_against_only_its_value(self):
        self.three()
        self.observe(3, signal='negative')
        self.observe(4, signal='negative')
        self.assertEqual(self.candidate()['status'], 'conflicted')
        self.assertEqual(self.candidate()['opposing_sessions'], 2)

    def test_recency_decay_reduces_old_preference_weight(self):
        for i in range(3):
            self.observe(i, occurred_at=(NOW - dt.timedelta(days=60)).isoformat())
        self.observe(3, value='detailed', occurred_at=NOW.isoformat())
        candidate = self.candidate()
        self.assertAlmostEqual(candidate['weighted_support'], .75)
        self.assertEqual(candidate['status'], 'insufficient_evidence')
        self.assertLess(candidate['score'], .5)
        self.assertEqual(self.call('profile_insights', context='writing')['confidence_kind'], 'heuristic_not_probability')

    def test_old_evidence_excluded_and_future_rejected(self):
        for i in range(3):
            self.observe(i, occurred_at=(NOW - dt.timedelta(days=91)).isoformat())
        self.assertEqual(self.call('profile_insights', context='writing')['candidates'], [])
        self.error('FUTURE_OBSERVATION', 'profile_observe', expected_revision=3, event=self.event(4, occurred_at=(NOW + dt.timedelta(minutes=6)).isoformat()))

    def test_candidates_change_when_evidence_changes(self):
        before = self.three()
        self.observe(3)
        self.error('CANDIDATE_STALE', 'profile_review', expected_revision=4, candidate_id=before['candidate_id'], decision='accept', source_id='review')
        self.error('STALE_REVISION', 'profile_review', expected_revision=3, candidate_id=self.candidate()['candidate_id'], decision='accept', source_id='review')

    def test_rejected_candidate_hidden_until_new_evidence(self):
        candidate = self.three()
        self.call('profile_review', expected_revision=3, candidate_id=candidate['candidate_id'], decision='reject', source_id='user-rejection')
        self.assertEqual(self.call('profile_insights', context='writing')['candidates'], [])
        self.assertEqual(self.call('profile_read', context='writing')['rules'], [])
        self.observe(3)
        self.assertNotEqual(self.candidate()['candidate_id'], candidate['candidate_id'])

    def test_explicit_typed_preference_prevents_behavior_override(self):
        self.three()
        self.correct(dimension='response_length', value='detailed')
        self.assertEqual(self.candidate()['status'], 'confirmed_preference_exists')
        self.assertEqual(self.call('profile_read', context='writing')['rules'][0]['value'], 'detailed')

    def test_typed_specific_rule_overrides_global_rule_only_in_context(self):
        self.correct(scope='*', dimension='response_length', value='detailed')
        self.correct(id='brief-writing', source_id='explicit-2', dimension='response_length', value='concise')
        self.assertEqual([r['value'] for r in self.call('profile_read', context='Writing')['rules']], ['concise'])
        self.assertEqual([r['value'] for r in self.call('profile_read', context='coding')['rules']], ['detailed'])

    def test_context_match_is_exact_not_substring(self):
        self.correct(scope='art')
        self.assertEqual(self.call('profile_read', context='cartography')['rules'], [])
        self.assertEqual(len(self.call('profile_read', context='ART')['rules']), 1)
        self.three()
        self.assertEqual(self.call('profile_insights', context='copywriting')['candidates'], [])

    def test_expiry_compares_instants_not_strings(self):
        future = dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=1)
        shifted = future.astimezone(dt.timezone(dt.timedelta(hours=-8)))
        self.correct(expires_at=shifted.isoformat())
        # Use actual-time relative fixture because recall's active helper is clock-patched.
        with patch('learning.now_utc', return_value=future - dt.timedelta(hours=1)):
            self.assertEqual(len(self.call('profile_read', context='writing')['rules']), 1)
        with patch('learning.now_utc', return_value=future + dt.timedelta(seconds=1)):
            self.assertEqual(self.call('profile_read', context='writing')['rules'], [])

    def test_pause_disables_collection_recall_insights_and_review(self):
        candidate = self.three()
        self.call('profile_pause', expected_revision=3, paused=True)
        self.assertEqual(self.call('profile_insights', context='writing')['candidates'], [])
        self.error('MEMORY_PAUSED', 'profile_observe', expected_revision=4, event=self.event(9))
        self.error('MEMORY_PAUSED', 'profile_review', expected_revision=4, candidate_id=candidate['candidate_id'], decision='accept', source_id='review')
        self.assertEqual(len(self.call('profile_export')['profile']['observations']), 3)
        self.call('profile_forget_observations', expected_revision=4, observation_ids=['event-0'])

    def test_subject_isolation_for_rules_and_evidence(self):
        self.three()
        self.accept()
        self.args.subject = 'bob'
        self.assertEqual(self.call('profile_insights', context='writing')['candidates'], [])
        self.assertEqual(self.call('profile_read', context='writing')['rules'], [])
        self.assertEqual(self.revision(), 0)

    def test_forgetting_reviewed_rule_erases_dependencies_and_blocks_replay(self):
        self.three()
        accepted = self.accept()
        path = Path(self.call('profile_export')['path'])
        result = self.call('profile_forget', expected_revision=4, rule_id=accepted['rule_id'])
        self.assertFalse(path.exists())
        self.assertEqual(result['profile']['observations'], {})
        self.assertEqual(result['profile']['rules'], {})
        self.assertEqual(result['profile']['history'], [])
        self.error('SOURCE_FORGOTTEN', 'profile_observe', expected_revision=5, event=self.event(0))
        self.error('SOURCE_FORGOTTEN', 'profile_observe', expected_revision=5, event=self.event(99, source_id='message-0'))
        self.error('SOURCE_FORGOTTEN', 'profile_observe', expected_revision=5, event=self.event(0, source_id='new-source'))

    def test_forgetting_event_removes_derived_rule_and_history(self):
        self.three()
        accepted = self.accept()
        self.correct(id=accepted['rule_id'], source_id='correction-after-review', kind='correction')
        result = self.call('profile_forget_observations', expected_revision=5, observation_ids=['event-0'])
        self.assertEqual(result['profile']['rules'], {})
        self.assertEqual(result['profile']['history'], [])
        self.assertEqual(result['profile']['observations'], {})
        self.error('SOURCE_FORGOTTEN', 'profile_correct', expected_revision=6, rule=self.rule(source_id='correction-after-review'))

    def test_reset_purges_all_content_pauses_and_keeps_replay_markers(self):
        self.three()
        self.accept()
        path = Path(self.call('profile_export')['path'])
        result = self.call('profile_reset', expected_revision=4)['profile']
        self.assertTrue(result['paused'])
        self.assertEqual(result['rules'], {})
        self.assertEqual(result['observations'], {})
        self.assertEqual(len(result['deleted_source_hashes']), 4)
        self.assertFalse(path.exists())
        self.call('profile_pause', expected_revision=5, paused=False)
        self.error('SOURCE_FORGOTTEN', 'profile_observe', expected_revision=6, event=self.event(0))

    def test_forgetting_replacement_id_also_purges_old_learned_evidence(self):
        self.three()
        accepted = self.accept()
        self.correct(id='new-explicit-id', dimension='response_length', value='detailed')
        self.assertNotIn(accepted['rule_id'], self.call('profile_export')['profile']['rules'])
        result = self.call('profile_forget', expected_revision=5, rule_id='new-explicit-id')['profile']
        self.assertEqual(result['rules'], {})
        self.assertEqual(result['observations'], {})
        self.assertEqual(result['history'], [])
        self.assertEqual(self.call('profile_insights', context='writing')['candidates'], [])

    def test_forgetting_rule_purges_shadowed_session_evidence(self):
        for i in range(3):
            self.observe(i, session_id='session-' + str(i), occurred_at=(NOW - dt.timedelta(days=2)).isoformat())
            self.observe(i + 3, session_id='session-' + str(i), occurred_at=(NOW - dt.timedelta(days=1)).isoformat())
        self.observe(20, context='coding')
        self.observe(21, dimension='language', value='en')
        self.assertEqual(self.candidate()['source_event_ids'], ['event-3', 'event-4', 'event-5'])
        accepted = self.accept()
        result = self.call('profile_forget', expected_revision=9, rule_id=accepted['rule_id'])['profile']
        self.assertEqual(set(result['observations']), {'event-20', 'event-21'})
        self.assertEqual(result['rules'], {})
        self.assertEqual(result['history'], [])
        self.assertFalse(any(c['dimension'] == 'response_length' for c in self.call('profile_insights', context='writing')['candidates']))
        for i in range(6):
            self.error('SOURCE_FORGOTTEN', 'profile_observe', expected_revision=10, event=self.event(i + 100, source_id='message-' + str(i)))
            self.error('SOURCE_FORGOTTEN', 'profile_observe', expected_revision=10, event=self.event(i, source_id='new-source-' + str(i)))

    def test_forgetting_typed_explicit_rule_purges_older_observations(self):
        self.three()
        self.correct(dimension='response_length', value='detailed')
        result = self.call('profile_forget', expected_revision=4, rule_id='short')['profile']
        self.assertEqual(result['observations'], {})
        self.assertEqual(self.call('profile_insights', context='writing')['candidates'], [])
        self.error('SOURCE_FORGOTTEN', 'profile_observe', expected_revision=5, event=self.event(99, source_id='message-0'))

    def test_forgetting_global_typed_rule_purges_dimension_across_contexts(self):
        self.observe(1)
        self.observe(2, context='coding')
        self.observe(3, dimension='language', value='en')
        self.correct(scope='*', dimension='response_length', value='concise')
        result = self.call('profile_forget', expected_revision=4, rule_id='short')['profile']
        self.assertEqual(set(result['observations']), {'event-3'})

    def test_forgetting_linked_event_purges_shadowed_same_dimension_only(self):
        for i in range(3):
            self.observe(i, session_id='session-' + str(i), occurred_at=(NOW - dt.timedelta(days=2)).isoformat())
            self.observe(i + 3, session_id='session-' + str(i), occurred_at=(NOW - dt.timedelta(days=1)).isoformat())
        self.accept()
        self.observe(20, context='coding')
        result = self.call('profile_forget_observations', expected_revision=8, observation_ids=['event-3'])['profile']
        self.assertEqual(set(result['observations']), {'event-20'})
        self.assertEqual(result['rules'], {})

    def test_forgetting_unlinked_shadow_does_not_remove_unrelated_rule(self):
        self.observe(0, session_id='session-0', occurred_at=(NOW - dt.timedelta(days=2)).isoformat())
        self.observe(1, session_id='session-0')
        self.correct(id='language', dimension='language', value='en')
        result = self.call('profile_forget_observations', expected_revision=3, observation_ids=['event-0'])['profile']
        self.assertEqual(set(result['observations']), {'event-1'})
        self.assertEqual(set(result['rules']), {'language'})

    def test_forgetting_unrelated_event_preserves_rejection(self):
        candidate = self.three()
        self.call('profile_review', expected_revision=3, candidate_id=candidate['candidate_id'], decision='reject', source_id='review-reject')
        self.observe(20, context='coding')
        self.call('profile_forget_observations', expected_revision=5, observation_ids=['event-20'])
        self.assertEqual(self.call('profile_insights', context='writing')['candidates'], [])

    def test_legacy_profile_upgrades_without_dropping_rules(self):
        original = {'subject_id': 'alice', 'revision': 8, 'paused': False, 'rules': {'short': {**self.rule(), 'confirmed_at': NOW.isoformat(), 'source_hash': 'hash'}}, 'source_hashes': {}, 'deleted_source_hashes': [], 'history': [], 'updated_at': NOW.isoformat()}
        db = Database(self.root)
        db.put('profile:alice', original)
        db.close()
        self.assertEqual(self.call('profile_read', context='writing')['rules'][0], original['rules']['short'])
        result = self.observe(1)['profile']
        self.assertEqual(result['revision'], 9)
        self.assertEqual(result['schema_version'], 2)
        self.assertEqual(result['rules'], original['rules'])

    def test_legacy_source_fingerprint_replay_is_compatible(self):
        raw = self.rule()
        original = learning.blank_profile('alice')
        original['revision'] = 2
        original['rules']['short'] = {**raw, 'confirmed_at': NOW.isoformat(), 'source_hash': learning.digest(raw['source_id'])}
        original['source_hashes'][learning.digest(raw['source_id'])] = learning.digest(json.dumps(raw, sort_keys=True))
        for key in ('schema_version', 'observations', 'deleted_observation_hashes', 'dismissed_candidates'):
            del original[key]
        db = Database(self.root)
        db.put('profile:alice', original)
        db.close()
        result = self.call('profile_correct', expected_revision=2, rule=raw)
        self.assertTrue(result['replayed'])
        self.assertEqual(result['profile']['revision'], 2)

    def test_review_rechecks_aging_evidence_at_commit(self):
        candidate = self.three()
        with patch('learning.now_utc', return_value=NOW + dt.timedelta(days=31)):
            self.error('CANDIDATE_NOT_READY', 'profile_review', expected_revision=3, candidate_id=candidate['candidate_id'], decision='accept', source_id='late-review')
        self.assertEqual(self.call('profile_read', context='writing')['rules'], [])

    def test_typed_replacement_at_rule_limit_does_not_require_extra_slot(self):
        db = Database(self.root)
        profile = learning.blank_profile('alice')
        profile['rules'] = {str(i): {**self.rule(id=str(i), source_id='source-' + str(i)), 'source_hash': learning.digest('source-' + str(i))} for i in range(30)}
        profile['rules']['0'].update(dimension='response_length', value='concise')
        db.put('profile:alice', profile)
        db.close()
        result = self.correct(id='typed-replacement', dimension='response_length', value='detailed')['profile']
        self.assertEqual(len(result['rules']), 30)
        self.assertNotIn('0', result['rules'])

    def test_invalid_structured_fields_fail_without_writes(self):
        for change in ({'dimension': 'mental_health'}, {'value': 'diagnosis'}, {'session_id': ' '}, {'context': '*'}, {'occurred_at': '2026-11-03T12:00:00'}, {'raw_chat': 'not accepted'}):
            with self.subTest(change=change), self.assertRaises(Problem):
                self.call('profile_observe', expected_revision=0, event=self.event(1, **change))
        self.assertEqual(self.revision(), 0)
        self.error('INVALID_DIMENSION', 'profile_correct', expected_revision=0, rule=self.rule(dimension='language'))
        self.error('INVALID_INPUT', 'profile_forget_observations', expected_revision=0, observation_ids=[])
        self.error('UNKNOWN_TOOL', 'invented_tool')

    def test_failed_validation_does_not_record_source(self):
        self.error('INVALID_EXPIRY', 'profile_correct', expected_revision=0, rule=self.rule(expires_at='bad'))
        self.correct()
        self.assertEqual(self.revision(), 1)

    def test_observation_limit_preserves_existing_evidence(self):
        db = Database(self.root)
        profile = learning.blank_profile('alice')
        profile['observations'] = {str(i): self.event(i) for i in range(200)}
        db.put('profile:alice', profile)
        db.close()
        self.error('OBSERVATION_LIMIT', 'profile_observe', expected_revision=0, event=self.event(201))
        self.assertEqual(len(self.call('profile_export')['profile']['observations']), 200)

    def test_workflow_next_step_is_only_a_reviewable_suggestion(self):
        for i in range(3):
            self.observe(i, dimension='workflow_next_step', value='test')
        candidate = self.candidate('test')
        self.assertEqual(candidate['status'], 'ready_to_review')
        accepted = self.call('profile_review', expected_revision=3, candidate_id=candidate['candidate_id'], decision='accept', source_id='workflow-review')
        self.assertIn('do not execute it automatically', accepted['profile']['rules'][accepted['rule_id']]['statement'])


if __name__ == '__main__':
    unittest.main()
