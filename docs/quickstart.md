# Quick start — v0.5.1

[English](quickstart.md) · [中文](quickstart.zh-CN.md)

Download and verify [v0.5.1](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.5.1), extract it, and use Python 3.11+ from that directory.

```sh
python3 -B scripts/check_package.py
python3 -B scripts/workspace.py --root ../private-profile --subject demo --enable-conversations
```

Open the printed local URL. Choose **Try a synthetic example**, inspect the three supporting conversations, and review the concise-answer habit. In **Shape the next task**, preview its effect, then choose a detailed response **just for this task**. The saved preference stays unchanged.

Save a plan and rate the prompt review. A model account is not needed for this local walkthrough; the preview is a composed prompt, not a generated answer. Stop the server with Ctrl+C.

Continue with the [full tutorial](tutorial.en.md), [selected-file watcher](automatic-learning.en.md), or [Codex/Cursor configuration](host-integration.md). Use a private root outside Git. Current learning and model-response limits are recorded in [evaluation](evaluation.md).
