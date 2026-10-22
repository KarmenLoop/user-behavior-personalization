# Contributing

Thank you for improving User Behavior Personalization. Focused changes to instructions, documentation, evaluation cases, and host integrations are welcome.

## Before You Start

Search existing issues and read the relevant workflow. For a substantial change, describe the concrete behavior and expected result in an issue before implementing a broad redesign. Small corrections can go directly to a pull request.

Provide matching English and Simplified Chinese entry pages and user guides. Keep code, templates, issue reports, and pull request descriptions in English. Examples should be synthetic and clearly labeled.

## Scope

Keep the main skill focused on evidence-backed personalization. Add a script or reference only when it has a specific maintained purpose. Avoid duplicating the same rule across many files.

Do not add model training, account linking, background scheduling, or synchronization claims without an actual implementation and reproducible validation for that scope.

## Making a Change

1. Fork the repository and create a branch for one coherent change.
2. Edit the relevant instructions, documentation, or adapter.
3. Add or update a realistic evaluation scenario when behavior changes.
4. Run `python3 scripts/check_package.py` with Python 3.9 or later.
5. Review the publishable diff for private data and unsupported capability claims.
6. Describe the problem, resulting behavior, actual validation, and remaining limits in the pull request.

The package check does not run an agent or validate user satisfaction. For a host adapter, include exact setup instructions, host version, observed results, and capability limits.

## Reporting Bugs

Include the package version, host and version, a minimal synthetic conversation, expected behavior, actual behavior, and any relevant sanitized state transition. Never attach real user profiles, private chat exports, or credentials.

Use the private reporting process in [SECURITY.md](SECURITY.md) for vulnerabilities or data exposure.

## Licensing

By intentionally submitting a contribution for inclusion, you provide it under the project's Apache License, Version 2.0, unless a different arrangement is explicitly agreed with the maintainer. Only contribute material you have the right to submit. Preserve applicable attribution and identify modified upstream material.

No separate contributor license agreement is required by this package.

## Community Conduct

Keep discussion respectful, specific, and relevant to the work. Critique behavior and evidence rather than people. Do not publish another person's private information. Maintainers may moderate content that violates these expectations.

## Documentation and release changes

Keep the English and Simplified Chinese entry pages and guides aligned. Explain the reader’s actual task with project-specific examples. Use concrete English commit subjects. New ordinary filenames and versioned release assets use lowercase kebab-case without spaces; conventional README, LICENSE, SKILL and metadata names remain unchanged. Before release, compare each package, version label, command, and current image with the documented behavior. Label diagrams, synthetic data, historical evidence, and unverified integrations accurately.
