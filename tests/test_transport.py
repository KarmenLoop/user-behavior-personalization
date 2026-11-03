"""Exercise transport, storage boundaries, and actual subprocess entry points."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from host_support import Database, Problem, atomic, install
from build_context import context_payload
from types import SimpleNamespace


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.private = self.base / 'private'
        self.workspace = self.base / 'workspace'
        self.workspace.mkdir()
        self.argv = [sys.executable, '-B', str(ROOT / 'scripts/host.py'),
                     '--root', str(self.private), '--subject', 'alice',
                     '--workspace', str(self.workspace)]

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, tool, data):
        result = subprocess.run(self.argv + ['call', tool], input=json.dumps(data),
                                text=True, capture_output=True, timeout=20)
        return result.returncode, json.loads(result.stdout or result.stderr)

    def rule(self, source='s1'):
        return {'id': 'brief', 'statement': 'Use concise answers.', 'scope': 'writing',
                'source_id': source, 'source_summary': 'Synthetic user request.', 'kind': 'explicit'}

    def test_real_mcp_initialization_list_validation_and_call(self):
        requests = [
            {'jsonrpc': '2.0', 'id': 1, 'method': 'initialize', 'params': {'protocolVersion': '2025-03-26'}},
            {'jsonrpc': '2.0', 'method': 'notifications/initialized'},
            {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/list'},
            {'jsonrpc': '2.0', 'id': 3, 'method': 'tools/call', 'params': {'name': 'profile_read', 'arguments': {'context': 'writing'}}},
            {'jsonrpc': '2.0', 'id': 4, 'method': 'tools/call', 'params': {'name': 'profile_read', 'arguments': {'context': 'writing', 'subject': 'bob'}}},
            {'jsonrpc': '2.0', 'id': 5, 'method': 'ping'},
        ]
        result = subprocess.run(self.argv + ['mcp'], input=''.join(json.dumps(x)+'\n' for x in requests),
                                text=True, capture_output=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        replies = {x['id']: x for x in map(json.loads, result.stdout.splitlines())}
        self.assertEqual(len(replies), 5)
        self.assertEqual(replies[1]['result']['protocolVersion'], '2025-03-26')
        self.assertIn('profile_read', {x['name'] for x in replies[2]['result']['tools']})
        self.assertEqual(replies[3]['result']['structuredContent']['subject_id'], 'alice')
        self.assertIn('error', replies[4])
        self.assertEqual(replies[5]['result'], {})

    def test_concurrent_writers_cannot_overwrite_same_revision(self):
        self.call('profile_read', {'context': 'writing'})
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda source: self.call('profile_correct', {
                'expected_revision': 0, 'rule': self.rule(source)}), ['s1', 's2']))
        self.assertEqual(sorted(x[0] for x in results), [0, 2])
        self.assertEqual(next(x[1]['code'] for x in results if x[0]), 'STALE_REVISION')
        self.assertEqual(self.call('profile_read', {'context': 'writing'})[1]['revision'], 1)

    def test_private_database_and_atomic_file_permissions(self):
        self.call('profile_correct', {'expected_revision': 0, 'rule': self.rule()})
        code, exported = self.call('profile_export', {})
        self.assertEqual(code, 0)
        if os.name == 'posix':
            self.assertEqual(self.private.stat().st_mode & 0o777, 0o700)
            self.assertEqual((self.private/'host.sqlite').stat().st_mode & 0o777, 0o600)
            self.assertEqual(Path(exported['path']).stat().st_mode & 0o777, 0o600)

    @unittest.skipUnless(os.name == 'posix', 'Symbolic link creation needs platform privileges.')
    def test_symbolic_link_database_and_export_are_refused(self):
        self.private.mkdir()
        other = self.base/'unrelated.sqlite'
        conn = sqlite3.connect(other)
        conn.execute('create table keep(value text)')
        conn.close()
        digest = hashlib.sha256(other.read_bytes()).hexdigest()
        (self.private/'host.sqlite').symlink_to(other)
        code, result = self.call('profile_read', {'context': 'writing'})
        self.assertEqual((code, result['code']), (2, 'UNSAFE_PATH'))
        self.assertEqual(hashlib.sha256(other.read_bytes()).hexdigest(), digest)
        destination = self.base/'linked-export.json'
        destination.symlink_to(other)
        with self.assertRaises(Problem):
            atomic(destination, 'do not write')
        self.assertEqual(hashlib.sha256(other.read_bytes()).hexdigest(), digest)

    def test_missing_subject_install_does_not_modify_workspace(self):
        argv = self.argv[:]
        index = argv.index('--subject')
        del argv[index:index+2]
        result = subprocess.run(argv + ['--install-host', 'codex', 'install'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.workspace/'.codex').exists())

    def test_install_resolves_quoted_tilde_and_rejects_public_data_root(self):
        args = SimpleNamespace(workspace=self.workspace, root='~/personalization-private',
                               subject='alice', install_host='cursor', enable_observations=False)
        original_expanduser = Path.expanduser
        with mock.patch('pathlib.Path.expanduser', autospec=True,
                        side_effect=lambda path: self.private if path.as_posix() == '~/personalization-private' else original_expanduser(path)):
            installed = install(args, 'profile', ROOT/'scripts/host.py')
        entry = json.loads(Path(installed['config']).read_text())['mcpServers']['profile']
        self.assertEqual(entry['args'][entry['args'].index('--root')+1], str(self.private.resolve()))
        args.root = ROOT/'would-leak-profile'
        before = Path(installed['config']).read_bytes()
        with self.assertRaises(Problem):
            install(args, 'second', ROOT/'scripts/host.py')
        self.assertEqual(Path(installed['config']).read_bytes(), before)

    def test_both_host_configs_preserve_other_servers_and_opt_in(self):
        import tomllib
        for host in ('codex', 'cursor'):
            result = subprocess.run(self.argv + ['--enable-observations', '--install-host', host, 'install'], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        config = tomllib.loads((self.workspace/'.codex/config.toml').read_text())
        codex = config['mcp_servers']['user_behavior_personalization']
        cursor = json.loads((self.workspace/'.cursor/mcp.json').read_text())['mcpServers']['user_behavior_personalization']
        for entry in (codex, cursor):
            self.assertIn('--enable-observations', entry['args'])
            self.assertEqual(entry['args'][entry['args'].index('--subject')+1], 'alice')
        before = (self.workspace/'.cursor/mcp.json').read_bytes()
        repeat = subprocess.run(self.argv + ['--install-host', 'cursor', 'install'], capture_output=True)
        self.assertEqual(repeat.returncode, 2)
        self.assertEqual((self.workspace/'.cursor/mcp.json').read_bytes(), before)

    def test_model_payload_uses_only_confirmed_context_and_honors_pause(self):
        self.call('profile_correct', {'expected_revision': 0, 'rule': self.rule()})
        args = SimpleNamespace(root=self.private, subject='alice', context='writing')
        payload = context_payload(args, 'Explain a release note.')
        self.assertEqual(payload['personalization']['rule_ids'], ['brief'])
        self.assertEqual(payload['messages'][0]['role'], 'user')
        self.assertIn('current request', payload['messages'][0]['content'])
        self.assertNotIn('Synthetic user request', payload['messages'][0]['content'])
        self.call('profile_pause', {'expected_revision': 1, 'paused': True})
        paused = context_payload(args, 'Explain a release note.')
        self.assertEqual(paused['personalization']['rule_ids'], [])
        self.assertNotIn('Use concise answers.', paused['messages'][0]['content'])

    def test_whitespace_rejected_without_saving(self):
        code, response = self.call('profile_read', {'context': '  '})
        self.assertEqual((code, response['code']), (2, 'INVALID_INPUT'))


if __name__ == '__main__':
    unittest.main()
