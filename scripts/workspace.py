#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Serve the subject-bound personalization workspace on this computer only."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import secrets
import sqlite3
from urllib.parse import urlsplit

from host import dispatch, load
from host_support import Database, Problem, identifier, private_root
from learning import DIMENSIONS, STATEMENTS
from conditions import CONDITION_VALUES
from model_jobs import ModelJobs

ROOT = Path(__file__).resolve().parents[1]
ASSETS = {'/': ('index.html', 'text/html; charset=utf-8'),
          '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
          '/style.css': ('style.css', 'text/css; charset=utf-8')}
ALLOWED_TOOLS = frozenset({
    'profile_read', 'profile_portrait', 'profile_model_context', 'conversation_import',
    'profile_proposal_review', 'profile_habits', 'profile_habit_review',
    'profile_correct', 'profile_forget', 'profile_forget_conversation',
    'profile_forget_messages', 'profile_pause', 'profile_plan',
    'profile_plan_prepare', 'profile_plan_forget', 'profile_outcome', 'profile_outcome_summary',
    'profile_comparison_list', 'profile_comparison_read', 'profile_comparison_reveal',
    'profile_comparison_vote', 'profile_comparison_forget',
})
MAX_BODY = 1_000_000


def bootstrap(args):
    db = Database(args.root)
    try:
        profile = load(db, args)
        # Pause hides ordinary evidence and preferences. Controls remain available.
        rules = [] if profile['paused'] else list(profile['rules'].values())
        sources = [] if profile['paused'] else [
            {key: row[key] for key in ('key', 'context', 'session_key', 'at', 'excerpt')}
            for row in profile['conversation_messages'].values()]
        contexts = sorted({row['context'] for row in sources}
                          | {r['scope'] for r in rules if r['scope'] != '*'})
        return {'version': (ROOT / 'VERSION').read_text().strip(),
                'subject_id': args.subject, 'revision': profile['revision'],
                'paused': profile['paused'], 'conversation_import_enabled': args.enable_conversations,
                'model_enabled':getattr(args,'enable_models',False),
                'configured_model':getattr(args,'model',None) if getattr(args,'enable_models',False) else None,
                'condition_values':CONDITION_VALUES,
                'contexts': contexts, 'rules': rules, 'dimensions': DIMENSIONS, 'statements': STATEMENTS,
                'sources': sorted(sources, key=lambda row: (row['at'], row['key']), reverse=True)}
    finally:
        db.close()


class WorkspaceHandler(BaseHTTPRequestHandler):
    server_version = 'KarmenWorkspace'
    sys_version = ''

    def log_message(self, *_args):
        pass  # Private request text and paths are not retained in an access log.

    def reply(self, status, data, content_type='application/json; charset=utf-8'):
        body = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=True).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'")
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def reject(self, code, message, status=403):
        self.reply(status, {'code': code, 'message': message})
        return False

    def boundary(self, api=False):
        hosts = self.headers.get_all('Host') or []
        expected = {'127.0.0.1:' + str(self.server.server_port),
                    'localhost:' + str(self.server.server_port)}
        if len(hosts) != 1 or hosts[0] not in expected:
            return self.reject('HOST_REJECTED', 'Use the local workspace address.')
        origin = self.headers.get('Origin')
        if origin is not None and origin != 'http://' + hosts[0]:
            return self.reject('ORIGIN_REJECTED', 'Cross-origin access is not allowed.')
        if self.headers.get('Sec-Fetch-Site') not in (None, 'same-origin', 'none'):
            return self.reject('ORIGIN_REJECTED', 'Cross-site access is not allowed.')
        if api:
            token = self.headers.get('X-Workspace-Token', '')
            if not secrets.compare_digest(token.encode(), self.server.token.encode()):
                return self.reject('TOKEN_REQUIRED', 'Reload this workspace to establish a local session.')
        return True

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self.boundary(api=path.startswith('/api/')):
            return
        if self.path == '/api/bootstrap':
            try:
                self.reply(200, bootstrap(self.server.args))
            except (Problem, OSError, ValueError, sqlite3.Error) as error:
                self.reject(getattr(error, 'code', 'STORAGE_ERROR'), str(error), 400)
        elif self.path.startswith('/api/model-jobs/') and '?' not in self.path:
            try:
                self.reply(200,self.server.jobs.read(self.path.removeprefix('/api/model-jobs/')))
            except Problem as error:
                self.reject(error.code,str(error),404 if error.code=='MODEL_JOB_MISSING' else 400)
        elif self.path in ASSETS:
            name, mime = ASSETS[self.path]
            body = (ROOT / 'web' / name).read_bytes()
            if name == 'index.html':
                body = body.replace(b'__WORKSPACE_TOKEN__', self.server.token.encode())
            self.reply(200, body, mime)
        else:
            self.reject('NOT_FOUND', 'This workspace route does not exist.', 404)

    def do_POST(self):
        if not self.boundary(api=True):
            return
        if self.path not in ('/api/call','/api/model-jobs'):
            self.reject('NOT_FOUND', 'This workspace route does not exist.', 404)
            return
        lengths = self.headers.get_all('Content-Length') or []
        if self.headers.get('Transfer-Encoding') or len(lengths) != 1 or not lengths[0].isdigit():
            self.reject('INVALID_LENGTH', 'Provide one bounded Content-Length.', 400)
            return
        length = int(lengths[0])
        if not 0 < length <= MAX_BODY:
            self.reject('BODY_TOO_LARGE', 'The request must contain at most 1 MB.', 413)
            return
        if self.headers.get('Content-Type', '').split(';', 1)[0].strip() != 'application/json':
            self.reject('JSON_REQUIRED', 'Send application/json.', 415)
            return
        self.connection.settimeout(5)
        try:
            raw = self.rfile.read(length)
            if len(raw) != length:
                raise ValueError('The request body was incomplete.')
            value = json.loads(raw)
            if self.path=='/api/model-jobs':
                self.reply(202,self.server.jobs.submit(value))
                return
            if not isinstance(value, dict) or set(value) != {'name', 'arguments'}:
                raise ValueError('Provide a tool name and its arguments only.')
            if not isinstance(value['name'], str) or value['name'] not in ALLOWED_TOOLS:
                self.reject('TOOL_NOT_ALLOWED', 'This tool is not available in the workspace.', 403)
                return
            result = dispatch(value['name'], value['arguments'], self.server.args)
            # Browser mutations need the new revision, not the entire private
            # profile. In particular, pausing must not return hidden excerpts.
            if isinstance(result, dict) and 'profile' in result:
                result = {**result, 'profile': {key: result['profile'][key] for key in ('revision', 'paused')}}
            self.reply(200, result)
        except (Problem, ValueError, TypeError, KeyError, OSError, sqlite3.Error) as error:
            code = getattr(error, 'code', 'INVALID_REQUEST')
            self.reject(code, str(error), 409 if code == 'STALE_REVISION' else 400)

    def do_OPTIONS(self):
        self.reject('METHOD_NOT_ALLOWED', 'Cross-origin requests are not available.', 405)


def make_server(args):
    identifier(args.subject)
    args.root = private_root(args.root)
    if getattr(args,'enable_models',False):
        if not isinstance(getattr(args,'model',None),str) or not args.model.strip():
            raise Problem('MODEL_REQUIRED','Use --model with --enable-models.')
        if type(getattr(args,'model_timeout',90)) is not int or not 1<=getattr(args,'model_timeout',90)<=300:
            raise Problem('INVALID_TIMEOUT','Use a model deadline from 1 to 300 seconds.')
    class LocalServer(ThreadingHTTPServer):
        def server_close(self):
            self.jobs.close()
            super().server_close()
    server = LocalServer(('127.0.0.1', args.port), WorkspaceHandler)
    server.daemon_threads = True
    server.args = args
    server.token = secrets.token_urlsafe(32)
    server.jobs = ModelJobs(args)
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--enable-conversations', action='store_true')
    parser.add_argument('--enable-models',action='store_true',help='Allow explicitly selected excerpts and tasks to be sent to the configured Codex account.')
    parser.add_argument('--model',help='A model available to the signed-in Codex account; required with --enable-models.')
    parser.add_argument('--system-proxy',action='store_true',help='Opt into the existing macOS loopback proxy for model child processes.')
    parser.add_argument('--model-timeout',type=int,default=90)
    parser.add_argument('--port', type=int, default=0)
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error('port must be between 0 and 65535')
    args.enable_observations = False
    args.workspace = str(ROOT)
    args.host_id = 'local-workspace'
    try:
        server = make_server(args)
        print(json.dumps({'url': 'http://127.0.0.1:' + str(server.server_port),
                          'subject': args.subject, 'version': (ROOT/'VERSION').read_text().strip()}), flush=True)
        try:
            server.serve_forever(poll_interval=.25)
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
    except (Problem, OSError, ValueError) as error:
        print(json.dumps({'code': getattr(error, 'code', 'ERROR'), 'message': str(error)}))
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
