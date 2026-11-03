# Host integration — v0.5.1

[English](host-integration.md) · [中文](host-integration.zh-CN.md)

The browser workspace, CLI, and MCP stdio share the same local adapter and [25 tools](tools.en.md). The subject and private root are bound when the process starts. A tool call cannot select another user.

## Start with the local workspace

```sh
python3 -B scripts/workspace.py --root ../private-profile --subject owner --enable-conversations
```

Open the printed localhost URL. Import selected feedback, review a habit, preview a task, and record an explicit assessment. No provider request is made. For a continuing source, run the [selected-file watcher](automatic-learning.en.md) with the same root and subject in a separate terminal. It imports that file while running; it does not install a daemon or discover accounts.

## Configure Codex or Cursor

```sh
python3 scripts/host.py --root ../private-profile --subject owner \
  --workspace /path/to/project --enable-conversations --install-host codex install
```

Use `--install-host cursor` for Cursor. The installer writes `.codex/config.toml` or `.cursor/mcp.json`, preserving existing entries and refusing a duplicate server name. It records the Python executable, package path, root, subject, and enabled collection flags. `--enable-observations` separately enables direct typed events.

Reload the configured server in the host and inspect its tool list. Test reading the same confirmed preference from both hosts. Configuration and MCP calls do not prove a model actually used the rule; check a real response separately.

Host instruction mechanisms remain separate. Codex discovers scoped `AGENTS.md` files; Cursor project rules use `.cursor/rules/*.mdc`. Installing this server does not rewrite those instructions or force a call every turn. See the official [Codex guide](https://developers.openai.com/codex/guides/agents-md) and [Cursor rules](https://cursor.com/docs/rules).

Run the v0.5.1 scripts from the package you actually installed. An older copied skill or an MCP entry pointing to an older directory will keep using its old implementation. Install into a new directory, inspect and update the existing server entry to that path, then restart the workspace or reload the MCP server. The installer does not silently overwrite an existing copy or duplicate server. Check `--help` on that installed `build_context.py` or `run_host.py` for the temporary override options.

## Use one resolver for preview and execution

`profile_plan` previews selected and excluded rules with reasons. `scripts/build_context.py` and `scripts/run_host.py` use the same resolver for actual request content. All support a context, temporary typed overrides, omitted rule IDs, and a preference-text budget.

```sh
python3 scripts/build_context.py --root ../private-profile --subject owner \
  --context writing --task-file /path/to/private-task.txt \
  --override response_length=detailed --preference-budget 4000
```

The JSON output contains `messages` and local personalization metadata. Send only the needed request fields through your own client. The builder makes no network call and does not save the raw task. Redirected output is a separate private copy you control.

`run_host.py` loads preferences before a new Codex or Cursor CLI invocation and streams the result to the console. Its saved receipts contain metadata, not raw prompt or output. Codex receives the prompt on stdin; the current Cursor CLI path uses a positional argument, visible to same-user process inspection. Host accounts, model access, terminal logging, and provider retention remain separate. No hook is installed in an already-running desktop chat.

## Optional model-assisted learning

`profile_model_context(context)` returns bounded retained excerpts and a proposal contract. An authorized host can send these to its chosen model, including a DeepSeek-style chat API. Submit returned proposals through `profile_model_propose`; known source keys, exact quotes, categories, and scope are checked. Valid output stays pending until the user reviews it.

DeepSeek JSON Output constrains format, not truth. Reject blank/truncated responses, validate fields and source allowlists, and treat excerpts as data rather than instructions. See the [official JSON Output guide](https://api-docs.deepseek.com/guides/json_mode/). This package does not include provider credentials, a model loop, or a live DeepSeek certification.

## Keep integration boundaries clear

The host supplies verified identity, authorized messages, accurate roles/source IDs, and actual review decisions. Source strings are attestations, not independent proof of permission. Current instructions and normal execution authority still apply.

Daily schedules, account-history export, OS isolation, multi-device synchronization, and external retention need their own host implementation. The [legacy reflection contract](../references/reflection-workflow.md) describes these responsibilities. The selected-file watcher is an implemented foreground importer, not that entire service. See [current evaluation](evaluation.md) for local and provider results.
