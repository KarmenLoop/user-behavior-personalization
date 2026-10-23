# Host Integration — v0.2.0

The bundled implementation is [scripts/host.py](../scripts/host.py), backed by a private transactional SQLite store. It implements subject-bound recall, sourced correction, source deduplication, compare-and-swap writes, pause, export, and rule deletion. [scripts/run_host.py](../scripts/run_host.py) loads a current scoped profile before invoking a real Codex or Cursor CLI task and records its actual result.

Use the [tutorial](tutorial.en.md) for installation and an end-to-end exercise. The subject mapping is an explicit local configuration supplied by the account owner, not a value supplied by a tool call. MCP instructions are not a guaranteed hook in every existing desktop conversation; use the wrapper when load-before-invocation is required.

Automatic conversation ingestion, account identity-provider integration, session-end events, and reflection scheduling are not implemented. Existing workflow references describe those future host contracts, not active services. An integration must provide verified identity, authorization, new-message cursors, and an actual registered trigger before it advertises those behaviors.

中文：已实现本地档案与 CLI/MCP 操作，包装入口可在真实宿主调用前加载偏好。自动账号映射、历史采集和反思调度仍未提供，不能把协议设计当作运行中的服务。
