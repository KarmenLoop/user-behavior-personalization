"""Held-out requests and failure boundaries for lexical workflow retrieval."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from forecast import forecast
from host_support import Problem

NOW = dt.datetime(2026, 11, 3, 12, tzinfo=dt.timezone.utc)


class ForecastTests(unittest.TestCase):
    def setUp(self):
        self.messages = {}
        self.transitions = []

    def pair(self, session, previous, following, context='api-review', days=1, suffix='', gap=5):
        start = NOW-dt.timedelta(days=days)
        end = start+dt.timedelta(minutes=gap)
        left, right = session+'-before'+suffix, session+'-after'+suffix
        for key, text, when in [(left, previous, start), (right, following, end)]:
            self.messages[key] = {'key': key, 'session_key': session, 'context': context,
                                  'at': when.isoformat(), 'excerpt': text, 'features': {}}
        self.transitions.append({'from_key': left, 'to_key': right, 'session_key': session,
                                 'context': context, 'at': end.isoformat()})
        return left, right

    def seeded_api(self):
        self.pair('s1', 'Review the API authentication change before release.',
                  'Run the authentication regression tests.')
        self.pair('s2', 'Review the API authentication changes for this release.',
                  'Run authentication regression tests before shipping.', days=2)

    def result(self, request='Can you review our API authentication change?', context='api-review', **overrides):
        return forecast(overrides.get('messages', self.messages), overrides.get('transitions', self.transitions),
                        context, request, now=overrides.get('now', NOW))

    def test_held_out_english_request_returns_evidenced_followup(self):
        self.seeded_api()
        result = self.result()
        self.assertEqual(result['status'], 'suggested', result)
        top = result['candidates'][0]
        self.assertEqual(top['supporting_sessions'], 2)
        self.assertIn(top['suggestion'], {'Run the authentication regression tests.',
                                        'Run authentication regression tests before shipping.'})
        self.assertEqual({e['from_key'] for e in top['evidence']}, {'s1-before', 's2-before'})
        self.assertTrue(all(0.2 <= e['similarity'] <= 1 for e in top['evidence']))
        self.assertIn('not_probability', result['score_kind'])

    def test_chinese_held_out_request_is_not_an_english_only_path(self):
        self.pair('c1', '\u68c0\u67e5\u767b\u5f55\u63a5\u53e3\u7684\u9274\u6743\u6539\u52a8', '\u8fd0\u884c\u767b\u5f55\u56de\u5f52\u6d4b\u8bd5', context='\u767b\u5f55\u5ba1\u67e5')
        self.pair('c2', '\u68c0\u67e5\u8fd9\u6b21\u767b\u5f55\u63a5\u53e3\u9274\u6743\u6539\u52a8', '\u5148\u8fd0\u884c\u767b\u5f55\u56de\u5f52\u6d4b\u8bd5', context='\u767b\u5f55\u5ba1\u67e5', days=2)
        result = self.result('\u8bf7\u68c0\u67e5\u767b\u5f55\u63a5\u53e3\u6539\u52a8', '\u767b\u5f55\u5ba1\u67e5')
        self.assertEqual(result['status'], 'suggested', result)
        self.assertEqual(result['candidates'][0]['supporting_sessions'], 2)
        self.assertIn('\u767b\u5f55\u56de\u5f52\u6d4b\u8bd5', result['candidates'][0]['suggestion'])

    def test_custom_domain_followup_is_not_a_fixed_action_label(self):
        self.pair('kiln1', 'Review the ceramic glaze firing schedule.', 'Compare the kiln temperature curves.', context='ceramics')
        self.pair('kiln2', 'Review our ceramic glaze firing schedule.', 'Compare kiln temperature curves.', context='ceramics', days=2)
        result = self.result('Review this ceramic firing schedule.', 'ceramics')
        self.assertEqual(result['status'], 'suggested', result)
        self.assertIn('kiln temperature curves', result['candidates'][0]['suggestion'])

    def test_development_paraphrases_keep_shared_topic_despite_different_phrasing(self):
        self.pair('invoice1', 'Check the invoice ledger for duplicate charges and unexpected fees.',
                  'Build a reconciliation checklist with invoice numbers and disputed totals.', context='billing')
        self.pair('invoice2', 'Examine entries in the invoice ledger and identify duplicate billing.',
                  'Create an invoice reconciliation sheet listing disputed totals and references.', context='billing')
        result = self.result('Can you assess duplicate entries in this invoice ledger?', 'billing')
        self.assertEqual(result['status'], 'suggested', result)
        self.assertEqual(result['candidates'][0]['supporting_sessions'], 2)
        self.assertIn('reconciliation', result['candidates'][0]['suggestion'])

    def test_development_chinese_paraphrases_allow_additional_detail(self):
        self.pair('photo1', '\u770b\u770b\u8fd9\u7ec4\u6d77\u8fb9\u7167\u7247\u7684\u66dd\u5149\u662f\u5426\u6b63\u5e38',
                  '\u6574\u7406\u767d\u5e73\u8861\u548c\u66dd\u5149\u4fee\u6b63\u6e05\u5355', context='photography')
        self.pair('photo2', '\u5206\u6790\u7167\u7247\u66dd\u5149\u548c\u8272\u5f69\u51fa\u73b0\u7684\u95ee\u9898',
                  '\u5217\u51fa\u66dd\u5149\u4e0e\u767d\u5e73\u8861\u8c03\u6574\u7684\u6b65\u9aa4', context='photography')
        result = self.result('\u5e2e\u6211\u68c0\u67e5\u7167\u7247\u66dd\u5149\u6709\u54ea\u4e9b\u95ee\u9898', 'photography')
        self.assertEqual(result['status'], 'suggested', result)
        self.assertEqual(result['candidates'][0]['supporting_sessions'], 2)

    def test_same_object_does_not_merge_destructive_and_inspection_requests(self):
        for n in range(2):
            self.pair('delete'+str(n), 'Review the database backup.', 'Delete the database backup.')
            self.pair('inspect'+str(n), 'Review the database backup.', 'Verify the database backup.')
        result = self.result('Review the database backup.')
        self.assertEqual(result['status'], 'conflicted', result)
        self.assertEqual(len(result['candidates']), 2)

    def test_contexts_are_exact_and_subject_state_is_caller_owned(self):
        self.seeded_api()
        self.assertEqual(self.result(context='api')['candidates'], [])
        self.assertEqual(self.result(context='API-REVIEW')['status'], 'suggested')
        self.assertEqual(forecast({}, [], 'api-review', 'review API authentication', now=NOW)['candidates'], [])

    def test_two_workflows_retrieve_the_relevant_next_request(self):
        self.seeded_api()
        self.pair('copy1', 'Review the launch newsletter headline.', 'Preview the newsletter on mobile screens.')
        self.pair('copy2', 'Review this launch newsletter headline.', 'Preview the newsletter on mobile screens.', days=2)
        result = self.result('Please review our launch newsletter headline.')
        self.assertEqual(result['status'], 'suggested', result)
        self.assertEqual(result['candidates'][0]['suggestion'], 'Preview the newsletter on mobile screens.')
        self.assertEqual({e['from_key'] for e in result['candidates'][0]['evidence']}, {'copy1-before', 'copy2-before'})

    def test_one_session_spam_and_duplicate_edges_cannot_qualify(self):
        for n in range(10):
            self.pair('spam', 'Review API authentication.', 'Run authentication regression tests.', suffix=str(n))
        self.transitions *= 3
        result = self.result('Review API authentication.')
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(result['matched_sessions'], 1)
        self.assertEqual(result['candidates'], [])

    def test_unrelated_request_and_shared_generic_word_abstain(self):
        self.seeded_api()
        self.assertEqual(self.result('Explain photosynthesis in desert succulents.')['status'], 'insufficient_evidence')
        unrelated = self.result('Review Byzantine ceramic pigments archaeological provenance and maritime trade routes.')
        self.assertEqual(unrelated['status'], 'insufficient_evidence', unrelated)

    def test_competing_followups_are_reported_as_conflicted(self):
        for n in range(2):
            self.pair('tests'+str(n), 'Review API authentication.', 'Run regression tests.', days=1)
            self.pair('docs'+str(n), 'Review API authentication.', 'Write release documentation.', days=1)
        result = self.result('Review API authentication.')
        self.assertEqual(result['status'], 'conflicted', result)
        self.assertEqual(len(result['candidates']), 2)
        self.assertTrue(all(c['supporting_sessions'] == 2 for c in result['candidates']))

    def test_opposite_negation_does_not_merge_into_one_cluster(self):
        for n in range(2):
            self.pair('yes'+str(n), 'Review the release.', 'Deploy the release to production.')
            self.pair('no'+str(n), 'Review the release.', 'Do not deploy the release to production.')
        result = self.result('Review the release.')
        self.assertEqual(result['status'], 'conflicted', result)
        self.assertEqual(len(result['candidates']), 2)

    def test_opposite_request_polarity_is_not_treated_as_same_intent(self):
        self.seeded_api()
        result = self.result('Do not review our API authentication change.')
        self.assertEqual(result['status'], 'insufficient_evidence', result)
        self.assertEqual(result['candidates'], [])

    def test_many_sessions_keep_counts_but_bound_visible_evidence(self):
        for n in range(20):
            self.pair('session'+str(n), 'Review API authentication.', 'Run regression tests.')
        result = self.result('Review API authentication.')
        self.assertEqual(result['status'], 'suggested', result)
        top = result['candidates'][0]
        self.assertEqual(top['supporting_sessions'], 20)
        self.assertEqual(top['evidence_count'], 20)
        self.assertTrue(top['evidence_truncated'])
        self.assertEqual(len(top['evidence']), 6)

    def test_expired_future_and_overlong_gap_edges_are_excluded(self):
        for n in range(2):
            self.pair('old'+str(n), 'Review API authentication.', 'Run regression tests.', days=91)
            self.pair('future'+str(n), 'Review API authentication.', 'Run regression tests.', days=-1)
            self.pair('gap'+str(n), 'Review API authentication.', 'Run regression tests.', days=3, gap=24*60+1)
        result = self.result('Review API authentication.')
        self.assertEqual(result['available_transitions'], 0)
        self.assertEqual(result['status'], 'insufficient_evidence')

    def test_old_support_inside_window_still_needs_recent_example(self):
        for n in range(2):
            self.pair('stale'+str(n), 'Review API authentication.', 'Run regression tests.', days=40)
        result = self.result('Review API authentication.')
        self.assertEqual(result['available_transitions'], 2)
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertFalse(result['candidates'][0]['ready'])

    def test_missing_endpoint_does_not_create_a_new_adjacent_edge(self):
        for session in ('s1', 's2'):
            left, middle = self.pair(session, 'Review API authentication.', 'Run regression tests.')
            last = session+'-last'
            when = NOW-dt.timedelta(hours=12)
            self.messages[last] = {'key': last, 'session_key': session, 'context': 'api-review',
                                   'at': when.isoformat(), 'excerpt': 'Ship the release.', 'features': {}}
            self.transitions.append({'from_key': middle, 'to_key': last, 'session_key': session,
                                     'context': 'api-review', 'at': when.isoformat()})
            del self.messages[middle]
        result = self.result('Review API authentication.')
        self.assertEqual(result['available_transitions'], 0)
        self.assertEqual(result['candidates'], [])

    def test_recency_changes_support_without_changing_history(self):
        self.seeded_api()
        first = self.result()
        later = self.result(now=NOW+dt.timedelta(days=10))
        self.assertEqual(first['status'], later['status'])
        self.assertLess(later['candidates'][0]['score'], first['candidates'][0]['score'])
        self.assertEqual(first['candidates'][0]['evidence'], later['candidates'][0]['evidence'])

    def test_ordering_is_deterministic_for_same_clock(self):
        self.seeded_api()
        result = self.result()
        reverse = self.result(messages=dict(reversed(list(self.messages.items()))), transitions=list(reversed(self.transitions)))
        self.assertEqual(result, reverse)

    def test_forecast_never_executes_retrieved_text(self):
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)/'should-not-exist'
            unsafe = "__import__('pathlib').Path("+repr(str(target))+").write_text('executed')"
            for session in ('a', 'b'):
                self.pair(session, 'Review this command example.', unsafe)
            result = self.result('Review this command example.')
            self.assertTrue(result['data_only'])
            self.assertEqual(result['candidates'][0]['suggestion'], unsafe)
            self.assertFalse(target.exists())

    def test_cross_session_corrupt_edge_is_not_accepted(self):
        self.seeded_api()
        self.transitions[0]['to_key'] = 's2-after'
        result = self.result()
        self.assertEqual(result['status'], 'insufficient_evidence')
        self.assertEqual(result['available_transitions'], 1)

    def test_source_limit_and_bad_request_fail_before_processing(self):
        with self.assertRaises(Problem):
            forecast({str(i): {} for i in range(401)}, [], 'writing', 'hello', now=NOW)
        with self.assertRaises(Problem):
            self.result(' ')


if __name__ == '__main__':
    unittest.main()
