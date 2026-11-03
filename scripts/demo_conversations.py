#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Exercise conversation learning through separate real CLI processes, without a provider."""
import argparse
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    args = parser.parse_args()
    package = Path(__file__).resolve().parents[1]
    private = args.root.expanduser().resolve()
    if private.exists() or private == package or package in private.parents:
        parser.error('choose a new private directory outside the package')
    command = [sys.executable, '-B', str(package/'scripts/host.py'), '--root', str(private),
               '--subject', 'synthetic-user', '--enable-conversations']
    calls = []

    def call(tool, values, error=None):
        result = subprocess.run(command + ['call', tool], input=json.dumps(values), capture_output=True, text=True, timeout=20)
        data = json.loads(result.stdout if result.returncode == 0 else result.stderr)
        if error:
            assert result.returncode == 2 and data['code'] == error, data
        else:
            assert result.returncode == 0, data
        calls.append({'tool': tool, 'exit_code': result.returncode, 'expected_error': error})
        return data

    def write(tool, values, error=None):
        revision = call('profile_read', {'context': 'lab-review'})['revision']
        return call(tool, {'expected_revision': revision, **values}, error)

    now = dt.datetime.now(dt.timezone.utc)
    sessions = []
    for index in range(2):
        conversation = {'session_id': 'lab-'+str(index), 'context': 'lab-review', 'messages': [
            {'id': 'preference', 'role': 'user', 'text': 'For future laboratory reports, list sample identifiers and measurement units before the conclusion.', 'at': (now-dt.timedelta(days=index+1)).isoformat()},
            {'id': 'request', 'role': 'user', 'text': 'Analyze these laboratory results and highlight abnormal samples.', 'at': (now-dt.timedelta(days=index+1)+dt.timedelta(minutes=1)).isoformat()},
            {'id': 'reply', 'role': 'assistant', 'text': 'This synthetic assistant text is not user evidence.', 'at': (now-dt.timedelta(days=index+1)+dt.timedelta(minutes=2)).isoformat()},
            {'id': 'next', 'role': 'user', 'text': 'List the abnormal sample identifiers and propose a repeat-measurement plan.', 'at': (now-dt.timedelta(days=index+1)+dt.timedelta(minutes=3)).isoformat()},
        ]}
        sessions.append(conversation)
        result = write('conversation_import', {'conversation': conversation})
        assert result['added_messages'] == 3
    portrait = call('profile_portrait', {'context': 'lab-review'})
    assert portrait['writing_observations']['message_count'] == 6
    assert portrait['confirmed_preferences'] == []
    proposal = portrait['pending_preferences'][0]
    reviewed = write('profile_proposal_review', {'proposal_id': proposal['id'], 'decision': 'accept', 'source_id': 'synthetic-approval'})
    assert call('profile_read', {'context': 'lab-review'})['rules'][0]['id'] == reviewed['rule_id']
    forecast = call('profile_forecast', {'context': 'lab-review', 'request': 'Analyze laboratory results and highlight abnormal samples.'})
    assert forecast['status'] == 'suggested', forecast
    assert forecast['candidates'][0]['supporting_sessions'] >= 2
    context = call('profile_model_context', {'context': 'lab-review'})
    source = next(item for item in context['excerpts'] if 'sample identifiers and measurement units' in item['text'])
    model_proposal = {'statement': 'Keep sample IDs and units visible in laboratory reports.', 'scope': 'lab-review', 'category': 'workflow', 'evidence': [{'source_key': source['source_key'], 'quote': source['text']}]}
    staged = write('profile_model_propose', {'proposals': [model_proposal]})
    assert staged['added_proposals'] == 1
    assert len(call('profile_read', {'context': 'lab-review'})['rules']) == 1
    write('profile_forget_conversation', {'session_id': 'lab-0'})
    assert call('profile_forecast', {'context': 'lab-review', 'request': 'Analyze laboratory results and highlight abnormal samples.'})['status'] == 'insufficient_evidence'
    write('conversation_import', {'conversation': sessions[0]}, 'SOURCE_FORGOTTEN')
    write('profile_reset', {})
    final = call('profile_export', {})['profile']
    assert final['paused'] and not final['conversation_messages'] and not final['conversation_proposals'] and not final['rules']
    print(json.dumps({'ok': True, 'synthetic': True, 'version': (package/'VERSION').read_text().strip(),
                      'transport': 'actual CLI subprocesses', 'calls': calls,
                      'forecast': {'status': forecast['status'], 'supporting_sessions': forecast['candidates'][0]['supporting_sessions']},
                      'checks': ['raw text import', 'freeform preference proposal', 'style evidence', 'explicit review', 'restart recall', 'historical next-request retrieval', 'grounded model proposal validation', 'derived data deletion', 'replay suppression', 'reset'],
                      'not_run': ['live model extraction', 'human outcome study', 'native desktop GUI']}, indent=2))


if __name__ == '__main__':
    main()
