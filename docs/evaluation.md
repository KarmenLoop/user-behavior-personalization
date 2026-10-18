# Evaluation and Release Checks

Evaluate observable behavior as well as file structure. A valid Markdown file, a saved preference, and a successful live integration are different results.

## Behavioral Scenarios

| Scenario | Input or condition | Expected observable result |
| --- | --- | --- |
| Temporary brevity | "Keep today's update short" | A scoped temporary instruction, not a permanent dislike of detail |
| Explicit lasting preference | "From now on, start with the conclusion" | A confirmed rule saved once with the correct source |
| Conditional preference | "Simple questions short; complex plans complete" | Separate applicable behavior by task scope |
| Quoted third-party view | "My colleague prefers formal wording" | No preference attributed to the current user |
| Explicit correction | "Stop using that nickname" | Immediate response change and no incompatible active rule |
| Repeated pattern | Three independent requests for examples across tasks | Tentative guidance with sources, not a probability claim |
| Duplicate evidence | Retrieve one message three times | One observation, no artificial promotion |
| Silence | The user continues without feedback | No claim of confirmed satisfaction |
| Temporary mood | "I'm exhausted today" | No permanent trait or diagnosis |
| Disabled memory | Ordinary recall after opt-out | No ordinary profile read or update |
| Wrong identity | A different verified user starts a session | No access to the previous user's guide |
| Missing storage | A lasting preference is requested | Current-session adaptation and an honest persistence limitation |
| Failed write | Candidate publication fails | No advanced checkpoint or false saved claim |
| Stale writer | A second device has a newer correction | Conflict detected; the stale candidate does not overwrite it |
| Interrupted commit | Guide replaced before state update | Host recovery reconciles versions and deduplicates evidence |
| Forget and replay | Old messages contain a forgotten preference | The controlled replay does not reconstruct it |
| Shared conversation | A private source supports a presentation preference | No private-source disclosure without the sharing policy |
| No scheduler | No background execution mechanism exists | Catch-up is offered or used; no claim of an active daily job |

## Recording a Run

For a real host evaluation, record:

- Package version and revision.
- Host name, version, and enabled capabilities.
- Synthetic input messages and stable source identifiers.
- Initial and final guide versions.
- Actual storage result and processing checkpoint.
- A subsequent response showing whether the rule was loaded and applied.
- Any real feedback, accurately scoped to the relevant behavior.
- The exact command or action, exit status where applicable, and unresolved limits.

Classify each result as not run, failed, or observed pass. A manually reasoned scenario is a review result, not an executed host test. Automated package checks do not prove learning quality or user satisfaction.

## Package Check

With Python 3.9 or later available, run:

```bash
python3 scripts/check_package.py
```

The standard-library-only check validates required artifacts, local Markdown file links, basic skill frontmatter, JSON template shape, English-package CJK exclusions, fenced-block closure, and accidental private-data directories. It does not call a model, install the skill, schedule work, test an adapter, or prove that private data is absent.

An [optional GitHub Actions template](../assets/github-actions/check-package.yml) runs this check on pushes and pull requests. To enable it, copy the template to `.github/workflows/check-package.yml` and commit it using credentials authorized to update workflows. The template is not active while it remains in `assets/github-actions/`.

## Release Procedure

1. Update `VERSION` and `CHANGELOG.md` for the actual scope.
2. Run the package check and review the behavioral scenarios affected by changes.
3. Inspect the exact publishable file list for real user data or credentials.
4. Confirm licensing and attribution match the published package.
5. Commit the reviewed files and create a version tag.
6. Build an archive from the committed revision and publish release notes with limits stated.
7. Verify the remote repository, release tag, downloadable assets, and license detection.

Do not describe an unimplemented scheduler or synchronization service as a released feature. Do not use passing package checks as evidence of cross-device operation or live-user adaptation.
