#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Load confirmed preferences before a CLI task; retain only a metadata receipt."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid

from build_context import context_payload, add_plan_arguments, parse_plan_arguments
from host import load
from host_support import Database, Problem, atomic, need, stamp


def stop_owned_process(process):
    """Attempt bounded group cleanup and always try to reap the owned child."""
    errors = []
    try:
        if os.name == 'posix':
            os.killpg(process.pid, signal.SIGKILL)
        else:
            stopped = subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                     capture_output=True, timeout=10)
            if stopped.returncode:
                errors.append('taskkill returned ' + str(stopped.returncode))
    except ProcessLookupError:
        pass  # The child may have finished between the deadline and termination.
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(type(exc).__name__)
    try:
        process.wait(timeout=10)
        reaped = True
    except (OSError, subprocess.SubprocessError) as exc:
        errors.append(type(exc).__name__)
        reaped = False
    return {'owned_child_reaped': reaped, 'termination_errors': errors,
            'external_effects_checked': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--context', required=True)
    parser.add_argument('--host', choices=['codex', 'cursor'], required=True)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--prompt', type=Path, required=True)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--read-only', action='store_true', help='Use the host read-only mode.')
    add_plan_arguments(parser)
    args = parser.parse_args()
    try:
        parse_plan_arguments(args)
        need(args.workspace.is_dir(), 'WORKSPACE_MISSING', 'Create the workspace first.')
        need(args.prompt.stat().st_size <= 1000000, 'INPUT_TOO_LARGE', 'Prompt exceeds 1 MB.')
        payload = context_payload(args, args.prompt.read_text(encoding='utf-8'))
        prompt = payload['messages'][0]['content']
        profile = payload['personalization']
        record = {'host': args.host, 'profile_revision': profile['revision'],
                  'rule_ids': profile['rule_ids'], 'paused': profile['paused'],
                  'plan_id': profile['plan_id'], 'rule_versions': profile['rule_versions'],
                  'judgment_policy': profile['judgment_policy'],
                  'started_at': stamp(), 'output_retention': 'console_only'}
        workspace = str(args.workspace.resolve())
        if args.host == 'codex':
            argv = ['codex', 'exec', '--ephemeral', '--skip-git-repo-check', '--json', '-C', workspace]
            if args.read_only:
                argv += ['--sandbox', 'read-only']
            argv += ['-']
        else:
            argv = ['agent', '--print', '--output-format', 'stream-json', '--workspace', workspace]
            if args.read_only:
                argv += ['--mode', 'ask']
            # Cursor uses a positional prompt; same-user process tools can see it.
            argv += [prompt]
        try:
            process = subprocess.Popen(
                argv, stdin=subprocess.PIPE if args.host == 'codex' else subprocess.DEVNULL,
                start_new_session=os.name == 'posix',
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
            try:
                process.communicate(input=prompt.encode() if args.host == 'codex' else None,
                                    timeout=max(1, min(args.timeout, 300)))
                record['exit_code'] = process.returncode
            except subprocess.TimeoutExpired:
                record['cleanup'] = stop_owned_process(process)
                record['exit_code'] = 124
                record['error'] = 'Host timed out. Inspect external effects before retrying.'
        except OSError as exc:
            record['exit_code'] = 127
            record['error'] = str(exc)
        record['finished_at'] = stamp()
        db = Database(args.root)
        try:
            def save_receipt():
                changed = load(db, args)['revision'] != profile['revision']
                record['profile_changed_during_run'] = changed
                if changed:
                    record['rule_ids'] = []
                    record['rule_versions'] = {}
                    record['plan_id'] = None
                runs = db.root / 'host-runs'
                subject_runs = runs / hashlib.sha256(args.subject.encode()).hexdigest()
                need(not runs.is_symlink() and not subject_runs.is_symlink(),
                     'UNSAFE_PATH', 'Refusing a symbolic-link receipt directory.')
                subject_runs.mkdir(parents=True, exist_ok=True, mode=0o700)
                os.chmod(runs, 0o700)
                os.chmod(subject_runs, 0o700)
                path = subject_runs / (uuid.uuid4().hex + '.json')
                atomic(path, json.dumps(record, indent=2) + '\n')
                return path
            receipt = db.transaction(save_receipt)
        finally:
            db.close()
        print(json.dumps({'receipt': str(receipt), **record}), flush=True)
        return record['exit_code']
    except (Problem, OSError, ValueError) as exc:
        print(json.dumps({'code': getattr(exc, 'code', 'ERROR'), 'message': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
