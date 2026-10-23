# User Behavior Personalization

[English](README.md) · [中文](README.zh-CN.md) · **v0.2.0**

Save an explicit preference once, correct it when it changes, and load the relevant version before the next task. The Python adapter provides subject-bound profiles, transactional corrections, pause/export/forget controls, and a wrapper that reads the profile before starting Codex or Cursor.

![Profile workflow](docs/images/workflow-v0.2.0.svg)

Each rule has a source, scope, revision, and optional expiry. A forgotten source cannot recreate a deleted rule by replay. Separate subjects use separate records; the subject is bound in local host configuration, not chosen by a model's tool arguments.

Download [v0.2.0](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.2.0), use Python 3.11+, and follow the [tutorial](docs/tutorial.en.md). No model-training step or hosted account is needed to store profiles. Calling a CLI model still requires that host's own access.

A live Codex run loaded the saved profile before invocation, called the tools, and followed its output preference. Cursor discovered all profile tools; its model conversation was blocked by local login/usage limits. Automatic chat identity mapping, daily reflection scheduling, ingestion of conversation history, and guaranteed per-turn hooks in already-running desktop chats are not supplied. Use the wrapper when profile loading must happen before a new CLI invocation.

[Apache-2.0](LICENSE). [Privacy controls](docs/privacy-and-memory-control.md). [KarmenLoop](https://karmenloop.com).
