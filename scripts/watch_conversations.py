#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Import complete snapshots appended to one explicitly selected JSONL file.

Run in the foreground. No history crawler, background installation or provider
call is performed. Each line is a full conversation_import conversation object.
Minimal cursor metadata survives profile reset to avoid accidental replay.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import time

from host_support import Problem, atomic, identifier, need, private_root, stamp
from learning import digest

MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_RECORD_BYTES = 1000000
MAX_FEEDS = 16


def _directory(root, subject, create=True):
    identifier(subject)
    root = private_root(root)
    paths = [root, root / 'watchers', root / 'watchers' / digest(subject)]
    for path in paths:
        need(not path.is_symlink(), 'UNSAFE_PATH', 'Refusing a symbolic-link watcher directory.')
        if create:
            path.mkdir(exist_ok=True, parents=True, mode=0o700)
            os.chmod(path, 0o700)
        need(not path.exists() or path.is_dir(), 'UNSAFE_PATH', 'Watcher metadata needs a private directory.')
    return paths[-1]


def _state(path):
    need(not path.is_symlink(), 'UNSAFE_PATH', 'Refusing a symbolic-link watcher cursor.')
    if not path.exists():
        return None
    need(path.is_file() and path.stat().st_size <= 16000, 'INVALID_CURSOR', 'Watcher cursor is invalid.')
    try:
        value = json.loads(path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError):
        raise Problem('INVALID_CURSOR', 'Watcher cursor is not valid JSON.')
    need(isinstance(value, dict) and value.get('schema_version') == 1 and
         type(value.get('offset')) is int and value['offset'] >= 0 and
         type(value.get('lines')) is int and value['lines'] >= 0 and
         type(value.get('imported_records')) is int and value['imported_records'] >= 0 and
         isinstance(value.get('prefix_sha256'), str) and len(value['prefix_sha256']) == 64,
         'INVALID_CURSOR', 'Watcher cursor fields are invalid.')
    return value


def read_watch_status(root, subject):
    """Read bounded local metadata, without opening any source file."""
    directory = _directory(root, subject, create=False)
    if not directory.exists():
        return []
    paths = sorted(directory.glob('*.json'))
    need(len(paths) <= MAX_FEEDS, 'WATCH_LIMIT', 'Too many selected feeds.')
    return [value for path in paths if (value := _state(path)) is not None]


def _read_source(path):
    try:
        selected = path.lstat()
    except OSError as error:
        raise Problem('INPUT_UNAVAILABLE', 'The selected conversation file is unavailable.') from error
    # Windows may refuse to open a directory before fstat can classify it.
    # lstat also rejects links without following them, including broken links.
    need(stat.S_ISREG(selected.st_mode), 'UNSAFE_INPUT', 'Select a regular JSONL file, not a symbolic link or directory.')
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise Problem('INPUT_UNAVAILABLE', 'The selected conversation file is unavailable.') from error
    try:
        metadata = os.fstat(descriptor)
        # The pre-open check does not replace checking the opened descriptor.
        need(stat.S_ISREG(metadata.st_mode), 'UNSAFE_INPUT', 'Select a regular JSONL file.')
        need(metadata.st_size <= MAX_FILE_BYTES, 'INPUT_TOO_LARGE', 'Selected feed exceeds 4 MiB.')
        stream = os.fdopen(descriptor, 'rb')
    except BaseException:
        os.close(descriptor)
        raise
    with stream:
        raw = stream.read(MAX_FILE_BYTES + 1)
    need(len(raw) <= MAX_FILE_BYTES, 'INPUT_TOO_LARGE', 'Selected feed exceeds 4 MiB.')
    return raw


def process_once(args):
    """Consume each complete new line once; stop before the first rejected line.

    Returns a metadata status object. A nonblocking directory claim serializes
    this subject/feed. If a process dies, its stale claim is left for deliberate
    operator recovery, rather than stealing an unknown active writer's lock.
    """
    need(getattr(args, 'enable_conversations', False), 'CONVERSATIONS_DISABLED',
         'Enable authorized conversation import before selecting a feed.')
    identifier(args.subject)
    selected = Path(args.input).expanduser().absolute()
    directory = _directory(args.root, args.subject)
    feed_id = digest(str(selected))
    path = directory / (feed_id + '.json')
    claim = directory / (feed_id + '.lock')
    need(not claim.is_symlink(), 'UNSAFE_PATH', 'Refusing a symbolic-link watcher lock.')
    try:
        claim.mkdir(mode=0o700)
    except FileExistsError as error:
        raise Problem('WATCH_BUSY', 'Another importer owns this feed; inspect a stale lock only after stopping its owner.') from error
    try:
        cursor = _state(path)
        if cursor is None:
            need(len(list(directory.glob('*.json'))) < MAX_FEEDS, 'WATCH_LIMIT', 'At most 16 selected feeds are supported per subject.')
            cursor = {'schema_version': 1, 'feed_id': feed_id, 'filename': selected.name[:200],
                      'offset': 0, 'lines': 0, 'prefix_sha256': hashlib.sha256(b'').hexdigest(),
                      'imported_records': 0}
        need(cursor.get('feed_id') == feed_id, 'INVALID_CURSOR', 'Cursor does not belong to this selected feed.')

        def save(status, code=None):
            cursor.update(status=status, last_code=code, updated_at=stamp())
            atomic(path, json.dumps(cursor, ensure_ascii=True, indent=2) + '\n')
            return dict(cursor)

        try:
            # Import lazily to keep read_watch_status usable from a web host
            # without introducing an import cycle through host.dispatch.
            from host import dispatch
            current = dispatch('profile_read', {'context': 'selected-feed'}, args)
            if current['paused']:
                return save('paused')
            raw = _read_source(selected)
            offset = cursor['offset']
            need(offset <= len(raw) and hashlib.sha256(raw[:offset]).hexdigest() == cursor['prefix_sha256'],
                 'FEED_HISTORY_CHANGED', 'Processed bytes changed or were truncated. Preserve the original feed prefix.')
            while offset < len(raw):
                end = raw.find(b'\n', offset)
                if end < 0:
                    need(len(raw) - offset <= MAX_RECORD_BYTES, 'RECORD_TOO_LARGE', 'Incomplete record exceeds 1 MB.')
                    return save('waiting_for_line')
                need(end + 1 - offset <= MAX_RECORD_BYTES, 'RECORD_TOO_LARGE', 'A conversation record exceeds 1 MB.')
                try:
                    value = json.loads(raw[offset:end].decode('utf-8'))
                except UnicodeDecodeError as error:
                    raise Problem('INVALID_UTF8', 'A complete record is not UTF-8.') from error
                except ValueError as error:
                    raise Problem('INVALID_JSONL', 'A complete record is not valid JSON.') from error
                current = dispatch('profile_read', {'context': 'selected-feed'}, args)
                if current['paused']:
                    return save('paused')
                imported = dispatch('conversation_import', {'expected_revision': current['revision'], 'conversation': value}, args)
                offset = end + 1
                cursor.update(offset=offset, lines=cursor['lines'] + 1,
                              prefix_sha256=hashlib.sha256(raw[:offset]).hexdigest(),
                              imported_records=cursor['imported_records'] + int(not imported.get('replayed', False)))
                save('importing')
            return save('caught_up')
        except (Problem, OSError, ValueError) as error:
            code = getattr(error, 'code', 'WATCH_ERROR')
            save('error', code)
            raise
    finally:
        claim.rmdir()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', required=True)
    parser.add_argument('--subject', required=True)
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--enable-conversations', action='store_true')
    parser.add_argument('--once', action='store_true')
    parser.add_argument('--interval', type=float, default=2, help='Polling seconds, from 1 to 60; foreground only.')
    args = parser.parse_args()
    args.workspace = '.'
    args.host_id = 'selected-feed'
    args.enable_observations = False
    try:
        need(1 <= args.interval <= 60, 'INVALID_INTERVAL', 'Choose a polling interval from 1 to 60 seconds.')
        while True:
            result = process_once(args)
            print(json.dumps(result, ensure_ascii=True), flush=True)
            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        return 0
    except (Problem, OSError, ValueError) as error:
        print(json.dumps({'code': getattr(error, 'code', 'WATCH_ERROR'),
                          'message': str(error)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
