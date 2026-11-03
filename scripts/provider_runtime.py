# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Opt-in child-process networking; never changes global proxy or auth settings."""
import ipaddress
import os
import re
import subprocess
import sys

from host_support import need


def proxy_environment(use_system_proxy=False, environ=None, platform=None):
    env = dict(os.environ if environ is None else environ)
    names = ('HTTPS_PROXY','https_proxy','HTTP_PROXY','http_proxy','ALL_PROXY','all_proxy')
    inherited = any(env.get(name) for name in names)
    meta = {'proxy_source': 'environment' if inherited else 'client_default'}
    if not use_system_proxy or inherited:
        return env, meta
    need((platform or sys.platform) == 'darwin', 'SYSTEM_PROXY_UNAVAILABLE',
         'System proxy discovery is available on macOS. Elsewhere configure HTTPS_PROXY in the calling shell.')
    try:
        result = subprocess.run(['scutil','--proxy'], capture_output=True, text=True,
                                encoding='utf-8', timeout=3, check=False)
    except (OSError, subprocess.SubprocessError):
        need(False, 'SYSTEM_PROXY_UNAVAILABLE', 'Could not read the existing system proxy within three seconds.')
    need(result.returncode == 0 and len(result.stdout) <= 16384, 'SYSTEM_PROXY_UNAVAILABLE',
         'Could not read the existing system proxy.')
    values = dict(re.findall(r'^\s*(HTTPSEnable|HTTPSProxy|HTTPSPort|HTTPEnable|HTTPProxy|HTTPPort)\s*:\s*(\S+)\s*$',
                             result.stdout, re.M))

    def endpoint(kind):
        need(values.get(kind+'Enable') == '1', 'SYSTEM_PROXY_UNAVAILABLE',
             'Enable a fixed HTTPS proxy in system settings or configure HTTPS_PROXY explicitly; PAC scripts are not evaluated.')
        host, port = values.get(kind+'Proxy',''), values.get(kind+'Port','')
        try:
            loopback = host.casefold() == 'localhost' or ipaddress.ip_address(host).is_loopback
        except ValueError:
            loopback = False
        need(loopback and port.isascii() and port.isdecimal() and 1 <= int(port) <= 65535,
             'UNSAFE_SYSTEM_PROXY', 'Automatic discovery accepts only an existing loopback proxy without credentials.')
        return 'http://' + ('['+host+']' if ':' in host else host) + ':' + port

    env['HTTPS_PROXY'] = endpoint('HTTPS')
    if values.get('HTTPEnable') == '1':
        env['HTTP_PROXY'] = endpoint('HTTP')
    return env, {'proxy_source': 'macos_system_loopback'}
