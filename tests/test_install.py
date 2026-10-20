from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallTests(unittest.TestCase):
    def test_installation_is_portable_and_an_existing_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'user-behavior-personalization'
            command = [sys.executable, '-B', str(ROOT / 'scripts/install_skill.py'), '--destination', str(target)]
            result = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse((target / '.git').exists())
            self.assertEqual((target / 'SKILL.md').read_bytes(), (ROOT / 'SKILL.md').read_bytes())
            self.assertEqual((target / 'assets/templates/state.json').read_bytes(), (ROOT / 'assets/templates/state.json').read_bytes())
            check = subprocess.run([sys.executable, '-B', str(target / 'scripts/check_package.py')], capture_output=True, text=True, timeout=20)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            (target / 'owner-file.txt').write_text('keep')
            again = subprocess.run(command, capture_output=True, text=True, timeout=20)
            self.assertEqual(again.returncode, 2)
            self.assertEqual((target / 'owner-file.txt').read_text(), 'keep')

    def test_destination_inside_source_is_rejected_before_writing(self):
        target = ROOT / 'nested-install-test'
        result = subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/install_skill.py'), '--destination', str(target)], capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(target.exists())


if __name__ == '__main__':
    unittest.main()
