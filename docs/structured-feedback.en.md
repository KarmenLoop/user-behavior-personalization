# User Behavior Personalization v0.6.0 structured feedback tutorial

[English](structured-feedback.en.md) · [中文](structured-feedback.zh-CN.md)

Start with the local exercise below. It uses synthetic feedback and no model account. Then connect one host and verify an actual response before relying on it.

## 1. Download and check the package

Get the ZIP and `SHA256SUMS.txt` from [v0.5.1](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.6.0). Compare the ZIP's SHA-256 with the published file before extracting. On macOS, use `shasum -a 256`; on Linux, `sha256sum`; in PowerShell, `Get-FileHash -Algorithm SHA256`.

Use Python 3.11 or newer. The adapter has no third-party Python dependencies. Open a terminal in the extracted package:

```sh
python3 --version
python3 -B scripts/check_package.py
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_publication.py
```

Windows installations may use `py -3.12` instead of `python3`. Use the same interpreter for installation, tools, and the MCP entry. These checks exercise local code and publication consistency; they do not contact a model.

To copy the portable package to a new host-selected directory:

```sh
python3 scripts/install_skill.py --destination ../installed-skills/user-behavior-personalization
```

The destination must not already exist. Keep `SKILL.md`, `scripts/`, `references/`, and `assets/` together. Never use the public checkout as a private profile directory.

## 2. Complete a local learning cycle

For a single-command version of the same synthetic exercise:

```sh
python3 -B scripts/demo_learning.py --root ../new-synthetic-demo
```

Choose a destination that does not exist. This launches actual local CLI processes; it is not a model-based effectiveness test.


The following Python block is a complete exercise. Save it outside the package or paste it into Python while your working directory is the extracted package. It reads the revision before each write instead of guessing which version comes next.

```python
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import tempfile

# Run from the extracted package. This store contains synthetic data only.
package = Path.cwd()
private = Path(tempfile.mkdtemp(prefix="personalization-demo-"))
command = [sys.executable, "-B", str(package / "scripts/host.py"),
           "--root", str(private), "--subject", "demo",
           "--enable-observations"]

def call(tool, arguments):
    result = subprocess.run(command + ["call", tool],
                            input=json.dumps(arguments), text=True,
                            capture_output=True, check=True)
    return json.loads(result.stdout)

def revision():
    return call("profile_read", {"context": "code-review"})["revision"]

# Explicit requests do not need three observations.
call("profile_correct", {"expected_revision": revision(), "rule": {
    "id": "status-length", "statement": "Keep status updates concise.",
    "scope": "status-update", "source_id": "demo-explicit-1",
    "source_summary": "Synthetic user asked for concise status updates.",
    "kind": "explicit", "dimension": "response_length", "value": "concise"
}})
assert call("profile_read", {"context": "code-review"})["rules"] == []

# Three distinct sessions, not three copies of one message.
for day in (3, 2, 1):
    occurred = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=day)
    call("profile_observe", {"expected_revision": revision(), "event": {
        "id": f"demo-event-{day}", "source_id": f"demo-feedback-{day}",
        "session_id": f"demo-session-{day}", "context": "code-review",
        "dimension": "structure", "value": "conclusion_first",
        "signal": "positive", "occurred_at": occurred.isoformat()
    }})

insights = call("profile_insights", {"context": "code-review"})
print(json.dumps(insights, indent=2))
candidate = next(c for c in insights["candidates"]
                 if c["status"] == "ready_to_review")
assert call("profile_read", {"context": "code-review"})["rules"] == []

# Synthetic confirmation for this exercise only.
# A real integration must ask the user and use the actual review source.
accepted = call("profile_review", {
    "expected_revision": revision(), "candidate_id": candidate["candidate_id"],
    "decision": "accept", "source_id": "demo-user-confirmation-1"
})
assert call("profile_read", {"context": "code-review"})["rules"]

call("profile_pause", {"expected_revision": revision(), "paused": True})
assert call("profile_read", {"context": "code-review"})["rules"] == []
export = call("profile_export", {})
print("Private export:", export["path"])

# Deletion remains available while paused.
call("profile_forget", {"expected_revision": revision(),
                        "rule_id": accepted["rule_id"]})
call("profile_reset", {"expected_revision": revision()})
assert call("profile_read", {"context": "code-review"})["paused"] is True
print("Demo complete. Private demo directory:", private)
```

Expected behavior: a scoped explicit preference is saved immediately; three independent feedback events produce a reviewable candidate; ordinary recall stays empty for that context until confirmation; pause suppresses recall; export and deletion remain available; reset ends paused. The local demo directory is printed so you can inspect or remove this synthetic store.

A new `source_id` must identify a genuinely new user statement or feedback item. Changing an identifier to bypass a forgotten-source error defeats the control; a host must not do that. Source and session IDs are host attestations, not cryptographic proof that three people or sessions existed.

## 3. Choose dimensions and contexts

| Dimension | Values | Example context |
|---|---|---|
| `response_length` | `concise`, `balanced`, `detailed` | `status-update` |
| `structure` | `conclusion_first`, `steps`, `examples`, `code_first`, `bullets` | `code-review` |
| `teaching` | `explain_back`, `worked_example`, `practice` | `learn-python` |
| `initiative` | `ask_first`, `suggest_next` | `project-planning` |
| `workflow_next_step` | `clarify`, `plan`, `implement`, `test`, `review`, `summarize` | `after-implementation` |
| `language` | `en`, `zh` | `technical-explanation` |

Use stable, narrow context names. Matching is exact and case-insensitive. A global explicit rule uses `scope: "*"`; observations should describe the specific context in which feedback occurred. A temporary request is not a lasting observation by default. Use an explicit rule with a timezone-qualified `expires_at` when the user authorizes a temporary stored preference.

Negative feedback uses `signal: "negative"` for the dimension and value the user actually rejected. Do not turn “that example was wrong” into a rejection of examples in general. Silence, assistant output, a quoted colleague, or a generated explanation of the user's motives is not feedback from the user.

## 4. Connect Codex or Cursor

Create the intended project first. Choose a private profile root outside Git and bind an opaque subject ID to the actual user in your host setup.

```sh
python3 scripts/host.py --root ../private-profile --subject owner \
  --workspace /path/to/project --enable-observations --install-host codex install
python3 scripts/host.py --root ../private-profile --subject owner \
  --workspace /path/to/project --enable-observations --install-host cursor install
```

Omit `--enable-observations` if you only want explicitly saved rules. It is a server setting, not a permission a tool argument can grant. Existing server entries are preserved: if installation reports an existing entry, inspect and update it deliberately rather than adding a duplicate server.

Reload the chosen host and approve this specific server. Check `tools/list`, then `profile_read`. Verify the subject and root, save a synthetic preference, and read it from the second host. Sharing a store does not link online accounts automatically.

For each host's next model turn, ask a harmless question with a clear style preference. Check whether the preference was loaded, whether the actual answer followed it, and whether correction changes the next response. Configuration, MCP tool discovery, and model behavior are separate acceptance steps.

## 5. Load preferences before a new CLI task

Write a private task file, then invoke the wrapper:

```sh
python3 scripts/run_host.py --root ../private-profile --subject owner \
  --context code-review --host codex --workspace /path/to/project \
  --prompt /path/to/private-task.txt
```

Use `--host cursor` for Cursor CLI. The wrapper loads confirmed rules before starting the host. It streams host output to the console and stores a subject-bound metadata receipt, not raw prompt or model-output files. Terminal history, host logs, and provider retention remain outside this store. The wrapper creates no recurring job or per-turn hook in an already-open chat.

## 6. Build a model API request

```sh
python3 scripts/build_context.py --root ../private-profile --subject owner \
  --context code-review --task-file /path/to/private-task.txt
```

This prints JSON with `messages` and local `personalization` metadata. Your own DeepSeek-style chat client can send the **`messages` value** in its request. Do not send the entire output as if it were the provider's request schema. The command makes no network call and requires no API key. Redirected output contains the task and selected rules: treat that file as private and clean it up separately.

DeepSeek's chat API is a model endpoint, not a direct MCP client. A tool-using integration needs its own allowlisted tool bridge, current revisions, response validation, and user authorization. See [host integration](host-integration.md).

## 7. Inspect, correct, forget, and reset

- Use `profile_insights` to inspect candidates. A support score is an engineering heuristic; it is not psychological certainty.
- Use `profile_correct` with the existing rule ID and a new source to replace an explicit preference. Include `dimension` and `value` together when you want structured conflict handling.
- Use `profile_review` with `decision: "reject"` to dismiss a candidate. New evidence can justify a later review; rejection is not agreement.
- Use `profile_forget_observations` with a nonempty `observation_ids` list to remove selected evidence and dependent learned rules.
- Use `profile_forget` to remove a rule and its linked learning evidence. Previously copied exports and provider histories require separate action.
- Use `profile_reset` to remove profile content and pause future ordinary use. Minimal source hashes remain to suppress replay; it is not a physical disk wipe.

All writes require the current `expected_revision`. Do not retry a stale write blindly. Read again, review what changed, and decide whether the intended update still makes sense.

## 8. Understand failures and limits

| Symptom | What to check |
|---|---|
| `STALE_REVISION` | Another write changed the profile. Re-read before deciding what to save. |
| Observation is disabled | Start the approved server with `--enable-observations`; do not infer consent from a conversation. |
| `MEMORY_PAUSED` | Resume only at the user's request. Inspection and deletion still work. |
| Source was forgotten | Do not replay that source with a new identifier. Obtain genuinely new feedback if appropriate. |
| No candidate is ready | Check independent sessions, context, recency, counterevidence, and an existing explicit preference. |
| A scope stopped matching after upgrade | Current versions use exact labels. `art` intentionally no longer matches `cartography`. |
| The observation limit is reached | Review and remove unnecessary evidence; the adapter does not silently discard it. |
| A host ignores a saved preference | Check actual tool loading or use the wrapper; a stored rule is not proof of model compliance. |

For advanced use, compare behavior across contexts, test a changed preference, challenge a candidate with counterevidence, and confirm that deletion prevents reappearance. Record results with the [evaluation guide](evaluation.md). Never use test pass counts as a score for how well the system understands a person.
