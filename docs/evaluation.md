# Evaluation — v0.3.0

[English](evaluation.md) · [中文](evaluation.zh-CN.md)

Saving a preference, loading it into a host, following it in an answer, and making the experience better are separate outcomes. Keep that distinction in every report.

## Reproduce local behavior

Use Python 3.11+ in the extracted package:

```sh
python3 -B scripts/check_package.py
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_publication.py
python3 -B scripts/demo_learning.py --root ../new-synthetic-acceptance
```

The demo requires a new private directory. It runs actual CLI processes and SQLite writes with synthetic input: observation, review, recall after restart, context and subject separation, pause, export, deletion, replay blocking, and reset. It leaves a paused profile with content cleared and suppression hashes retained. It does not call a model.

## Acceptance matrix

| Check | Evidence to record |
|---|---|
| Explicit preference | New source, current revision, persisted rule, subsequent matching recall |
| Context boundary | `art` does not match `cartography`; a different subject sees no rule |
| Duplicate input | Replaying one event does not create more support |
| Session independence | Repeated events in one session do not meet the three-session threshold |
| Conflicting feedback | Counterevidence is shown; no unreviewed preference enters recall |
| Recency | Old evidence decays or leaves the 90-day window; readiness requires recent support |
| Stale review | Changing evidence or revision invalidates an older review |
| Correction | A new explicit correction replaces the appropriate default |
| Forget | Affected history, evidence, derived rules, and managed artifacts are removed; replay is blocked |
| Pause / reset | Ordinary use stops; export/deletion still work; reset ends paused |
| Host transport | Actual initialize, tools/list, and tool calls through an MCP pipe |
| Model response | A real answer applies a harmless preference and changes after correction |
| User benefit | The user reports whether the change helps across comparable tasks |

Use synthetic examples in public evidence. A support score is not an “understanding score,” and passing deterministic tests does not establish psychological validity.

## Host attempts during this release work

- Actual local MCP pipe calls and generated Codex/Cursor configuration checks were exercised. They establish local transport/configuration behavior, not a successful model answer.
- The Codex wrapper loaded the saved rule and revision, but the model request did not complete within the configured 55-second deadline. The wrapper returned exit 124 and reaped its owned child. **Model-response acceptance remains unverified.**
- The Cursor wrapper loaded the same saved preference, then exited with an authentication-required message. **No model response was obtained.**
- The DeepSeek-style request payload was built locally. **No live DeepSeek API call was run.**
- Native desktop GUI behavior was not tested. Any v0.2.0 live-host result remains historical evidence for that version.

This table preserves unsuccessful and unrun steps instead of treating configuration as a substitute. Consult the actual release checks and notes for the final tested revision and platform results.

## Test usefulness with a person

Start with a small set of representative tasks: a status update, a code review, a learning exercise, and a changed preference. Agree on what would count as improvement, such as fewer repeated formatting corrections. Record actual feedback, avoid inventing approval from silence, and retain cases where personalization makes the answer worse.

Do not infer a general personality trait from one task. Do not use accuracy on an optional lesson quiz as a measure of intelligence or as consent to record learning behavior. A user can skip the exercise or turn off memory.

## Release checks

Verify the exact commit, version, archive SHA-256, bilingual document links, diagram hashes, source hashes, extracted-package behavior, and actual CI results. The packaged license and notices must stay intact. Keep failures and unverified hosts visible. Publish only synthetic examples and original diagrams, never real profiles or credentials.
