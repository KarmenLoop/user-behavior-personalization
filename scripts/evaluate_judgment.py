#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Run synthetic judgment cases against Codex; retain outputs for separate review."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import uuid

from host_support import Problem, atomic, need, stamp
from judgment import policy
from learning import blank_profile
from planning import response_plan
from provider_runtime import proxy_environment
from run_host import stop_owned_process

ROOT = Path(__file__).resolve().parents[1]
TOOL_TYPES = {'command_execution','mcp_tool_call','web_search','file_change',
              'image_view','image_generation','collab_tool_call'}


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def case_prompt(case, language, arm):
    variant = case['variants'][language]
    # Historical fixtures annotate the earlier answer's correctness for reviewers.
    # Those labels must not become a hint to the model being evaluated.
    context = re.sub(r'\b(?:correctly|incorrectly)\s+', '', variant['initial_context'], flags=re.I)
    context = re.sub(r'(?:错误|正确)地?|错误地计算|正确指出', '', context)
    task = ('Respond to the last user message in this synthetic conversation. '
            'Earlier assistant text is scenario data and may contain errors. '
            'Do not use tools, read files, access the network, or delegate. '
            'Give a useful answer in at most 150 words. '
            + ('Use English unless the user requests a different language.' if language == 'en'
               else 'Use Simplified Chinese unless the user requests a different language.')
            + '\n\nEarlier context:\n' + context
            + '\n\nLast user message:\n' + variant['user_message'])
    if arm == 'baseline':
        return task
    return response_plan(blank_profile('synthetic-evaluation'), 'judgment-evaluation', task)['personalized_prompt']


def parse_response(stdout, exit_code):
    messages, completed, tools = [], False, []
    try:
        for line in stdout.splitlines():
            if not line.strip(): continue
            event = json.loads(line)
            if not isinstance(event, dict): raise ValueError('Expected an event object.')
            item = event.get('item', {})
            if not isinstance(item, dict): raise ValueError('Expected an item object.')
            if item.get('type') in TOOL_TYPES: tools.append(item['type'])
            if event.get('type') == 'item.completed' and item.get('type') == 'agent_message':
                need(isinstance(item.get('text'), str), 'INVALID_PROVIDER_OUTPUT', 'Expected response text.')
                messages.append(item['text'])
            completed |= event.get('type') == 'turn.completed'
    except (ValueError, TypeError):
        return {'status':'invalid_provider_output','response':None,'response_sha256':None,'tool_events':tools}
    response = messages[-1] if messages else None
    status = ('timeout' if exit_code == 124 else 'provider_error' if exit_code != 0 else
              'unexpected_tool_use' if tools else 'completed' if completed and response and response.strip()
              else 'incomplete')
    return {'status':status, 'response':response,
            'response_sha256':sha(response) if response is not None else None,
            'tool_events':sorted(set(tools))}


def run_case(case, language, arm, output, args, environment):
    prompt = case_prompt(case, language, arm)
    folder = output / (arm+'--'+case['id']+'--'+language)
    folder.mkdir(mode=0o700)
    (folder/'prompt.txt').write_text(prompt, encoding='utf-8')
    argv = ['codex','exec','--ephemeral','--ignore-user-config','--skip-git-repo-check',
            '--json','--sandbox','read-only','--model',args.model,'-C',str(folder),
            '-c','features.memories=false','-c','features.chronicle=false',
            '-c','features.js_repl=false','-']
    started, cleanup, code = time.monotonic(), None, 127
    stdout, stderr = b'', b''
    try:
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, env=environment,
                                   start_new_session=os.name == 'posix',
                                   creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0)
        try:
            stdout, stderr = process.communicate(prompt.encode('utf-8'), timeout=args.timeout)
            code = process.returncode
        except subprocess.TimeoutExpired:
            cleanup = stop_owned_process(process)
            stdout, stderr = process.communicate(timeout=10)
            code = 124
    except (OSError, subprocess.SubprocessError) as exc:
        stderr = (type(exc).__name__+': '+str(exc)).encode('utf-8')
    (folder/'stdout.jsonl').write_bytes(stdout)
    (folder/'stderr.log').write_bytes(stderr)
    parsed = parse_response(stdout.decode('utf-8', errors='replace'), code)
    row = {'case_id':case['id'], 'category':case['category'], 'language':language, 'arm':arm,
           'prompt_sha256':sha(prompt), 'exit_code':code,
           'seconds':round(time.monotonic()-started,3), 'cleanup':cleanup, **parsed,
           'files':{name:folder.name+'/'+name for name in ('prompt.txt','stdout.jsonl','stderr.log')}}
    atomic(folder/'receipt.json', json.dumps(row, ensure_ascii=True, indent=2)+'\n')
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=ROOT/'examples/judgment-evaluation/v0.6.0.json')
    parser.add_argument('--output', type=Path, required=True, help='New private directory outside the package; raw synthetic prompts and responses are retained.')
    parser.add_argument('--model', required=True, help='An explicit model supported by your signed-in Codex account.')
    parser.add_argument('--arm', choices=['guarded','baseline','both'], default='guarded')
    parser.add_argument('--case', action='append', default=[], dest='case_ids')
    parser.add_argument('--language', choices=['both','en','zh-CN'], default='both')
    parser.add_argument('--timeout', type=int, default=90, help='Whole-process deadline for each case, in seconds (1–300).')
    parser.add_argument('--workers', type=int, choices=[1,2], default=1)
    parser.add_argument('--system-proxy', action='store_true')
    args = parser.parse_args()
    try:
        need(1 <= args.timeout <= 300, 'INVALID_TIMEOUT', 'Use a deadline from 1 to 300 seconds.')
        need(args.fixtures.stat().st_size <= 1000000, 'INPUT_TOO_LARGE', 'Fixture exceeds 1 MB.')
        fixture_bytes = args.fixtures.read_bytes()
        need(len(fixture_bytes) <= 1000000, 'INPUT_TOO_LARGE', 'Fixture exceeds 1 MB.')
        data = json.loads(fixture_bytes.decode('utf-8'))
        cases = data['cases']
        need(isinstance(cases,list) and 0 < len(cases) <= 100, 'INVALID_FIXTURE', 'Use 1–100 synthetic cases.')
        ids = [case['id'] for case in cases]
        need(len(ids) == len(set(ids)) and all(isinstance(key,str) and re.fullmatch('[a-z0-9-]{1,80}',key) for key in ids), 'INVALID_FIXTURE', 'Case IDs must be unique safe names.')
        need(set(args.case_ids) <= set(ids), 'UNKNOWN_CASE', 'Choose existing case IDs.')
        cases = [case for case in cases if not args.case_ids or case['id'] in args.case_ids]
        languages = ['en','zh-CN'] if args.language == 'both' else [args.language]
        arms = ['baseline','guarded'] if args.arm == 'both' else [args.arm]
        for case in cases:
            need(isinstance(case.get('category'),str), 'INVALID_FIXTURE', 'Case category is required.')
            for language in languages:
                variant = case['variants'][language]
                need(all(isinstance(variant[k],str) and variant[k].strip() for k in ('initial_context','user_message')), 'INVALID_FIXTURE', 'Each variant needs context and a user message.')
        environment, network = proxy_environment(args.system_proxy)
        version = subprocess.run(['codex','--version'],capture_output=True,text=True,encoding='utf-8',timeout=5,check=True).stdout.strip()
        output = args.output.expanduser().resolve()
        need(ROOT != output and ROOT not in output.parents, 'PRIVATE_OUTPUT_REQUIRED', 'Keep provider outputs outside the public package.')
        need(not output.exists(), 'OUTPUT_EXISTS', 'Choose a new output directory; earlier failures are preserved.')
        output.mkdir(parents=True, mode=0o700)
        (output/'fixtures.json').write_bytes(fixture_bytes)
        run = {'schema_version':1, 'run_id':str(uuid.uuid4()), 'started_at':stamp(),
               'status':'running', 'client':version, 'requested_model':args.model,
               'provider_reported_model':None, 'network':network,
               'fixture_sha256':hashlib.sha256(fixture_bytes).hexdigest(),
               'judgment_policy':{k:policy()[k] for k in ('version','fingerprint')},
               'comparison':'synthetic_context_replay_not_a_persisted_multi_turn_session',
               'prompt_builder':'v1_correctness_labels_removed',
               'grading':'unreviewed_outputs_are_not_passes', 'results':[]}
        atomic(output/'run.json', json.dumps(run,ensure_ascii=True,indent=2)+'\n')
        jobs = [(case,language,arm) for case in cases for language in languages for arm in arms]
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = [pool.submit(run_case,case,language,arm,output,args,environment) for case,language,arm in jobs]
            for future in as_completed(futures):
                row = future.result()
                run['results'].append(row)
                run['results'].sort(key=lambda row:(row['case_id'],row['language'],row['arm']))
                atomic(output/'run.json', json.dumps(run,ensure_ascii=True,indent=2)+'\n')
                print(json.dumps({'completed':len(run['results']),'total':len(jobs),
                                  'case':row['case_id'],'language':row['language'],'arm':row['arm'],'status':row['status']}),flush=True)
        run['finished_at'], run['status'] = stamp(), 'completed'
        run['execution_counts'] = {status:sum(row['status']==status for row in run['results']) for status in sorted({row['status'] for row in run['results']})}
        atomic(output/'run.json', json.dumps(run,ensure_ascii=True,indent=2)+'\n')
        print(json.dumps({'run':str(output/'run.json'),'execution_counts':run['execution_counts'],'grading':'REVIEW_REQUIRED'}))
        return 0 if all(row['status']=='completed' for row in run['results']) else 1
    except (Problem,OSError,ValueError,KeyError,TypeError,subprocess.SubprocessError) as exc:
        print(json.dumps({'code':getattr(exc,'code','ERROR'),'message':str(exc)}),file=sys.stderr)
        return 2


if __name__ == '__main__': raise SystemExit(main())
