"""Existing proxy settings apply only to explicitly opted-in child processes."""
from pathlib import Path
import sys
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from host_support import Problem
from provider_runtime import proxy_environment

PROXY = '''<dictionary> {
  HTTPEnable : 1
  HTTPPort : 7897
  HTTPProxy : 127.0.0.1
  HTTPSEnable : 1
  HTTPSPort : 7897
  HTTPSProxy : 127.0.0.1
}'''


class ProxyTests(unittest.TestCase):
    def environment(self, text=PROXY, env=None, platform='darwin', enabled=True):
        with mock.patch('provider_runtime.subprocess.run', return_value=mock.Mock(returncode=0, stdout=text)) as read:
            result = proxy_environment(enabled, environ={} if env is None else env, platform=platform)
            return result, read.call_count

    def test_default_does_not_read_or_change_system_settings(self):
        (env, meta), calls = self.environment(env={'EXAMPLE':'kept'}, enabled=False)
        self.assertEqual(env, {'EXAMPLE':'kept'})
        self.assertEqual(calls, 0)

    def test_explicit_proxy_is_child_only_and_uses_existing_loopback(self):
        original = {'EXAMPLE':'kept'}
        (env, meta), calls = self.environment(env=original)
        self.assertEqual(original, {'EXAMPLE':'kept'})
        self.assertEqual(env['HTTPS_PROXY'], 'http://127.0.0.1:7897')
        self.assertEqual(env['HTTP_PROXY'], 'http://127.0.0.1:7897')
        self.assertEqual(meta['proxy_source'], 'macos_system_loopback')
        self.assertEqual(calls, 1)
        self.assertNotIn('7897', str(meta))

    def test_existing_environment_takes_precedence_including_lowercase(self):
        for key in ('HTTPS_PROXY','https_proxy','ALL_PROXY','all_proxy','HTTP_PROXY','http_proxy'):
            with self.subTest(key=key):
                original = {key:'http://example.invalid:1234'}
                (env, meta), calls = self.environment(env=original)
                self.assertEqual(env, original)
                self.assertEqual(calls, 0)

    def test_remote_credentials_invalid_ports_and_disabled_settings_are_rejected(self):
        for text in (PROXY.replace('127.0.0.1','proxy.example.com'),
                     PROXY.replace('127.0.0.1','user:secret@127.0.0.1'),
                     PROXY.replace('7897','70000'),
                     PROXY.replace('HTTPSEnable : 1','HTTPSEnable : 0'),
                     '<dictionary> { ProxyAutoConfigEnable : 1 }'):
            with self.subTest(text=text), self.assertRaises(Problem): self.environment(text)

    def test_opt_in_on_other_platform_explains_configuration_instead_of_guessing(self):
        with self.assertRaises(Problem) as caught: self.environment(platform='linux')
        self.assertEqual(caught.exception.code, 'SYSTEM_PROXY_UNAVAILABLE')

    def test_ipv6_loopback_is_valid_and_bracketed(self):
        (env, _), _ = self.environment(PROXY.replace('127.0.0.1','::1'))
        self.assertEqual(env['HTTPS_PROXY'], 'http://[::1]:7897')


if __name__ == '__main__': unittest.main()
