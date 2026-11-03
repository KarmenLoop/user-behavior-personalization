"""Real owned subprocess protocol fixtures; no provider quality claims."""
import json
import os
from pathlib import Path
import subprocess
import signal
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from host_support import Problem
import model_runtime as runtime


@unittest.skipIf(os.name=='nt' and sys.version_info < (3,12),
                 'Actual nonblocking model pipes require Python 3.12+ on Windows.')
class ModelRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.real_popen=subprocess.Popen
        self.processes=[]
        self.argv=[]
        self.holder_pids=[]
    def tearDown(self):
        for process in self.processes:
            if process.poll() is None: runtime.stop_owned_process(process)
        for pid in self.holder_pids:
            try: os.kill(pid,signal.SIGKILL)
            except ProcessLookupError: pass
        self.tmp.cleanup()
    def call(self,body,prompt='synthetic private prompt',**kw):
        def spawn(argv,**options):
            self.argv.append(argv)
            process=self.real_popen([sys.executable,'-c',body],**options)
            self.processes.append(process)
            return process
        with patch.object(runtime,'client_capabilities',return_value=('test-client',set(runtime.DISABLED_FEATURES))),\
             patch.object(runtime,'proxy_environment',return_value=(dict(os.environ),{'proxy_source':'test'})),\
             patch.object(runtime.subprocess,'Popen',side_effect=spawn):
            return runtime.call_model(prompt,model='test-model',private_root=self.tmp.name,**kw)
    def stream(self,events):
        text='\n'.join(json.dumps(e) for e in events)
        return 'import sys;sys.stdin.read();print('+repr(text)+')'
    def good(self):
        return [{'type':'item.completed','item':{'type':'agent_message','text':'A complete answer.'}},{'type':'turn.completed'}]

    def test_complete_protocol_uses_fixed_disabled_tools_and_no_retained_transport(self):
        result=self.call(self.stream(self.good()),schema={'type':'object'})
        self.assertEqual(result['text'],'A complete answer.')
        self.assertEqual(result['metadata']['quality'],'not_automatically_graded')
        self.assertEqual(result['metadata']['cleanup'],{'owned_child_reaped':True,
                         'stdout_eof':True,'stderr_eof':True,'external_effects_checked':False})
        argv=self.argv[0]
        self.assertIn('--ignore-user-config',argv)
        self.assertIn('web_search="disabled"',argv)
        for feature in runtime.DISABLED_FEATURES: self.assertIn(feature,argv)
        self.assertEqual(argv[-1],'-')
        self.assertNotIn('synthetic private prompt',argv)
        self.assertEqual(list(Path(self.tmp.name).iterdir()),[])

    def test_partial_malformed_and_unknown_tool_protocol_are_rejected(self):
        cases=[self.stream(self.good()[:1]),'print("not json")',
               self.stream([{'type':'item.completed','item':{'type':'new_unrecognized_tool','text':'x'}},*self.good()]),
               self.stream([{'type':'item.completed','item':{'type':'error','message':'An unexpected provider failure.'}},*self.good()]),
               'import sys;sys.stdout.buffer.write(bytes([255]));sys.stdout.flush()']
        for body in cases:
            with self.subTest(body=body):
                with self.assertRaises(Problem) as e: self.call(body)
                self.assertEqual(e.exception.code,'MODEL_RESPONSE_INVALID')
        self.assertEqual(list(Path(self.tmp.name).iterdir()),[])

    def test_expected_disabled_host_notice_does_not_hide_a_complete_tool_free_answer(self):
        notice={'type':'item.completed','item':{'type':'error','message':
            'Code Mode is unavailable because code-mode host is disabled. Code mode will fail closed; enable `features.code_mode_host` and install `codex-code-mode-host`.'}}
        result=self.call(self.stream([notice,*self.good()]))
        self.assertEqual(result['text'],'A complete answer.')
        self.assertTrue(result['metadata']['disabled_host_notice'])

    def test_deadline_reaps_owned_child_and_blocked_stdin_does_not_bypass_it(self):
        started=time.monotonic()
        with self.assertRaises(Problem) as e: self.call('import time;time.sleep(30)',prompt='x'*150000,timeout=1)
        self.assertEqual(e.exception.code,'MODEL_TIMEOUT')
        self.assertLess(time.monotonic()-started,5)
        self.assertIsNotNone(self.processes[-1].poll())
        self.assertEqual(list(Path(self.tmp.name).iterdir()),[])

    def test_guard_mutation_stops_running_owned_process(self):
        checks=[]
        def guard():
            checks.append(1)
            if len(checks)>=4: raise Problem('STALE_REVISION','synthetic change')
        with self.assertRaises(Problem) as e: self.call('import time;time.sleep(30)',check_current=guard)
        self.assertEqual(e.exception.code,'STALE_REVISION')
        self.assertIsNotNone(self.processes[-1].poll())

    @unittest.skipUnless(os.name=='posix','Detached-session pipe-holder fixture requires POSIX.')
    def test_inherited_pipes_share_deadline_after_parent_exit(self):
        self.inherited_pipe_case(cancel=False)

    @unittest.skipUnless(os.name=='posix','Detached-session pipe-holder fixture requires POSIX.')
    def test_cancellation_remains_responsive_after_parent_exit_with_open_pipes(self):
        self.inherited_pipe_case(cancel=True)

    def inherited_pipe_case(self, *, cancel):
        pidfile=Path(self.tmp.name)/'holder.pid'
        child='import time;time.sleep(10)'
        body=('import subprocess,sys;from pathlib import Path;sys.stdin.read();'
              'p=subprocess.Popen([sys.executable,"-c",'+repr(child)+'],start_new_session=True);'
              'Path('+repr(str(pidfile))+').write_text(str(p.pid))')
        def guard():
            if cancel and self.processes and self.processes[-1].poll() is not None and pidfile.exists():
                raise Problem('STALE_REVISION','synthetic cancellation after parent exit')
        started=time.monotonic()
        try:
            with self.assertRaises(Problem) as caught:
                self.call(body,timeout=1,check_current=guard)
        finally:
            if pidfile.exists(): self.holder_pids.append(int(pidfile.read_text()))
        self.assertLess(time.monotonic()-started,3)
        self.assertEqual(caught.exception.code,'STALE_REVISION' if cancel else 'MODEL_TIMEOUT')
        self.assertIsNotNone(self.processes[-1].poll())
        # Reaping the parent is not evidence that either inherited pipe reached EOF.
        cleanup=caught.exception.cleanup_status
        self.assertTrue(cleanup['owned_child_reaped'])
        self.assertFalse(cleanup['stdout_eof'])
        self.assertFalse(cleanup['stderr_eof'])
        self.assertFalse(cleanup['external_effects_checked'])

    @unittest.skipUnless(os.name=='posix','POSIX process-group cleanup failure fixture.')
    def test_failed_termination_is_bounded_and_reported_without_pipe_eof(self):
        started=time.monotonic()
        with patch.object(runtime.os,'killpg',side_effect=PermissionError('synthetic denied cleanup')):
            with self.assertRaises(Problem) as caught:
                self.call('import time;time.sleep(30)',timeout=1)
        self.assertLess(time.monotonic()-started,3)
        self.assertEqual(caught.exception.code,'MODEL_TIMEOUT')
        cleanup=caught.exception.cleanup_status
        self.assertFalse(cleanup['owned_child_reaped'])
        self.assertFalse(cleanup['stdout_eof'])
        self.assertFalse(cleanup['stderr_eof'])
        self.assertEqual(cleanup['termination_errors'],['PermissionError','TimeoutExpired'])
        # tearDown owns the still-running process and performs real cleanup.

    def test_bounded_output_stops_writer_and_discards_partial_answer(self):
        with patch.object(runtime,'MAX_OUTPUT',16384):
            with self.assertRaises(Problem) as e: self.call('import sys,time;sys.stdout.write("x"*100000);sys.stdout.flush();time.sleep(30)')
        self.assertEqual(e.exception.code,'MODEL_OUTPUT_TOO_LARGE')
        self.assertIsNotNone(self.processes[-1].poll())


class ModelRuntimePlatformTests(unittest.TestCase):
    def test_windows_python311_fails_before_starting_optional_model_client(self):
        with patch.object(runtime.os,'name','nt'), patch.object(runtime.sys,'version_info',(3,11)), \
             patch.object(runtime,'client_capabilities') as capabilities, \
             patch.object(runtime.subprocess,'Popen') as spawn:
            with self.assertRaises(Problem) as caught:
                runtime.call_model('synthetic',model='fixture',private_root='unused')
        self.assertEqual(caught.exception.code,'MODEL_CLIENT_UNSUPPORTED')
        self.assertIn('Python 3.12',str(caught.exception))
        capabilities.assert_not_called()
        spawn.assert_not_called()


if __name__=='__main__': unittest.main()
