# Automatic learning from a selected feed — v0.5.1

[English](automatic-learning.en.md) · [中文](automatic-learning.zh-CN.md)

You choose the source. The importer reads new complete records, and an experimental habit learner looks for supported recurring feedback in retained user excerpts. You still review what becomes a lasting preference. The selected-file importer and task resolver work independently of how well the learner recognizes a particular phrase.

## What is automatic

The foreground watcher reads newly appended lines from one selected file. `conversation_import` updates the existing store; `profile_habits` discovers supported correction cues without requiring a manually assigned label for each message. Three independent sessions, recency, and counterevidence determine whether a habit is ready to review. Duplicate input and repetition inside one session do not add independent support.

Habit discovery currently maps supported cues to the existing collaboration dimensions: response length, structure, teaching, initiative, workflow next step, and language. It does not learn arbitrary semantic concepts from every sentence. Open-text preferences, custom terminology, goals, and constraints use the separate explicit-proposal path; an optional host-model bridge can stage additional sourced proposals.

## Two JSONL formats serve different purposes

| Command | One line contains |
|---|---|
| `learn_conversation.py --format jsonl` | One message; session and context come from command arguments. |
| `watch_conversations.py` | One complete conversation object with `session_id`, `context`, and `messages`. |

A watcher record looks like this, written on one line and terminated by a newline:

```json
{"session_id":"writing-1","context":"writing","messages":[{"id":"feedback-1","role":"user","text":"Too long. Please keep it brief.","at":"2026-11-03T00:00:00Z"}]}
```

Use real timestamps and stable IDs for real data. To extend an existing conversation, append a new snapshot containing its original ordered prefix plus new messages. Never rewrite the bytes already processed in the feed or alter a previously stored user message.

## Run it

```sh
python3 -B scripts/watch_conversations.py --root ../private-profile --subject owner \
  --input /path/to/selected.jsonl --enable-conversations
```

The default poll interval is two seconds; `--interval` accepts 1–60 seconds. Add `--once` for one read. Stop foreground watching with Ctrl+C. No service or scheduled task is installed.

The workspace can use the same root and subject. Refresh it to review newly imported sources and habits. The watcher does not choose a user identity from the file, read another host's database, or grant itself access to account histories.

## Execute a three-session example

```python
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile

# Run from the package directory. This writes synthetic data only.
area = Path(tempfile.mkdtemp(prefix="selected-feed-demo-"))
feed, profile = area / "selected.jsonl", area / "private-profile"
feed.touch()
context = "writing"
now = dt.datetime.now(dt.timezone.utc)
for session in range(1, 4):
    conversation = {
        "session_id": f"feedback-{session}", "context": context,
        "messages": [{"id": "correction", "role": "user",
                      "text": "Too long. Please keep it brief.",
                      "at": (now - dt.timedelta(days=session)).isoformat()}]
    }
    with feed.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(conversation) + "\n")
    subprocess.run([sys.executable, "-B", "scripts/watch_conversations.py",
                    "--root", str(profile), "--subject", "demo",
                    "--enable-conversations", "--input", str(feed), "--once"],
                   check=True)

result = subprocess.run(
    [sys.executable, "-B", "scripts/host.py", "--root", str(profile),
     "--subject", "demo", "call", "profile_habits"],
    input=json.dumps({"context": context}), text=True, capture_output=True, check=True)
habits = json.loads(result.stdout)
assert any(item["status"] == "ready_to_review" for item in habits["candidates"])
print(json.dumps(habits, indent=2))
print("Synthetic files:", area)
```

This example starts a fresh importer for each appended record, exercising the saved cursor across restarts. It leaves a reviewable habit, not an accepted rule. Inspect the returned quotes and confirm only if they reflect the intended preference. For Chinese feedback, replace the synthetic text with `太长了，请简短一点。`.

## Status and recovery

| Status or error | Meaning and next step |
|---|---|
| `caught_up` | All complete records currently available have been processed. |
| `waiting_for_line` | The last record lacks its ending newline. Finish writing it; do not treat a partial record as imported. |
| `paused` | The profile is paused. The importer does not advance past unread data; resume only when appropriate. |
| `INVALID_JSONL` / rejected import | The first failed complete record remains unconsumed. Fix the unprocessed record or investigate its source; later records are not silently skipped. |
| `FEED_HISTORY_CHANGED` | Already processed bytes changed or were truncated. Restore the original prefix; do not reset the cursor to disguise the change. |
| `WATCH_BUSY` | Another importer holds the feed claim. If it is stale, verify the owning process has stopped before deliberate recovery. |

Feed files are bounded to 4 MiB, individual records to 1 MB, and selected feeds to 16 per subject. Rotate deliberately after reviewing retained state; a new path is a new selected feed, not permission to replay forgotten sources. The profile also enforces its conversation/message limits.

## Review, correction, and retention

Use `profile_habits` to inspect status, source quotes, support, and opposition. `profile_habit_review` accepts or dismisses a currently reviewable candidate using the actual user's decision. Current explicit preferences and corrections take precedence.

Imported text remains bounded under the existing conversation retention policy. Pause stops normal learning. Deleting source evidence cascades to dependent habits, rules, prepared plans, and ratings. Watcher cursor metadata survives reset so already processed content is not accidentally re-imported; it records progress and hashes, not the conversation body. Your selected source file itself is external and is not deleted by the profile controls.

The current learner covers 22/22 positive cases on exposed regression sets, but its first unseen `fresh-v4` run covered only 1/8 (English 1/4, Chinese 0/4), with no false offers on 8 negative controls. The initial 0/6 failure is also retained. This is experimental cue recognition, not general understanding of user behavior. The easy example above verifies an import-and-review path; see [current evaluation](evaluation.md) for the separate language-quality evidence.
