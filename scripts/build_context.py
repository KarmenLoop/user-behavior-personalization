#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Build a local, inspectable chat request from confirmed preferences. No network calls."""
import argparse
import json
import sys
from pathlib import Path

from host import load
from host_support import Database, Problem, content, identifier, need
from planning import response_plan


def add_plan_arguments(parser):
    parser.add_argument('--override', action='append', default=[], metavar='DIMENSION=VALUE', help='Temporary preference for this task only; repeat for multiple dimensions.')
    parser.add_argument('--omit-rule', action='append', default=[], dest='omit_rule_ids', help='Leave a saved rule out of this task without deleting it.')
    parser.add_argument('--preference-budget', type=int, default=4000, dest='max_preference_chars', help='Maximum saved preference characters (200–12000).')


def parse_plan_arguments(args):
    values = {}
    for entry in args.override:
        need('=' in entry, 'INVALID_OVERRIDES', 'Use --override dimension=value.')
        key, value = entry.split('=', 1)
        need(key not in values, 'INVALID_OVERRIDES', 'Provide each override dimension once.')
        values[key] = value
    args.task_overrides = values


def context_payload(args, task):
    identifier(args.subject)
    content(args.context, 'context', 200)
    content(task, 'task', 1000000)
    db = Database(args.root)
    try:
        plan = response_plan(load(db, args), args.context, task,
                             task_overrides=getattr(args, 'task_overrides', None),
                             omit_rule_ids=getattr(args, 'omit_rule_ids', None),
                             max_preference_chars=getattr(args, 'max_preference_chars', 4000))
    finally:
        db.close()
    return {'messages': [{'role': 'user', 'content': plan['personalized_prompt']}],
            'personalization': {'revision': plan['revision'], 'paused': plan['paused'],
                                'rule_ids': [rule['id'] for rule in plan['selected']],
                                'plan_id': plan['plan_id'], 'task_sha256': plan['task_sha256'],
                                'rule_versions': {r['id']: r['version_fingerprint'] for r in plan['selected']},
                                'task_overrides': plan['task_overrides']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--context', required=True)
    parser.add_argument('--task-file', type=Path, required=True)
    add_plan_arguments(parser)
    args = parser.parse_args()
    try:
        parse_plan_arguments(args)
        need(args.task_file.stat().st_size <= 1000000, 'INPUT_TOO_LARGE', 'Task exceeds 1 MB.')
        result = context_payload(args, args.task_file.read_text(encoding='utf-8'))
        print(json.dumps(result, ensure_ascii=True, indent=2))
    except (Problem, OSError, ValueError) as exc:
        print(json.dumps({'code': getattr(exc, 'code', 'ERROR'), 'message': str(exc)}), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
