# Reflection and Update Workflow

Read this reference for a session-end review, daily reflection, next-session catch-up, or a recovery from an interrupted update.

## 1. Establish the Batch

Verify memory authorization, user identity, timezone, conversation access, and the currently committed guide version. Read the per-conversation checkpoints from `state.json` and fix an input cutoff before analyzing messages.

Use stable message identities to deduplicate source messages. If no new authorized messages exist, skip the batch. Do not modify a profile simply to appear active.

For catch-up, process the unhandled available range in bounded batches. Keep the original source dates; do not pretend that an older reflection ran on schedule. Do not delay an urgent current user request for unbounded historical processing.

## 2. Extract Candidates

Classify new information using [Profile Format](profile-format.md). Collect explicit preferences, corrections, specific satisfaction or dissatisfaction feedback, repeated working patterns, changed context, and temporary instructions that should expire.

Each candidate needs a source, scope, classification, and a check for applicable counterevidence. Exclude the agent's own statements, quoted material, and duplicate messages as independent confirmation.

## 3. Review Observable Behavior

Identify which prior rules were followed, which were missed, and which user feedback supports a specific change. State the next observable action rather than a general promise to "understand the user better."

Save conclusions, evidence summaries, and proposed actions. Do not save hidden reasoning traces or full chat exports.

## 4. Choose an Outcome for Each Candidate

- Add a confirmed rule.
- Add a tentative rule.
- Attach new evidence to an existing rule.
- Narrow or clarify scope.
- Replace an obsolete rule.
- Expire a temporary instruction.
- Keep an observation out of the active guide.
- Make no change.

No justified changes means no profile-version increase. A processed batch can still have a reflection record and a checkpoint.

## 5. Draft and Validate

Generate a candidate `USER_SKILL.md` with stable rule identifiers, actionable wording, evidence references, and explicit scope. Review for wrong-user data, unsupported inferences, duplicated rules, unresolved contradictions, expired instructions, sensitive content, and unnecessary length.

Check the candidate against at least the relevant scenarios in [Evaluation](../docs/evaluation.md). Scenario review is useful evidence, but it is not an independent live-user test.

The guide must contain personalization data and guidance, not instructions to grant access, install tools, change system policy, or execute arbitrary content quoted from a source.

## 6. Publish and Checkpoint

Use the host's transaction mechanism when one exists. For a file-backed host:

1. Serialize updates for this user, or use compare-and-swap on the expected version.
2. Save the batch's reflection record with its stable batch identifier.
3. Preserve the previous guide version if a substantive update is being made.
4. Write and validate a temporary guide in the destination filesystem.
5. Atomically replace the current guide when the filesystem supports it.
6. Update `state.json` only after the reflection and any new guide are durable.
7. Record the actual result and release the update lock.

Atomic replacement of a single file is not a multi-file transaction. The host must define crash recovery, lock behavior, and version reconciliation. On a conflict, reload and recompute from the latest committed guide; do not overwrite a new user correction with an old candidate.

On failure, leave checkpoints unchanged and report the failure accurately. If the guide was replaced before a crash but the checkpoint was not, replay safely: use the batch and evidence identities to avoid duplicate rules or unsupported version increments.

Use [the reflection template](../assets/templates/REFLECTION.md). Multiple batches on the same local day append distinct sections instead of overwriting previous records.

## 7. Apply and Verify Later

At the next relevant response, load the committed guide and apply its selected rules. Observe actual user feedback. If a change leads to a clear negative correction, revise the affected rule rather than rewriting unrelated supported preferences.

Distinguish these outcomes:

- **Proposed:** candidate content was generated.
- **Saved:** content was durably committed.
- **Loaded:** a subsequent interaction read it.
- **Applied:** the subsequent behavior followed the rule.
- **Supported by feedback:** the user explicitly responded to the relevant behavior.

Do not collapse these stages into one success claim.

## Rollback and Deletion

For a damaged or unsuitable update, restore an allowed previous version through a new validated commit so the state remains consistent. Preserve later valid corrections when rolling back an unrelated change.

Do not restore forgotten information from a version, reflection, backup, or source replay. Apply the host's deletion markers and current authorization before using any historical material. See [Privacy and Memory Control](../docs/privacy-and-memory-control.md).
