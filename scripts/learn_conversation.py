#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Import an explicitly selected JSON/JSONL conversation and show reviewable results."""
import argparse
import json
from pathlib import Path
import sys
from host import dispatch
from host_support import Problem, need


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--format', choices=['json', 'jsonl'], default='json')
    parser.add_argument('--session-id')
    parser.add_argument('--context')
    parser.add_argument('--enable-conversations', action='store_true', help='Permit storing user excerpts, source records and derived features from the selected file.')
    args = parser.parse_args()
    try:
        need(args.enable_conversations, 'CONVERSATIONS_DISABLED', 'Explicitly enable conversation import before saving excerpts.')
        need(args.input.stat().st_size <= 1000000, 'INPUT_TOO_LARGE', 'Input exceeds 1 MB.')
        raw = args.input.read_text(encoding='utf-8')
        if args.format == 'jsonl':
            need(args.session_id and args.context, 'CONTEXT_REQUIRED', 'JSONL input needs --session-id and --context.')
            conversation = {'session_id': args.session_id, 'context': args.context,
                            'messages': [json.loads(line) for line in raw.splitlines() if line.strip()]}
        else:
            conversation = json.loads(raw)
        state = dispatch('profile_read', {'context': conversation['context']}, args)
        result = dispatch('conversation_import', {'expected_revision': state['revision'], 'conversation': conversation}, args)
        summary = {key: value for key, value in result.items() if key != 'profile'}
        summary['revision'] = result['profile']['revision']
        print(json.dumps({'import': summary, 'portrait': dispatch('profile_portrait', {'context': conversation['context']}, args)}, ensure_ascii=True, indent=2))
    except (Problem, OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'code': getattr(exc, 'code', 'INVALID_INPUT'), 'message': str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
