# Quick start — v0.4.0

[English](quickstart.md) · [中文](quickstart.zh-CN.md)

Download and verify [v0.4.0](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.4.0), extract it, and use Python 3.11+ from that directory.

```sh
python3 -B scripts/check_package.py
python3 -B scripts/learn_conversation.py --root ../private-profile --subject demo --enable-conversations --input examples/conversations/sample.en.json
python3 -B scripts/demo_conversations.py --root ../new-conversation-demo
```

The importer prints actual open-text proposals and writing observations; it does not confirm them. The lifecycle demo uses a new directory and synthetic conversations to exercise review, forecast, model-proposal staging, deletion, and reset through real local processes. No model provider is called.

Continue with the [tutorial](tutorial.en.md) for your own JSON/JSONL, independent context labels, Codex/Cursor configuration, granular deletion, and actual host acceptance. See [evaluation](evaluation.md) before relying on the experimental forecast; English paraphrase coverage is currently weak.

The [structured-feedback workflow](structured-feedback.en.md) remains available with its separate `--enable-observations` setting. Private stores belong outside Git.
