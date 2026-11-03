# Quick start — v0.3.0

[English](quickstart.md) · [中文](quickstart.zh-CN.md)

Download and extract the [current release](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.3.0). Use Python 3.11+ and start inside the extracted directory.

```sh
python3 -B scripts/check_package.py
python3 -B scripts/demo_learning.py --root ../new-personalization-demo
```

The second command uses a new private directory and synthetic inputs. It exercises the actual local learning/review/deletion path without a model call. Read its checks and inspect the printed directory; the demo finishes paused with content cleared and minimal replay markers retained.

Then follow the [full tutorial](tutorial.en.md) to bind your real subject, choose which feedback may be recorded, configure Codex or Cursor, and test a real model turn. Keep the store outside Git. Observations require `--enable-observations`; ordinary explicit rules work without it.

The original [Markdown profile format](../references/profile-format.md) and [reflection workflow](../references/reflection-workflow.md) remain available for hosts that manage their own files. The bundled adapter uses SQLite and does not automatically schedule reflection, ingest histories, or maintain those Markdown files.
