"""Owned-process cleanup is tested separately from any live model acceptance."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import run_host


class WrapperTests(unittest.TestCase):
    def test_windows_taskkill_failure_still_reaps_and_reports_uncertainty(self):
        process = mock.Mock(pid=123, returncode=0)
        with mock.patch.object(run_host.os, 'name', 'nt'), mock.patch.object(run_host.subprocess, 'run', return_value=mock.Mock(returncode=128)):
            result = run_host.stop_owned_process(process)
        process.wait.assert_called_once_with(timeout=10)
        self.assertTrue(result['owned_child_reaped'])
        self.assertEqual(result['termination_errors'], ['taskkill returned 128'])

    def test_failed_wait_is_retained_as_unknown_not_completed(self):
        process = mock.Mock(pid=123)
        process.wait.side_effect = subprocess.TimeoutExpired('fixture', 10)
        with mock.patch.object(run_host.os, 'name', 'nt'), mock.patch.object(run_host.subprocess, 'run', side_effect=subprocess.TimeoutExpired('taskkill', 10)):
            result = run_host.stop_owned_process(process)
        self.assertFalse(result['owned_child_reaped'])
        self.assertEqual(result['termination_errors'], ['TimeoutExpired', 'TimeoutExpired'])

    @unittest.skipUnless(os.name == 'posix', 'Executable fixture uses a POSIX shebang, not a real Codex model.')
    def test_actual_fixture_process_streams_output_but_saves_metadata_only(self):
        self.exercise(False)

    @unittest.skipUnless(os.name == 'posix', 'Executable fixture uses a POSIX shebang, not a real Codex model.')
    def test_actual_fixture_timeout_returns_receipt_and_reaps_child(self):
        self.exercise(True)

    def exercise(self, timeout):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            binary = base/'bin'
            binary.mkdir()
            fixture = binary/'codex'
            fixture.write_text('#!' + sys.executable + '\nimport sys,time\nsys.stdin.read()\n' +
                               ('time.sleep(30)\n' if timeout else 'print("SYNTHETIC_PRIVATE_OUTPUT")\n'))
            fixture.chmod(0o700)
            prompt = base/'task.txt'
            prompt.write_text('Synthetic task only.')
            env = {**os.environ, 'PATH': str(binary)+os.pathsep+os.environ.get('PATH', '')}
            result = subprocess.run([sys.executable, '-B', str(ROOT/'scripts/run_host.py'), '--root', str(base/'private'),
                         '--subject', 'alice', '--context', 'writing', '--workspace', str(base),
                         '--prompt', str(prompt), '--host', 'codex', '--read-only', '--timeout', '1' if timeout else '5'],
                         capture_output=True, text=True, env=env, timeout=20)
            self.assertEqual(result.returncode, 124 if timeout else 0, result.stdout+result.stderr)
            receipt = json.loads(result.stdout.splitlines()[-1])
            saved = Path(receipt['receipt']).read_text()
            self.assertNotIn('SYNTHETIC_PRIVATE_OUTPUT', saved)
            self.assertNotIn('Synthetic task only', saved)
            self.assertFalse(list((base/'private').rglob('stdout*')))
            if timeout:
                self.assertTrue(receipt['cleanup']['owned_child_reaped'])
            else:
                self.assertIn('SYNTHETIC_PRIVATE_OUTPUT', result.stdout)


if __name__ == '__main__':
    unittest.main()
