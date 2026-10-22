# User Behavior Personalization: user guide

English | [简体中文](tutorial.zh-CN.md) · [Project](../README.md)

This guide matches **v0.1.1**.

## 1. Download and verify

From the release, download [`user-behavior-personalization-v0.1.1.zip`](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.1.1) and its checksum file or manifest. Compare the complete SHA-256 before extracting: use shasum -a 256 on macOS, sha256sum on Linux, or Get-FileHash -Algorithm SHA256 in PowerShell. Byte consistency relies on obtaining the expected hash from a trusted source.

## 2. Install and load

Extract the ZIP, then run python3 scripts/install_skill.py --destination ../installed-skills/user-behavior-personalization from its top-level directory. The destination must be new and outside the source. Select that directory with your host’s supported loader.

Refresh host discovery or open a new session, explicitly read the installed SKILL.md, and check the version above. The skill needs no separate model account; the host supplies its own model, tools, and permissions.

## 3. Configure and try one task

Have the host establish PROFILE_ROOT, USER_ID, USER_TIMEZONE, MEMORY_ENABLED, CONVERSATION_SOURCE, and REFLECTION_TRIGGER. These are integration contract fields, not environment variables consumed by bundled code. Start with blank templates in a private user directory.

Use a synthetic conversation containing an explicit correction. Ask the host to propose the corresponding scoped preference, show its source, and save it only through available authorized operations. Verify later recall from that saved record.

## 4. Develop a repeatable workflow

Review a conflicting correction and test export or deletion through the real host. Repository checks preserve blank templates and package hygiene; no end-to-end live-user or device-continuity certification is claimed.

Keep the version, actual command, exit code, resulting files, and unverified limits together. Use synthetic data for the first check.

## 5. Troubleshoot, update, and remove

If the host cannot find the skill, check its configured discovery root and SKILL.md readability. A checksum mismatch needs a fresh verified download; do not skip it.

Finish active writes and back up the skill and private task data separately. Extract updates into a new directory and verify before switching. For rollback, restore the older skill while retaining newer user records and evidence. Uninstall only its exact skill directory or discovery entry; separately registered schedules must be cancelled and confirmed in their host.

## 6. License

[Apache-2.0](../LICENSE). This is concise user guidance; consult the original license for use and redistribution terms.
