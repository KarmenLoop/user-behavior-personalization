#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Run a synthetic learning tutorial through real CLI processes in a new private directory."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True, help='New directory outside the package; synthetic data only')
    args = parser.parse_args()
    root = args.root.expanduser().resolve()
    package = Path(__file__).resolve().parents[1]
    if root.exists() or root == package or package in root.parents:
        parser.error('choose a new private directory outside the package')
    observations = []
    base = [sys.executable, '-B', str(package/'scripts/host.py'), '--root', str(root), '--enable-observations']

    def call(tool, data, subject='demo-user', expected_error=None):
        result = subprocess.run(base + ['--subject', subject, 'call', tool], input=json.dumps(data),
                                capture_output=True, text=True, timeout=30)
        value = json.loads(result.stdout if result.returncode == 0 else result.stderr)
        if expected_error:
            assert result.returncode == 2 and value.get('code') == expected_error, value
        else:
            assert result.returncode == 0, value
        observations.append({'tool': tool, 'subject': subject, 'exit_code': result.returncode,
                             'revision': value.get('revision', value.get('profile', {}).get('revision')),
                             'error_code': value.get('code')})
        return value

    state = call('profile_read', {'context': 'status-update'})
    for number in range(3):
        event = {'id': 'demo-'+str(number), 'source_id': 'demo-source-'+str(number),
                 'session_id': 'demo-session-'+str(number), 'context': 'status-update',
                 'dimension': 'response_length', 'value': 'concise', 'signal': 'positive',
                 'occurred_at': (datetime.datetime.now(datetime.timezone.utc)-datetime.timedelta(days=number)).isoformat()}
        state = call('profile_observe', {'expected_revision': state['revision'], 'event': event})['profile']
    found = call('profile_insights', {'context': 'status-update'})
    candidate = next(c for c in found['candidates'] if c['status'] == 'ready_to_review')
    assert candidate['supporting_sessions'] == 3
    assert call('profile_read', {'context': 'status-update'})['rules'] == []
    approved = call('profile_review', {'expected_revision': state['revision'],
                    'candidate_id': candidate['candidate_id'], 'decision': 'accept', 'source_id': 'demo-confirmation'})
    rule_id = approved['rule_id']
    read = call('profile_read', {'context': 'status-update'})
    assert [r['id'] for r in read['rules']] == [rule_id]
    assert call('profile_read', {'context': 'status-update'}, subject='another-demo-user')['rules'] == []
    assert call('profile_read', {'context': 'implementation'})['rules'] == []
    paused = call('profile_pause', {'expected_revision': read['revision'], 'paused': True})['profile']
    assert call('profile_read', {'context': 'status-update'})['rules'] == []
    exported = call('profile_export', {})
    assert Path(exported['path']).is_file()
    forgotten = call('profile_forget', {'expected_revision': paused['revision'], 'rule_id': rule_id})['profile']
    assert not Path(exported['path']).exists()
    assert forgotten['observations'] == {} and forgotten['history'] == [] and forgotten['rules'] == {}
    resumed = call('profile_pause', {'expected_revision': forgotten['revision'], 'paused': False})['profile']
    call('profile_observe', {'expected_revision': resumed['revision'], 'event': event}, expected_error='SOURCE_FORGOTTEN')
    final = call('profile_reset', {'expected_revision': resumed['revision']})['profile']
    assert final['paused'] and not final['observations'] and not final['rules']
    print(json.dumps({'ok': True, 'version': (package/'VERSION').read_text().strip(),
                      'synthetic': True, 'transport': 'actual CLI subprocesses', 'calls': observations,
                      'checks': ['candidate needs confirmation', 'three independent session labels',
                                 'restart persistence', 'subject isolation', 'context isolation', 'pause',
                                 'export', 'derived data deletion', 'forgotten source suppression', 'reset'],
                      'not_run': ['production user data', 'provider model call', 'native desktop UI']}, indent=2))


if __name__ == '__main__':
    main()
