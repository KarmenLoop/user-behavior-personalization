# Conversation learning tutorial — v0.6.0

[English](conversation-guide.en.md) · [中文](conversation-guide.zh-CN.md)

This walkthrough starts with actual conversation text, then reviews a preference, uses a working profile, retrieves a historical follow-up, and deletes the source. All exercises use synthetic data. Your own imports should contain only conversations you are authorized to process.

## 1. Download and install

Download the ZIP and `SHA256SUMS.txt` from [v0.5.1](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.6.0). Compare the ZIP's SHA-256 before extraction: `shasum -a 256` on macOS, `sha256sum` on Linux, or `Get-FileHash -Algorithm SHA256` in PowerShell.

Use Python 3.11+; there are no third-party Python runtime dependencies. In the extracted directory:

```sh
python3 --version
python3 -B scripts/check_package.py
python3 -B -m unittest discover -s tests -v
```

Windows may use `py -3.12` instead of `python3`. To create a portable skill copy, use `python3 scripts/install_skill.py --destination ../installed-skills/user-behavior-personalization`. The destination must not already exist. Keep the package together and the private data root outside Git.

## 2. Import a selected conversation

```sh
python3 scripts/learn_conversation.py --root ../private-profile --subject demo \
  --enable-conversations --input examples/conversations/sample.en.json
```

The command obtains the current revision, imports the chosen file, and prints import counts plus a portrait. It does not auto-confirm proposals. A subject is a host-bound identity, not a display name inferred from chat.

The JSON shape is:

```json
{
  "session_id": "release-planning-1",
  "context": "release-planning",
  "messages": [
    {
      "id": "message-1",
      "role": "user",
      "text": "From now on, include a rollback checklist in release plans.",
      "at": "2026-11-03T00:00:00Z"
    }
  ]
}
```

Use actual timestamps and stable source identifiers. `session_id` and message `id` use 1–80 ASCII letters, numbers, hyphens, or underscores. Messages must be chronological. Each batch accepts at most 100 messages, each with at most 4,000 characters. Roles are `user`, `assistant`, `system`, or `tool`; only user messages become retained user evidence.

For JSONL, put one message object on each line and supply the session and context:

```sh
python3 scripts/learn_conversation.py --root ../private-profile --subject owner \
  --enable-conversations --format jsonl --session-id project-session-1 \
  --context release-planning --input /path/to/selected-messages.jsonl
```

To append, import the original session prefix plus new messages in order. Re-importing identical content is deduplicated. Rewriting a stored user message, changing the context, or reordering the original history is rejected. This prevents an updated export from silently changing the evidence behind an accepted preference.

## 3. Complete the learning and deletion cycle
For a one-command synthetic lifecycle, run:

```sh
python3 -B scripts/demo_conversations.py --root ../new-conversation-demo
```

It exercises actual local processes, including model-proposal staging without a provider call. Use a new directory.


Run this Python block from the package directory. Each write reads the current revision; the exercise does not rely on a hard-coded counter.

```python
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile

# Run from the extracted package. All messages here are synthetic.
private = Path(tempfile.mkdtemp(prefix="conversation-learning-"))
base = [sys.executable, "-B", str(Path.cwd() / "scripts/host.py"),
        "--root", str(private), "--subject", "demo", "--enable-conversations"]
context = "database-release"

def call(tool, arguments):
    result = subprocess.run(base + ["call", tool], input=json.dumps(arguments),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)

def revision():
    return call("profile_read", {"context": context})["revision"]

now = dt.datetime.now(dt.timezone.utc)
query = "Check the database schema migration plan."
followup = "Write a rollback checklist for the database migration."
conversations = []
for session in (1, 2):
    when = now - dt.timedelta(days=3-session)
    text = [query, followup]
    if session == 1:
        text.insert(0, "From now on, include a rollback checklist in release plans.")
    conversation = {
        "session_id": f"release-{session}", "context": context,
        "messages": [{"id": f"message-{i}", "role": "user", "text": body,
                      "at": (when + dt.timedelta(minutes=i)).isoformat()}
                     for i, body in enumerate(text)]
    }
    conversations.append(conversation)
    call("conversation_import", {"expected_revision": revision(),
                                 "conversation": conversation})

portrait = call("profile_portrait", {"context": context})
print(json.dumps(portrait, indent=2))
proposal = next(p for p in portrait["pending_preferences"]
                if p["category"] == "workflow")
assert call("profile_read", {"context": context})["rules"] == []

# Synthetic approval for this exercise; real use needs the user's actual decision.
reviewed = call("profile_proposal_review", {
    "expected_revision": revision(), "proposal_id": proposal["id"],
    "decision": "accept", "source_id": "demo-user-review-1"
})
assert call("profile_read", {"context": context})["rules"]

forecast = call("profile_forecast", {"context": context, "request": query})
print(json.dumps(forecast, indent=2))
assert forecast["status"] == "suggested"
assert forecast["candidates"][0]["suggestion"] == followup

# Forget the source of the confirmed rule and one supporting forecast session.
call("profile_forget_conversation", {"expected_revision": revision(),
                                     "session_id": "release-1"})
assert call("profile_read", {"context": context})["rules"] == []
assert call("profile_forecast", {"context": context,
                                 "request": query})["status"] == "insufficient_evidence"
call("profile_reset", {"expected_revision": revision()})
assert call("profile_read", {"context": context})["paused"] is True
print("Exercise complete. Private synthetic store:", private)
```

This example succeeds because two sessions contain the same preceding request and follow-up. It demonstrates the executable path, not performance on paraphrases. The frozen diagnostic in [evaluation](evaluation.md) tests separate, unseen queries and retains misses.

## 4. Read the portrait

`profile_portrait({"context": "release-planning"})` returns:

| Field | How to use it |
|---|---|
| `confirmed_preferences` | Preferences the user has reviewed or explicitly saved; suitable for contextual recall. |
| `pending_preferences` | Proposed communication, workflow, goal, or constraint statements with source quotes. |
| `writing_observations` | Message/session counts, median length, lists, questions, language mix, and source examples. |

A custom term, a detailed release ritual, or a stated learning goal can remain open text. The extractor looks for explicit English/Chinese cues. It does not require fitting them into the original six observation labels. It can miss indirect requests; a missed sentence is not evidence that the person lacks that preference.

Writing statistics describe the imported user's messages. They do not automatically tell the assistant to imitate that style. If a user asks for a matching style, inspect examples together and confirm the desired response rules.

## 5. Review or correct a proposal

Read the portrait, then call `profile_proposal_review` with its current `expected_revision`, the proposal's `id` as `proposal_id`, a genuine review `source_id`, and `decision: "accept"` or `"reject"`.

To replace a conflicting accepted rule, also supply `replace_rule_id` for that existing rule. A free-text correction is not semantically merged automatically. Review the old and proposed statements before replacing one; unrelated preferences should remain intact.

An explicit cue produces a proposal immediately. The three-session rule belongs to the older structured-feedback path, not this explicit-language extraction path. See [structured feedback](structured-feedback.en.md) if you want to keep using `profile_observe` and its fixed dimensions.

## 6. Ask what usually follows

Call `profile_forecast` with an exact context and the current request text. Inspect `status`, `candidates`, each candidate's `suggestion`, and its evidence containing `previous_request` and `next_request`.

- `suggested`: a leading historical follow-up has enough consistent support to offer.
- `insufficient_evidence`: too few matched sessions, stale evidence, or insufficient support.
- `conflicted`: competing follow-ups prevent a clear suggestion.

Candidates can be returned for inspection even when status is not `suggested`; do not present those as an accepted prediction. The method compares English word/subword and Chinese character patterns, considers recency, and gives each session at most one contributing match. Returned wording comes from a real retained request, not a newly generated plan. It never executes that request.

## 7. Add an optional model-assisted pass

`profile_model_context` selects up to 20 recent retained user excerpts for a context and supplies an extraction contract. Your host may send this context to its authorized model. The local tool sends nothing itself.

Return proposals through `profile_model_propose`. Each item needs `statement`, `scope`, `category`, and `evidence` containing a stored `source_key` and an exact retained `quote`. The adapter checks source existence, scope, quote matching, input bounds, and basic unsafe-content patterns. Passing those checks establishes traceability, not that the model interpreted the person correctly. Every item remains pending until `profile_proposal_review` records the user's decision.

See [host integration](host-integration.md) for the data flow and DeepSeek boundary. Do not send API keys or hidden model reasoning into the profile.

## 8. Connect and use a host

```sh
python3 scripts/host.py --root ../private-profile --subject owner \
  --workspace /path/to/project --enable-conversations --install-host codex install
```

Choose `--install-host cursor` for Cursor. Add `--enable-observations` separately if you also want the structured-feedback path. Reload and approve the server, verify its 25 tools, and make an actual call. Existing entries are preserved; review a duplicate-entry error instead of silently installing a second server.

Accepted rules can be loaded through `profile_read`, `scripts/run_host.py`, or `scripts/build_context.py`. The wrapper takes `--context`, `--host`, `--workspace`, and `--prompt`; the context builder takes `--context` and `--task-file`. The wrapper streams output and saves metadata-only receipts. Codex receives the composed prompt on stdin; the current Cursor CLI path uses a positional argument, visible to same-user process inspection.

## 9. Inspect, pause, and delete

`profile_pause` suppresses ordinary use and learning. Export and deletion remain available. `profile_forget_conversation` takes `session_id` and removes the session's messages and dependent proposals, rules, writing contributions, and transitions. It does not connect a request before a deleted message to a request after it. `profile_reset` clears profile content and ends paused, retaining minimal hashes against replay.

The store is bounded to 400 user records and 80 sessions. It retains up to 600 sanitized characters per user excerpt plus features and hashes. Delete evidence you no longer need; do not disguise the same source with new IDs to bypass limits or forgetting. External backups, exports, terminal output, and provider histories remain separate copies. See [privacy controls](privacy-and-memory-control.md).


To remove selected messages, call `profile_forget_messages` with the current revision and a nonempty `source_keys` list from the portrait or model context. It removes dependent proposals, rules, writing contributions, and transitions. Other messages in the session remain; no new transition is invented across a gap.

The portrait also compares request-length observations in the last 30 days with days 31–90, only when each window has at least three sessions. This describes a possible change in writing behavior; it does not change a response preference.

## 10. Evaluate before relying on suggestions

Run `python3 -B scripts/evaluate_conversations.py` for the frozen synthetic diagnostic. Read coverage, conditional precision, abstentions, failed case IDs, and extraction misses separately. A result on eleven queries is a diagnostic, not proof of broad accuracy. Compare the actual response before and after an accepted preference, then ask whether it helped with the task.
