# Host integration — v0.4.0

[English](host-integration.md) · [中文](host-integration.zh-CN.md)

## Local CLI and MCP

`scripts/host.py` exposes the eighteen tools listed in the [README](../README.md). CLI `call` and MCP stdio use the same implementation and validation. The subject is bound at process startup; tool arguments cannot select another user. `--enable-observations` enables the collection path after the operator has obtained permission.

The host supplies verified identity, authorized source messages, honest source/session identifiers, explicit review decisions, and the current context. The adapter imports explicitly supplied conversations; it does not scrape histories or prove that a supplied `source_id` is a real consent receipt. Never treat tool availability as blanket permission to collect feedback.

## Codex and Cursor

The installer writes `.codex/config.toml` for Codex or `.cursor/mcp.json` for Cursor, preserving existing entries and refusing a duplicate server name. The server configuration binds the Python executable, package path, private root, and subject. A shared private root and subject let the two hosts read the same committed profile on one machine.

Use the skill as host-readable guidance. Codex's `AGENTS.md` and Cursor's project rules are separate instruction mechanisms; installing an MCP server does not rewrite those files or guarantee a tool call on every turn. Cursor rule files use `.mdc` under `.cursor/rules`; a plain Markdown file there is not equivalent. Check the host's current [Codex instructions](https://developers.openai.com/codex/guides/agents-md) and [Cursor rules](https://cursor.com/docs/rules).

`scripts/run_host.py` reads confirmed preferences before a new CLI invocation. Its metadata receipts distinguish the loaded revision and rule IDs from the host's actual exit result. Output goes to the console. No timer or hook is installed in an already-running desktop conversation. A host still needs its own account, model access, permissions, and working CLI.

## DeepSeek and other chat APIs

```mermaid
sequenceDiagram
  participant User
  participant Host as Your host
  participant Local as Local profile adapter
  participant Model as Chat API
  User->>Host: Current task
  Host->>Local: profile_read(exact context)
  Local-->>Host: Confirmed rules and revision
  Host->>Model: messages with selected rules and task
  Model-->>Host: Answer or proposed tool call
  Host->>Host: Validate allowlist, arguments, identity, authority
  Host-->>User: Answer; ask before confirming a candidate
```

`scripts/build_context.py` generates a JSON request payload with `messages` and local metadata. It sends nothing. Your client selects the appropriate provider model and sends `messages` according to the provider's current API. Credentials stay in your client, not in the profile or this repository.

DeepSeek JSON Output can constrain response formatting; it does not prove the truth of extracted preferences. A custom tool bridge must validate types and enumerations, require sources from an authorized user-message allowlist, reject blank/truncated responses, preserve revision checks, and send only the necessary context. Do not ingest hidden reasoning or assistant output as user evidence. Consult the [official JSON Output guide](https://api-docs.deepseek.com/guides/json_mode/).

This release includes an offline explicit-cue extractor and a local bridge for host-model proposals. It does not ship an autonomous DeepSeek tool loop or make provider calls. A successful local payload build is not a live DeepSeek integration test.

## Capabilities still owned by the host

Identity providers, background history collection, session-end events, background reflection, encryption and OS access control, provider retention, shared-chat disclosure, and multi-device synchronization require their own implementations and acceptance. The [legacy reflection contract](../references/reflection-workflow.md) describes how a host could supply those capabilities; it is not a running service.

Use the [tutorial](tutorial.en.md) for reproducible local calls and the [evaluation guide](evaluation.md) for current acceptance boundaries.

## Local process visibility

Codex receives the composed prompt on stdin. The current Cursor CLI path accepts it as a positional argument, so other tools running as the same local user may be able to inspect it in process arguments. Use the MCP path or an appropriate local account boundary when that exposure is unacceptable. Streaming output can still be captured by your terminal or host; metadata-only adapter receipts do not erase those separate copies.

## Conversation import and host-model proposals

Enable `--enable-conversations` independently of `--enable-observations`. Feed selected JSON/JSONL through `learn_conversation.py`, or call `conversation_import` with the current revision. Tool role labels and source IDs are supplied by the host; bind them to authorized records before import. The adapter retains bounded sanitized user excerpts and stages open-text proposals.

For model assistance, call `profile_model_context(context)`, pass the selected excerpts and extraction instructions to your authorized model, then submit its structured proposals to `profile_model_propose`. Each proposal needs a category, scope, statement, and exact quotes from known source keys. A proposal is still pending after validation; `profile_proposal_review` records the user's actual decision. No provided tool can substitute the model's approval for that review.

`profile_portrait` and `profile_forecast` expose private source examples for inspection. Do not insert their complete output into unrelated or shared conversations. `profile_read` remains the compact confirmed-rule path for ordinary responses.
