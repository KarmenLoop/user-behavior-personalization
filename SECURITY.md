# Security Policy

## Scope

Security concerns include cross-user memory disclosure, unauthorized use of private conversation data, prompt injection through stored profiles, replay of forgotten information, and unsafe publication of real user records.

The repository is an instruction package. Report adapter-specific storage, identity, scheduling, and synchronization issues to the relevant adapter or host as well when applicable.

## Reporting Privately

Use GitHub's **Report a vulnerability** option in this repository's Security tab when private vulnerability reporting is enabled:

https://github.com/KarmenLoop/user-behavior-personalization/security/advisories/new

If GitHub does not offer a private report for your account or this repository, open a public issue requesting a private reporting channel without including exploit details, credentials, user records, or other sensitive material. Do not assume a reporting channel or response time that has not been confirmed.

Include the affected version, a minimal synthetic reproduction, the expected authorization boundary, and the observed result. Share only the information necessary to explain the issue.

## Supported Versions

The maintainer targets the latest published release for security-related corrections. No fixed response-time or support-duration commitment is made in this initial package.

## Sensitive Data in Reports

Do not upload live `USER_SKILL.md` files, reflection logs, message exports, tokens, or synchronization credentials. Replace identities and source messages with fictional fixtures.
