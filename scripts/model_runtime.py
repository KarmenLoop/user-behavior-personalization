# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Bounded, tool-disabled Codex generation for opted-in local workflows."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import signal
import sys
import time

from host_support import need, Problem
from provider_runtime import proxy_environment
from run_host import stop_owned_process

MAX_OUTPUT = 1_000_000
DISABLED_FEATURES = ('shell_tool','unified_exec','shell_snapshot','apps','view_image',
                     'image_generation','multi_agent','multi_agent_v2','agent_message_board',
                     'skill_search','skill_mcp_dependency_install','in_app_browser',
                     'in_app_local_automation','code_mode_tool_search','code_mode_host','code_mode',
                     'computer_use','browser_use','browser_use_external','goals','workspace_dependencies','sleep_tool')
REQUIRED_SWITCHES = {'shell_tool','apps','view_image','image_generation','multi_agent'}
DISABLED_HOST_NOTICE = ('Code Mode is unavailable because code-mode host is disabled. '
                        'Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.')


def sha(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def client_capabilities():
    try:
        version = subprocess.run(['codex','--version'],capture_output=True,text=True,encoding='utf-8',timeout=5,check=True).stdout.strip()
        features = subprocess.run(['codex','features','list'],capture_output=True,text=True,encoding='utf-8',timeout=5,check=True).stdout
    except (OSError,subprocess.SubprocessError):
        raise Problem('MODEL_CLIENT_UNAVAILABLE','Install and sign in to the compatible Codex CLI before enabling model workflows.')
    available = {line.split()[0] for line in features.splitlines() if line.split()}
    need(REQUIRED_SWITCHES <= available, 'MODEL_CLIENT_UNSUPPORTED',
         'This Codex CLI cannot disable the required tool features. Update the client before processing selected excerpts.')
    return version, available


def call_model(prompt, *, model, private_root, system_proxy=False, timeout=90, schema=None, check_current=None):
    need(isinstance(prompt,str) and 0 < len(prompt) <= 150000, 'MODEL_INPUT_TOO_LARGE','Select a smaller set of excerpts or a shorter task.')
    need(isinstance(model,str) and 0 < len(model) <= 100, 'MODEL_REQUIRED','Configure a model available to the signed-in Codex account.')
    need(type(timeout) is int and 1 <= timeout <= 300, 'INVALID_TIMEOUT','Use a model deadline from1 to300 seconds.')
    need(os.name != 'nt' or sys.version_info >= (3,12), 'MODEL_CLIENT_UNSUPPORTED',
         'Optional model workflows on Windows require Python 3.12 or newer for bounded pipe IO; offline workflows remain available.')
    if check_current: check_current()
    version, features = client_capabilities()
    environment, network = proxy_environment(system_proxy)
    with tempfile.TemporaryDirectory(prefix='model-workflow-',dir=str(private_root)) as folder:
        os.chmod(folder,0o700)
        argv = ['codex','exec','--ephemeral','--ignore-user-config','--skip-git-repo-check',
                '--json','--sandbox','read-only','--model',model,'-C',folder,
                '-c','web_search="disabled"','-c','features.memories=false','-c','features.chronicle=false']
        for feature in DISABLED_FEATURES:
            if feature in features: argv += ['--disable',feature]
        if schema is not None:
            path = Path(folder)/'response-schema.json'
            path.write_text(json.dumps(schema),encoding='utf-8')
            argv += ['--output-schema',str(path)]
        argv += ['-']
        if check_current: check_current()
        try:
            process = subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                       env=environment,bufsize=0,start_new_session=os.name=='posix',
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
        except OSError:
            raise Problem('MODEL_CLIENT_UNAVAILABLE','The configured Codex client could not start.')
        chunks = {'stdout':bytearray(),'stderr':bytearray()}
        eof = {'stdout':False,'stderr':False}
        started = time.monotonic()
        deadline = started + timeout
        remaining_input = memoryview(prompt.encode('utf-8'))
        streams = (process.stdin,process.stdout,process.stderr)
        try:
            # One owner, no buffered locks or IO threads. Python 3.12 added
            # Windows anonymous-pipe support to os.set_blocking.
            for stream in streams: os.set_blocking(stream.fileno(),False)
            while True:
                if check_current: check_current()
                need(time.monotonic() < deadline,'MODEL_TIMEOUT',
                     'The model request timed out; no proposal or comparison was saved.')
                if not process.stdin.closed:
                    try:
                        written = os.write(process.stdin.fileno(),remaining_input[:8192])
                        remaining_input = remaining_input[written:]
                    except BlockingIOError:
                        pass
                    except BrokenPipeError:
                        remaining_input = memoryview(b'')
                    if not remaining_input: process.stdin.close()
                for name in chunks:
                    if eof[name]: continue
                    try:
                        piece = os.read(getattr(process,name).fileno(),8192)
                    except BlockingIOError:
                        continue
                    if not piece:
                        eof[name] = True
                    else:
                        need(len(chunks[name])+len(piece) <= MAX_OUTPUT,'MODEL_OUTPUT_TOO_LARGE',
                             'The model output exceeded the bounded workflow limit.')
                        chunks[name].extend(piece)
                # Parent exit and per-stream EOF are independent observations.
                if process.poll() is not None and all(eof.values()) and process.stdin.closed:
                    break
                time.sleep(min(.01,max(0,deadline-time.monotonic())))
            need(process.returncode==0,'MODEL_REQUEST_FAILED','The Codex request failed. Check account access and connectivity; no private transport log was retained.')
            if check_current: check_current()
        except BaseException as error:
            # Cleanup has a separate, fixed 250ms reap allowance, never a pipe
            # drain allowance. Detached descendants are not claimed as stopped.
            errors = []
            try:
                if os.name == 'posix': os.killpg(process.pid,signal.SIGKILL)
                elif process.poll() is None: process.kill()
            except ProcessLookupError:
                pass
            except OSError as exc:
                errors.append(type(exc).__name__)
            try:
                process.wait(timeout=.25)
            except (OSError,subprocess.SubprocessError) as exc:
                errors.append(type(exc).__name__)
            error.cleanup_status = {'owned_child_reaped':process.poll() is not None,
                                    'termination_errors':errors,
                                    'stdout_eof':eof['stdout'],'stderr_eof':eof['stderr'],
                                    'external_effects_checked':False}
            raise
        finally:
            # Unbuffered pipes have no live reader/writer holding a close lock.
            for stream in streams: stream.close()
        # Use the existing protocol parser; output format is not a quality grade.
        from evaluate_judgment import parse_response
        try:
            raw=bytes(chunks['stdout']).decode('utf-8',errors='strict')
            events=[json.loads(line) for line in raw.splitlines() if line.strip()]
            def expected_notice(event):
                item=event.get('item') if isinstance(event,dict) else None
                return isinstance(item,dict) and item.get('type')=='error' and item.get('message')==DISABLED_HOST_NOTICE
            need(all(isinstance(event,dict) and (not str(event.get('type','')).startswith('item.')
                     or isinstance(event.get('item'),dict) and event['item'].get('type') in ('reasoning','agent_message')
                     or expected_notice(event))
                     for event in events),'MODEL_RESPONSE_INVALID','The client returned an unexpected tool or item type.')
        except (UnicodeError,ValueError,TypeError) as error:
            if isinstance(error,Problem): raise
            raise Problem('MODEL_RESPONSE_INVALID','The client returned an invalid event stream.')
        result = parse_response(raw,process.returncode)
        need(result['status']=='completed','MODEL_RESPONSE_INVALID','The client did not return a complete, tool-free model answer.')
        text = result['response']
        need(len(text) <= 32000,'MODEL_OUTPUT_TOO_LARGE','The answer exceeds the private comparison limit.')
        return {'text':text,'metadata':{'client':version,'requested_model':model,'provider_reported_model':None,
                'prompt_sha256':sha(prompt),'response_sha256':sha(text),
                'seconds':round(time.monotonic()-started,3),'network':network,
                'cleanup':{'owned_child_reaped':process.poll() is not None,
                           'stdout_eof':eof['stdout'],'stderr_eof':eof['stderr'],
                           'external_effects_checked':False},
                'execution_kind':'observed_owned_codex_subprocess','quality':'not_automatically_graded',
                'disabled_host_notice':any(expected_notice(event) for event in events),
                'disabled_tool_features':[f for f in DISABLED_FEATURES if f in features]}}
