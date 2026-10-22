# User Behavior Personalization

English | [简体中文](README.zh-CN.md)

Keep useful preferences in a profile the user can inspect and correct. This skill describes how an agent should turn explicit feedback into scoped guidance without quietly treating a guess as a personal fact.

[Download v0.1.1](https://github.com/KarmenLoop/user-behavior-personalization/releases/tag/v0.1.1) · [Guide](docs/tutorial.en.md) · [Issues](https://github.com/KarmenLoop/user-behavior-personalization/issues)

## What it does

An instruction package with blank templates and synthetic examples. The host supplies verified identity, private storage, loading, deletion/export, and any scheduling or synchronization.

![User Behavior Personalization workflow illustration](docs/images/workflow-v0.1.1.svg)

*Workflow illustration for v0.1.1; not an application screenshot or runtime acceptance.*

## Start here

Extract the ZIP, then run python3 scripts/install_skill.py --destination ../installed-skills/user-behavior-personalization from its top-level directory. The destination must be new and outside the source. Select that directory with your host’s supported loader.

Have the host establish PROFILE_ROOT, USER_ID, USER_TIMEZONE, MEMORY_ENABLED, CONVERSATION_SOURCE, and REFLECTION_TRIGGER. These are integration contract fields, not environment variables consumed by bundled code. Start with blank templates in a private user directory.

## A first useful task

Use a synthetic conversation containing an explicit correction. Ask the host to propose the corresponding scoped preference, show its source, and save it only through available authorized operations. Verify later recall from that saved record.

Review a conflicting correction and test export or deletion through the real host. Repository checks preserve blank templates and package hygiene; no end-to-end live-user or device-continuity certification is claimed.

## Questions

**Will installing it remember every conversation?** No. The host must explicitly provide authorized conversations, storage, and loading. The package starts no service and registers no timer.

## Documentation and license

[Download, setup, practice, and updates](docs/tutorial.en.md) · [LICENSE](LICENSE)

Apache-2.0. The original license terms govern use and redistribution; retain the included legal files. [KarmenLoop](https://karmenloop.com).
