"""Persisted conversation learning, exact evidence, deletion, and host authorization."""
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import host
from host_support import Problem


class ConversationStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.args = SimpleNamespace(root=self.base/'private', subject='alice', enable_conversations=True)
        self.now = dt.datetime.now(dt.timezone.utc)-dt.timedelta(days=1)

    def tearDown(self):
        self.tmp.cleanup()

    def conversation(self, session='one'):
        texts = ["For future code reviews, list deployment risks before naming a solution.",
                 'Review this parser implementation for regressions.',
                 'Write tests for the edge cases and invalid inputs.']
        return {'session_id': session, 'context': 'code-review', 'messages': [
            {'id': 'm'+str(i), 'role': 'user', 'text': text, 'at': (self.now+dt.timedelta(minutes=i)).isoformat()}
            for i, text in enumerate(texts)]}

    def read(self, name, values=None):
        return host.dispatch(name, values or {}, self.args)

    def write(self, name, values):
        revision = self.read('profile_read', {'context': 'code-review'})['revision']
        return self.read(name, {'expected_revision': revision, **values})

    def test_open_preference_restarts_and_applies_only_after_review(self):
        result = self.write('conversation_import', {'conversation': self.conversation()})
        self.assertEqual(result['added_messages'], 3)
        portrait = self.read('profile_portrait', {'context': 'code-review'})
        proposal = portrait['pending_preferences'][0]
        self.assertIn('deployment risks', proposal['statement'])
        self.assertEqual(self.read('profile_read', {'context': 'code-review'})['rules'], [])
        accepted = self.write('profile_proposal_review', {'proposal_id': proposal['id'], 'decision': 'accept', 'source_id': 'actual-review-1'})
        command = [sys.executable, '-B', str(ROOT/'scripts/host.py'), '--root', str(self.args.root), '--subject', 'alice', 'call', 'profile_read']
        process = subprocess.run(command, input='{"context":"code-review"}', capture_output=True, text=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)['rules'][0]['id'], accepted['rule_id'])

    def test_opt_in_and_pause_are_server_controls(self):
        self.args.enable_conversations = False
        with self.assertRaisesRegex(Problem, 'operator'):
            self.write('conversation_import', {'conversation': self.conversation()})
        self.args.enable_conversations = True
        self.write('conversation_import', {'conversation': self.conversation()})
        self.write('profile_pause', {'paused': True})
        with self.assertRaises(Problem):
            self.write('conversation_import', {'conversation': self.conversation('two')})
        self.assertEqual(self.read('profile_portrait', {'context': 'code-review'})['writing_observations'], {})
        self.assertEqual(self.read('profile_model_context', {'context': 'code-review'})['excerpts'], [])
        self.assertEqual(self.read('profile_forecast', {'context': 'code-review', 'request': 'Review parser code'})['status'], 'paused')
        self.write('profile_forget_conversation', {'session_id': 'one'})
        self.assertEqual(self.read('profile_export')['profile']['conversation_messages'], {})

    def test_reimport_is_idempotent_changed_source_rejects_atomically(self):
        first = self.write('conversation_import', {'conversation': self.conversation()})
        again = self.write('conversation_import', {'conversation': self.conversation()})
        self.assertTrue(again['replayed'])
        self.assertEqual(again['profile']['revision'], first['profile']['revision'])
        changed = self.conversation()
        changed['messages'][1]['text'] = 'Different source content.'
        with self.assertRaises(Problem):
            self.write('conversation_import', {'conversation': changed})
        self.assertEqual(len(self.read('profile_export')['profile']['conversation_messages']), 3)

    def test_append_keeps_original_history_and_reorder_is_rejected(self):
        conversation = self.conversation()
        self.write('conversation_import', {'conversation': conversation})
        conversation['messages'].append({'id': 'm3', 'role': 'user', 'text': 'Summarize the changes.', 'at': (self.now+dt.timedelta(minutes=4)).isoformat()})
        self.assertEqual(self.write('conversation_import', {'conversation': conversation})['added_messages'], 1)
        conversation['messages'][0]['id'] = 'changed-id'
        with self.assertRaises(Problem):
            self.write('conversation_import', {'conversation': conversation})

    def test_forgetting_rule_cascades_to_source_style_and_blocks_reimport(self):
        self.write('conversation_import', {'conversation': self.conversation()})
        proposal = self.read('profile_portrait', {'context': 'code-review'})['pending_preferences'][0]
        approved = self.write('profile_proposal_review', {'proposal_id': proposal['id'], 'decision': 'accept', 'source_id': 'review'})
        self.write('profile_forget', {'rule_id': approved['rule_id']})
        p = self.read('profile_export')['profile']
        self.assertEqual(len(p['conversation_messages']), 2)
        self.assertEqual(p['conversation_proposals'], {})
        self.assertEqual(p['rules'], {})
        self.assertEqual(self.read('profile_portrait', {'context': 'code-review'})['writing_observations']['message_count'], 2)
        with self.assertRaisesRegex(Problem, 'forgotten'):
            self.write('conversation_import', {'conversation': self.conversation()})

    def test_forgetting_middle_source_never_creates_a_new_transition(self):
        conversation = self.conversation()
        conversation['messages'][0]['text'] = 'Review this parser code.'
        conversation['messages'][1]['text'] = 'For future reviews, preserve the public function names.'
        self.write('conversation_import', {'conversation': conversation})
        proposal = self.read('profile_portrait', {'context': 'code-review'})['pending_preferences'][0]
        approved = self.write('profile_proposal_review', {'proposal_id': proposal['id'], 'decision': 'accept', 'source_id': 'review'})
        self.write('profile_forget', {'rule_id': approved['rule_id']})
        p = self.read('profile_export')['profile']
        self.assertEqual(len(p['conversation_messages']), 2)
        self.assertEqual(p['conversation_transitions'], [])

    def test_model_proposal_exact_sources_quotes_scope_and_review(self):
        self.write('conversation_import', {'conversation': self.conversation()})
        evidence = self.read('profile_model_context', {'context': 'code-review'})['excerpts']
        item = next(x for x in evidence if x['text'].startswith('For future'))
        proposal = {'statement': 'Discuss deployment risks first.', 'scope': 'code-review', 'category': 'workflow', 'evidence': [{'source_key': item['source_key'], 'quote': item['text']}]}
        added = self.write('profile_model_propose', {'proposals': [proposal]})
        self.assertEqual(added['added_proposals'], 1)
        self.assertEqual(self.read('profile_read', {'context': 'code-review'})['rules'], [])
        for invalid in [dict(proposal, scope='other'), dict(proposal, evidence=[{'source_key': 'invented', 'quote': 'made up'}]), dict(proposal, evidence=[{'source_key': item['source_key'], 'quote': 'made up'}])]:
            with self.assertRaises(Problem):
                self.write('profile_model_propose', {'proposals': [invalid]})
        self.write('profile_proposal_review', {'proposal_id': added['proposal_ids'][0], 'decision': 'reject', 'source_id': 'rejection'})
        self.assertTrue(self.write('profile_model_propose', {'proposals': [proposal]})['replayed'])

    def test_direct_middle_message_deletion_keeps_a_real_gap(self):
        conversation = self.conversation()
        self.write('conversation_import', {'conversation': conversation})
        p = self.read('profile_export')['profile']
        middle = next(key for key, message in p['conversation_messages'].items() if message['ordinal'] == 1)
        self.write('profile_forget_messages', {'source_keys': [middle]})
        p = self.read('profile_export')['profile']
        self.assertEqual(len(p['conversation_messages']), 2)
        self.assertEqual(p['conversation_transitions'], [])
        with self.assertRaisesRegex(Problem, 'forgotten'):
            self.write('conversation_import', {'conversation': conversation})

    def test_model_cannot_use_a_quoted_third_party_preference(self):
        conversation = self.conversation()
        conversation['messages'][0]['text'] = 'My colleague said: "I prefer one-word answers."'
        self.write('conversation_import', {'conversation': conversation})
        row = next(x for x in self.read('profile_model_context', {'context': 'code-review'})['excerpts'] if 'colleague' in x['text'])
        item = {'statement': 'Give one-word answers.', 'scope': 'code-review', 'category': 'communication', 'evidence': [{'source_key': row['source_key'], 'quote': 'I prefer one-word answers.'}]}
        with self.assertRaisesRegex(Problem, 'wholly authored'):
            self.write('profile_model_propose', {'proposals': [item]})

    def test_whole_third_party_quote_is_not_user_evidence(self):
        conversation = self.conversation()
        conversation['messages'][0]['text'] = 'My colleague said: "I prefer one-word answers."'
        self.write('conversation_import', {'conversation': conversation})
        row = next(x for x in self.read('profile_model_context', {'context': 'code-review'})['excerpts'] if 'colleague' in x['text'])
        item = {'statement': 'Give one-word answers.', 'scope': 'code-review', 'category': 'communication', 'evidence': [{'source_key': row['source_key'], 'quote': row['text']}]}
        with self.assertRaisesRegex(Problem, 'wholly authored'):
            self.write('profile_model_propose', {'proposals': [item]})

    def test_unquoted_reported_speech_and_examples_are_not_user_evidence(self):
        for number, text in enumerate(['My colleague said I prefer one-word answers.', 'Example: I prefer one-word answers.']):
            conversation = self.conversation('reported-'+str(number))
            conversation['messages'][0]['text'] = text
            self.write('conversation_import', {'conversation': conversation})
            row = next(x for x in self.read('profile_model_context', {'context': 'code-review'})['excerpts'] if x['text'] == text)
            for quote in [text, 'I prefer one-word answers.']:
                item = {'statement': 'Give one-word answers.', 'scope': 'code-review', 'category': 'communication', 'evidence': [{'source_key': row['source_key'], 'quote': quote}]}
                with self.assertRaisesRegex(Problem, 'Reported speech'):
                    self.write('profile_model_propose', {'proposals': [item]})

    def test_ignored_role_cannot_be_rewritten_as_user_evidence(self):
        conversation = self.conversation()
        conversation['messages'][0]['role'] = 'assistant'
        self.write('conversation_import', {'conversation': conversation})
        conversation['messages'][0]['role'] = 'user'
        with self.assertRaisesRegex(Problem, 'immutable'):
            self.write('conversation_import', {'conversation': conversation})
        self.assertEqual(self.read('profile_portrait', {'context': 'code-review'})['pending_preferences'], [])

    def test_relabeling_deleted_middle_source_cannot_reconnect_edges(self):
        conversation = self.conversation()
        self.write('conversation_import', {'conversation': conversation})
        p = self.read('profile_export')['profile']
        middle = next(key for key, message in p['conversation_messages'].items() if message['ordinal'] == 1)
        self.write('profile_forget_messages', {'source_keys': [middle]})
        conversation['messages'][1]['role'] = 'assistant'
        conversation['messages'].append({'id': 'later', 'role': 'user', 'text': 'Summarize changes.', 'at': (self.now+dt.timedelta(minutes=5)).isoformat()})
        with self.assertRaisesRegex(Problem, 'forgotten'):
            self.write('conversation_import', {'conversation': conversation})
        self.assertEqual(self.read('profile_export')['profile']['conversation_transitions'], [])

    def test_subject_context_isolation_and_reset(self):
        self.write('conversation_import', {'conversation': self.conversation()})
        self.assertEqual(self.read('profile_portrait', {'context': 'other'})['writing_observations']['message_count'], 0)
        self.args.subject = 'bob'
        self.assertEqual(self.read('profile_portrait', {'context': 'code-review'})['writing_observations']['message_count'], 0)
        self.args.subject = 'alice'
        self.write('profile_reset', {})
        p = self.read('profile_export')['profile']
        for name in ['conversation_messages', 'conversation_proposals', 'conversation_transitions', 'conversation_sessions']:
            self.assertFalse(p[name])
        self.write('profile_pause', {'paused': False})
        with self.assertRaises(Problem):
            self.write('conversation_import', {'conversation': self.conversation()})

    def test_command_imports_selected_file_without_auto_confirming(self):
        source = self.base/'conversation.json'
        source.write_text(json.dumps(self.conversation()))
        result = subprocess.run([sys.executable, '-B', str(ROOT/'scripts/learn_conversation.py'), '--root', str(self.args.root), '--subject', 'alice', '--input', str(source), '--enable-conversations'], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        value = json.loads(result.stdout)
        self.assertEqual(value['import']['added_messages'], 3)
        self.assertEqual(value['portrait']['confirmed_preferences'], [])
        self.assertTrue(value['portrait']['pending_preferences'])


if __name__ == '__main__':
    unittest.main()
