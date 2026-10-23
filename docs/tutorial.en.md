# User Behavior Personalization v0.2.0 tutorial

[English](tutorial.en.md) · [中文](tutorial.zh-CN.md)

## Install and bind a subject

Extract the release and use Python 3.11+. Choose a private data directory outside Git. A local account owner must map the intended person to a stable `--subject` ID; this release does not discover ChatGPT/Cursor account identities automatically. Do not let a conversation select another subject or expose the shared data root to an untrusted local user.

```sh
python /path/to/scripts/host.py --root /private/profiles --workspace /path/to/project --subject owner --install-host codex install
python /path/to/scripts/host.py --root /private/profiles --workspace /path/to/project --subject owner --install-host cursor install
```

Reload and approve this specific server. Verify the five profile tools. The server entry binds its subject outside tool arguments.

## Save a correction and verify it

Call `profile_read` with the task context. Use its current revision in `profile_correct`. A rule needs `id`, `statement`, `scope` (`*` for all contexts), a new `source_id`, `source_summary`, and `kind` (`explicit` or `correction`). Optional `expires_at` must include a timezone. Save only preferences the user authorized; the adapter does not infer consent from text.

Read in the other configured host using the matching context. An unrelated context returns no rule. A different bound subject returns its own profile. To correct a rule, keep its ID, provide a genuinely new source ID, and use the current revision. Stale writes are rejected; repeating an unchanged source is deduplicated.

For a model-free call, pass the same tool arguments in a JSON file to `python /path/to/scripts/host.py --root /private/profiles --workspace /path/to/project --subject owner call profile_read --input request.json`.

## Load before a new host task

Write the task into a private prompt file. Run:

```sh
python /path/to/scripts/run_host.py --root /private/profiles --subject owner --context writing --host codex --workspace /path/to/project --prompt /private/task.txt
```

Use `--host cursor` for Cursor CLI. Each host needs its own login and model access. The wrapper loads the current relevant profile before invocation and saves the used revision, rule IDs, actual exit, and host output in `host-runs`. It creates no recurring task and installs no global lifecycle hook. A timeout kills the process group it owns; inspect external effects before a retry.

## Pause, export, and forget

Use the current revision in `profile_pause`. Paused recall returns no ordinary preferences; correction is blocked until resume. `profile_export` remains available. `profile_forget` removes the chosen rule and its retained historical content, deletes the controlled export, and keeps only source hashes needed to suppress replay. External exports, backups, and physical storage remnants are separate copies. Secure-delete mode is enabled for SQLite, but no SSD-erasure guarantee is made.

Keep private stores out of release archives. Stop writers before backing up. If a profile cannot be read, the wrapper fails instead of silently pretending it applied preferences.

The acceptance exercise used an actual Codex turn and saved receipts. Cursor tool discovery passed; its model turn and native Windows/Linux behavior remain unverified. Reflection timers, automatic conversation ingestion, and identity providers need an explicit host integration rather than documentation alone.
