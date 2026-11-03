"""Actual selected-file ingestion and restart/pause/error boundaries."""
import datetime as dt
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from host import dispatch
from host_support import Problem
from watch_conversations import process_once, read_watch_status, _read_source, MAX_RECORD_BYTES


class WatchTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory()
        self.base=Path(self.temporary.name)
        self.source=self.base/'selected.jsonl'
        self.source.write_bytes(b'')
        self.args=SimpleNamespace(root=str(self.base/'private'),subject='demo',input=self.source,
            enable_conversations=True,enable_observations=False,workspace=str(self.base),host_id='watch-test')

    def tearDown(self):self.temporary.cleanup()

    def record(self,session='one',text='Too long. Keep it brief.'):
        return {'session_id':session,'context':'writing','messages':[{'id':'m1','role':'user','text':text,
            'at':(dt.datetime.now(dt.timezone.utc)-dt.timedelta(hours=1)).isoformat()}]}

    def append(self,value):
        with self.source.open('ab') as stream:stream.write(json.dumps(value,ensure_ascii=False).encode()+b'\n')

    def profile(self):return dispatch('profile_export',{},self.args)['profile']

    def error(self,code):
        with self.assertRaises(Problem) as caught:process_once(self.args)
        self.assertEqual(caught.exception.code,code)

    def test_explicit_optin_is_required_before_creating_private_root(self):
        self.args.enable_conversations=False
        self.error('CONVERSATIONS_DISABLED')
        self.assertFalse(Path(self.args.root).exists())

    def test_append_restart_and_identical_snapshot_do_not_duplicate_evidence(self):
        first=self.record();self.append(first)
        status=process_once(self.args)
        self.assertEqual((status['status'],status['lines'],status['imported_records']),('caught_up',1,1))
        revision=self.profile()['revision']
        self.assertEqual(process_once(self.args)['lines'],1)
        self.assertEqual(self.profile()['revision'],revision)
        self.append(first)
        status=process_once(self.args)
        self.assertEqual((status['lines'],status['imported_records']),(2,1))
        self.assertEqual(self.profile()['revision'],revision)
        second=self.record('two');self.append(second)
        self.assertEqual(process_once(self.args)['imported_records'],2)
        self.assertEqual(len(self.profile()['conversation_messages']),2)

    def test_complete_utf8_line_only(self):
        raw=json.dumps(self.record(text='太长了，请简短一点。'),ensure_ascii=False).encode()
        partial=raw.index('太'.encode())+1
        self.source.write_bytes(raw[:partial])
        status=process_once(self.args)
        self.assertEqual((status['status'],status['offset']),('waiting_for_line',0))
        with self.source.open('ab') as stream:stream.write(raw[partial:]+b'\n')
        self.assertEqual(process_once(self.args)['lines'],1)
        self.assertEqual(len(self.profile()['conversation_messages']),1)

    def test_pause_does_not_consume_then_resume_uses_same_line(self):
        self.append(self.record())
        dispatch('profile_pause',{'expected_revision':0,'paused':True},self.args)
        status=process_once(self.args)
        self.assertEqual((status['status'],status['offset'],status['lines']),('paused',0,0))
        dispatch('profile_pause',{'expected_revision':1,'paused':False},self.args)
        self.assertEqual(process_once(self.args)['lines'],1)

    def test_invalid_line_stops_before_later_valid_record_and_preserves_cursor(self):
        self.append(self.record())
        with self.source.open('ab') as stream:stream.write(b'{invalid}\n')
        self.append(self.record('later'))
        self.error('INVALID_JSONL')
        status=read_watch_status(self.args.root,self.args.subject)[0]
        self.assertEqual((status['status'],status['last_code'],status['lines']),('error','INVALID_JSONL',1))
        self.assertEqual(len(self.profile()['conversation_messages']),1)
        self.error('INVALID_JSONL')
        self.assertEqual(len(self.profile()['conversation_messages']),1)

    def test_changed_or_truncated_consumed_prefix_is_rejected(self):
        self.append(self.record());process_once(self.args)
        original=self.source.read_bytes()
        self.source.write_bytes(original.replace(b'Too long',b'Too slow'))
        self.error('FEED_HISTORY_CHANGED')
        self.source.write_bytes(b'')
        self.error('FEED_HISTORY_CHANGED')
        self.assertEqual(len(self.profile()['conversation_messages']),1)

    def test_profile_rejection_does_not_advance_cursor(self):
        first=self.record();self.append(first);process_once(self.args)
        changed=json.loads(json.dumps(first));changed['messages'][0]['text']='Include more details.'
        self.append(changed)
        self.error('SESSION_HISTORY_CHANGED')
        self.assertEqual(read_watch_status(self.args.root,self.args.subject)[0]['lines'],1)

    def test_separate_subjects_have_independent_cursors_and_profiles(self):
        self.append(self.record());process_once(self.args)
        other=SimpleNamespace(**{**vars(self.args),'subject':'other'})
        self.assertEqual(read_watch_status(other.root,other.subject),[])
        self.assertEqual(process_once(other)['lines'],1)
        self.assertEqual(len(dispatch('profile_export',{},other)['profile']['conversation_messages']),1)
        dispatch('profile_reset',{'expected_revision':1},self.args)
        self.assertEqual(process_once(self.args)['status'],'paused')
        self.assertEqual(read_watch_status(self.args.root,self.args.subject)[0]['lines'],1)
        self.assertEqual(len(dispatch('profile_export',{},other)['profile']['conversation_messages']),1)

    def test_metadata_has_no_raw_text_or_full_selected_path(self):
        self.append(self.record(text='Please keep it brief. This is a synthetic private sentence.'))
        process_once(self.args)
        status=read_watch_status(self.args.root,self.args.subject)
        rendered=json.dumps(status)
        self.assertNotIn('synthetic private sentence',rendered)
        self.assertNotIn(str(self.source),rendered)
        self.assertIn(self.source.name,rendered)

    def test_regular_file_and_size_boundaries(self):
        self.args.input=self.base
        self.error('UNSAFE_INPUT')
        self.args.input=self.source
        self.source.write_bytes(b'x'*(MAX_RECORD_BYTES+1))
        self.error('RECORD_TOO_LARGE')

    def test_directory_is_classified_before_windows_open_permission_error(self):
        # Windows os.open(directory) raises PermissionError rather than returning
        # a descriptor. The diagnostic should still identify the invalid input.
        with patch('watch_conversations.os.open',side_effect=PermissionError('directory access denied')) as opened:
            with self.assertRaises(Problem) as caught:
                _read_source(self.base)
        self.assertEqual(caught.exception.code,'UNSAFE_INPUT')
        opened.assert_not_called()

    def test_regular_file_access_error_remains_input_unavailable(self):
        denied=PermissionError('file access denied')
        with patch('watch_conversations.os.open',side_effect=denied) as opened:
            with self.assertRaises(Problem) as caught:
                _read_source(self.source)
        self.assertEqual(caught.exception.code,'INPUT_UNAVAILABLE')
        self.assertIs(caught.exception.__cause__,denied)
        opened.assert_called_once()

    def test_opened_descriptor_type_is_checked_after_regular_path_precheck(self):
        descriptor=os.open(self.source,os.O_RDONLY)
        with patch('watch_conversations.os.open',return_value=descriptor), \
             patch('watch_conversations.os.fstat',return_value=SimpleNamespace(st_mode=stat.S_IFDIR)), \
             patch('watch_conversations.os.close',wraps=os.close) as closed:
            with self.assertRaises(Problem) as caught:
                _read_source(self.source)
        self.assertEqual(caught.exception.code,'UNSAFE_INPUT')
        closed.assert_called_once_with(descriptor)
        with self.assertRaises(OSError):
            os.fstat(descriptor)

    def test_symlink_input_is_rejected(self):
        link=self.base/'alias.jsonl'
        try:link.symlink_to(self.source)
        except OSError:self.skipTest('Symlink creation unavailable for this account.')
        self.args.input=link
        self.error('UNSAFE_INPUT')

    def test_actual_cli_once_ingests_and_returns_metadata(self):
        self.append(self.record())
        command=[sys.executable,'-B',str(ROOT/'scripts/watch_conversations.py'),'--root',self.args.root,
            '--subject',self.args.subject,'--input',str(self.source),'--enable-conversations','--once']
        result=subprocess.run(command,text=True,capture_output=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'],'caught_up')
        self.assertEqual(len(self.profile()['conversation_messages']),1)


if __name__=='__main__':unittest.main()
