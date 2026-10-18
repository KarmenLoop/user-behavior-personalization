# Quick Start

This guide installs the instruction package and prepares a private user guide. It does not install an agent runtime or background service.

## Requirements

- An agent host that can load Markdown instructions.
- Access to the current user's authorized messages.
- For durable memory, an approved private storage location and a verified user ID.
- For unattended reflection, a host scheduler or a session-end event.

The skill itself has no Python, Node.js, package manager, or model-provider dependency.

## 1. Download or Clone

```bash
git clone https://github.com/KarmenLoop/user-behavior-personalization.git
cd user-behavior-personalization
```

Alternatively, download a release archive and extract it. Keep the package's directory structure intact.

## 2. Make the Skill Available

Use the host's supported skill loader. For directory-based discovery, name the installed directory `user-behavior-personalization` and include `SKILL.md` with its supporting directories.

Do not copy a real user's profile into the installed public package. The controller is shared; personal memory is private and identity-scoped.

If the host does not automatically discover skills, explicitly ask it to read the package's `SKILL.md`. This supports the current session, but does not by itself guarantee automatic loading in future sessions.

## 3. Initialize Private Memory

Choose a directory outside the checkout. The following Bash example initializes a fictional local account. Replace the path and identifier with your host's approved location and verified storage key before using it.

```bash
profile_root="$HOME/.local/share/user-behavior-personalization"
profile_user_id="demo-user-001"
profile_dir="$profile_root/$profile_user_id"

mkdir -p "$profile_dir/reflections" "$profile_dir/versions"
test ! -e "$profile_dir/USER_SKILL.md" && cp assets/templates/USER_SKILL.md "$profile_dir/USER_SKILL.md"
test ! -e "$profile_dir/state.json" && cp assets/templates/state.json "$profile_dir/state.json"
```

The existence checks preserve an existing guide. If a file already exists, inspect it instead of overwriting it. For multiple concurrent initializers, use the host's exclusive-create or transaction operation rather than these interactive setup commands.

Edit the new files through the host's authorized file operation:

- Set the guide's `user_id` to the verified identity.
- Set `updated_at` to the actual initialization timestamp with timezone.
- Set `state.json`'s `user_id` to the same identity.
- After the initial guide is committed, set `profile_version` to `1`.
- Keep the initial preference sections empty.

Set `MEMORY_ENABLED` only according to the user's memory authorization. Bind `USER_TIMEZONE` and `CONVERSATION_SOURCE` in the host.

## 4. Invoke the First Review

Provide this instruction using your host's normal skill invocation mechanism:

```text
Use user-behavior-personalization for the current verified user.
Read only authorized conversations and the configured private profile.
Learn explicit preferences without inventing background facts.
Apply corrections immediately and save only through available authorized operations.
```

If the host supports `$skill-name` syntax, the invocation name is `$user-behavior-personalization`. Other hosts may use a different loader.

## 5. Check a Real Correction

Tell the agent:

```text
For future answers, start with the conclusion. Keep simple questions short,
but include the full steps and validation for complex implementation work.
```

Verify that the guide contains a conditional confirmed preference with a source reference. Ask a new relevant question and inspect whether the answer follows the rule. A saved file alone does not establish that later recall works.

## 6. Connect Daily Reflection

Choose one host-supported trigger:

- A session-end event after the user's conversation finishes.
- A daily scheduled event in the configured timezone.
- Catch-up before the next conversation if background scheduling is unavailable.

The event should pass the verified identity, source range, and fixed cutoff to the reflection workflow. Multiple conversations need separate checkpoints.

See [Host Integration](host-integration.md) for persistence, concurrency, and recovery requirements. This repository does not register a scheduler automatically.

## 7. Check User Control

Try inspecting a stored preference, correcting it, and forgetting it. Confirm that a later reflection does not recreate a forgotten rule from the same old message. Validate deletion behavior in the actual host, including logs and recoverable versions.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| The agent does not remember across sessions | Persistent storage, stable identity, and profile loading on the next session |
| Reflection never runs | An actual scheduler or lifecycle event exists; a Markdown instruction is not a timer |
| A correction keeps coming back | Old rules were superseded, checkpoints deduplicate messages, and deletion markers are honored |
| One user's preferences affect another | Identity mapping and storage namespace isolation |
| The context window fills up | Load the current guide and selected evidence rather than every reflection and chat export |
| Two devices overwrite each other | Host-provided synchronization, version checks, and correction-preserving conflict resolution |

For a reproducible issue, use [SUPPORT.md](../SUPPORT.md) and include synthetic examples only.
