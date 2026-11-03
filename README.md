# User Behavior Personalization

[English](README.md) · [中文](README.zh-CN.md) · **v0.5.1**

You have asked for shorter answers three times. The next task needs a detailed explanation. Your assistant should handle both.

This local workspace turns recurring feedback into preferences you can review, shows exactly how those preferences change the next task's prompt, and lets you record whether the change helped. A one-time choice leaves your saved habits intact.

![Actual v0.5.1 task preview with the shared evidence-first judgment policy](docs/images/judgment-v0.5.1.en.jpg)

*Actual v0.5.1 workspace with a synthetic task. A concise-answer preference changes presentation; the judgment rules still require evidence and counterexample checks.*

[Download](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.5.1) · [Full walkthrough](docs/tutorial.en.md) · [Automatic learning](docs/automatic-learning.en.md) · [Current evaluation](docs/evaluation.md)

## Try the complete loop

Python **3.11+** is required. Download, verify, and extract the release, then run:

```sh
python3 -B scripts/workspace.py --root ../private-profile --subject demo --enable-conversations
```

Open the printed `http://127.0.0.1:...` URL. The workspace runs on your computer; no model account is needed.

1. Select **Try a synthetic example**. Three separate conversations contain “Too long. Please keep it brief.”
2. Open the evidence for the proposed concise-answer habit, then choose **Keep this preference**.
3. Open **Shape the next task**, enter a task, and preview the saved preference in the actual prompt.
4. Choose a detailed answer under **Just for this task**. Preview again: the temporary choice replaces the saved brevity rule for this task, without changing the profile.
5. Save the plan, then record whether reviewing the prompt helped. After using a real response through your host, record that separately.

## What makes the difference

**Recurring corrections become usable habits.** Import selected conversations or follow an append-only file. The learner finds supported English and Chinese feedback cues across independent sessions, with source quotes and counterevidence. A direct preference can be reviewed immediately; a recurring habit needs consistent support.

**You can see the actual change.** The workspace, context builder, and host wrapper use one preference resolver. The preview explains which rules were included or left out, and why. It does not fill the screen with an invented before/after answer.

**Exceptions stay temporary.** Current-task controls, omitted rules, context, expiry, and a preference budget determine what is sent. Your permanent profile remains unchanged by a preview.

**Feedback belongs to the version you used.** Helpful, mixed, not helpful, and unsure ratings refer to a prepared plan and exact preference versions. A rewritten rule does not inherit an old score. Silence and a successful command are never counted as approval.

**Adapt the collaboration, keep independent judgment.** Both prompt previews include the same evidence-first rules. Technical explanations remain hypotheses until supported; a conclusion changes for new evidence or better reasoning, not pressure or a high rating. Recognized requests for unconditional agreement are blocked from active preferences. [See the behavior and its limits](docs/independent-judgment.en.md).

## Bring your own conversations

Import a JSON conversation in the workspace, or run:

```sh
python3 -B scripts/watch_conversations.py --root ../private-profile --subject owner \
  --enable-conversations --input /path/to/selected.jsonl
```

Each complete line is a **full conversation snapshot**, not a single message. The foreground watcher imports new lines from that one selected file, keeps a restart cursor, and stops at a rejected record. It does not search your accounts or install a background service. See the [feed format and recovery guide](docs/automatic-learning.en.md).

Automatic recognition is experimental and can miss ordinary paraphrases. Review the evidence and correct preferences directly when needed; the [published diagnostics](docs/evaluation.md) report misses as well as successful suggestions.

Existing capabilities remain available: open-text preferences, project terminology, stated goals, writing observations, optional model-assisted proposals, and experimental historical next-request retrieval. The latter still has weak English paraphrase coverage; it is not the new habit learner.

## Use the result with your host

Codex and Cursor can use the included MCP configuration helpers or pre-invocation wrapper. `build_context.py` produces scoped messages for your own model client, including DeepSeek-style APIs. The package sends no provider request on its own.

The browser preview is real local functionality. It is **not a successful model-response test**: the v0.5.0 Codex attempt timed out after 80 seconds, and the v0.5.1 pressure-case preflight timed out after 45 seconds without an answer. Read [host acceptance and learning diagnostics](docs/evaluation.md) before treating a feature or score as proven.

## Go deeper

- [Tutorial](docs/tutorial.en.md) / [中文教程](docs/tutorial.zh-CN.md): download, workspace, review, temporary choices, feedback, and deletion.
- [Independent judgment](docs/independent-judgment.en.md): evidence, justified corrections, counterexamples, and the limits of prompt safeguards.
- [Automatic learning](docs/automatic-learning.en.md): selected feeds, evidence, conflicts, restart, and errors.
- [Host integration](docs/host-integration.md): Codex, Cursor, model context, and the [25 tools](docs/tools.en.md).
- [Conversation guide](docs/conversation-guide.en.md): JSON/JSONL imports, open-text proposals, portrait, and historical forecasts.
- [Privacy](docs/privacy-and-memory-control.md), [research](docs/research.en.md), and [20 practical questions](docs/faq.en.md).

Profiles stay in a private SQLite store outside the package. Pause, inspect, correct, forget, and reset are available. The workspace is bilingual, and the local runtime uses the Python standard library and native browser assets.

[Apache-2.0](LICENSE) · Built by [KarmenLoop](https://karmenloop.com) · [Support](SUPPORT.md) · [Security](SECURITY.md)

Historical overviews: [v0.2.0](docs/overview-v0.2.0.en.md), [v0.3.0 intermediate source](docs/overview-v0.3.0.en.md), [v0.4.0](docs/overview-v0.4.0.en.md).
