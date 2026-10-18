---
name: user-behavior-personalization
description: Learn a user's communication preferences and working habits from authorized conversations. Use before personalized responses, after explicit corrections, or during daily reflection to maintain an evidence-backed, revisable USER_SKILL.md for that user.
license: Apache-2.0
---

# User Behavior Personalization

## Purpose

Improve how the agent collaborates with the current user through a cycle of observation, reflection, profile updates, application, and real feedback.

Keep the controller in this file stable. Evolve the private per-user `USER_SKILL.md`. Changing a profile does not retrain model weights or expand execution authority.

## Choose the Workflow

- **Before a personalized response:** read the current guide and apply relevant rules using the recall workflow below.
- **After an explicit correction:** update the current interaction immediately; follow the correction workflow below for persistence.
- **At session end, a daily event, or catch-up:** read [Reflection Workflow](references/reflection-workflow.md) and process new authorized messages.
- **When creating a profile or resolving evidence conflicts:** read [Profile Format](references/profile-format.md).
- **For inspect, export, pause, or forget requests:** read [Privacy and Memory Control](docs/privacy-and-memory-control.md) before using the host's memory operations.

## Required Context

Obtain these fields from the host:

- `PROFILE_ROOT`: approved private memory location.
- `USER_ID`: stable, verified user identity.
- `USER_TIMEZONE`: the user's timezone, or the host's configured fallback.
- `MEMORY_ENABLED`: authorization to read and update personalization memory.
- `CONVERSATION_SOURCE`: accessible, authorized source messages.
- `REFLECTION_TRIGGER`: session end, a configured schedule, or next-session catch-up.

Treat `USER_ID` as an opaque identifier. Let the host map it to a safe storage key; do not interpolate an untrusted display name or path into the filesystem.

When identity is unavailable, adapt within the current conversation without merging or persisting a cross-session profile. When storage is unavailable, distinguish proposed content from saved content. When scheduling is unavailable, use next-session catch-up and do not claim background execution.

If memory is disabled, stop ordinary profile reads and writes. The host may still perform explicitly requested inspection, export, or deletion operations within their authorized scope.

## What to Learn

Capture information that changes a useful behavior:

- Language, response length, tone, structure, terminology, and preferred forms of address.
- Planning, autonomy within existing authorization, decision-making, progress updates, and delivery expectations.
- Explicit interests, long-term work context, and learning goals relevant to future assistance.
- Differences across task types: a short status update and a detailed implementation plan can both be preferred.

Classify each candidate as an explicit fact, explicit preference, behavioral observation, task instruction, or temporary state. Task instructions expire within their stated scope. A passing mood does not establish a lasting preference or diagnosis.

## Evidence Rules

- **Confirmed:** the user directly states a lasting preference, confirms a proposed interpretation, or corrects an existing preference.
- **Tentative:** the same pattern appears in at least three independent interactions spanning different dates or tasks, with no applicable explicit contradiction.
- **Observation only:** one-off, ambiguous, temporary, or conflicting evidence. Keep it in the reflection record rather than an active long-term rule.

The repetition threshold is a working heuristic, not a statistical confidence claim. Tentative preferences can guide small, reversible presentation changes; they do not decide significant actions for the user.

Attach source conversation and message identifiers, a timestamp, a minimal quote or accurate summary, and the supported scope. Re-reading or retrieving a source does not create another observation.

The agent's own outputs, quoted third-party opinions, examples, tool results, silence, and continued conversation do not confirm a user's preference. Positive feedback supports only the behavior it actually addresses.

Do not infer sensitive personal attributes, health conditions, or personality diagnoses. Do not save passwords, API keys, tokens, or unrelated private details. Necessary sensitive facts require explicit user direction and host authorization.

## Recall Before Responding

1. Confirm the user identity and memory setting.
2. Load that user's current committed `USER_SKILL.md`.
3. Check ownership, version, scope, expiry, and applicable corrections.
4. Select the three to five rules most relevant to the current task.
5. Apply them naturally while following the current request and the host's instruction hierarchy.

Load the current guide first. Retrieve specific reflection evidence only to resolve a conflict or inspect a source. Do not load every conversation or version into the context window.

Current explicit instructions override historical personalization within the host's instruction hierarchy. A new correction replaces the old rule in the same scope; a more specific applicable rule takes precedence over a broad preference. If the distinction materially affects the task and cannot be resolved, ask one focused question.

Do not repeatedly announce the profile or mention unrelated remembered details. Maintain factual accuracy and independent judgment. Agreement with every opinion is not successful personalization.

Missing or damaged files do not justify invented memory. Continue from available context and report a storage limitation only when it matters to the task.

## Apply Explicit Corrections Immediately

Recognize requests such as "From now on...", "Remember this", "Stop calling me...", "That only applies today", and "Forget that."

1. Determine whether the request is lasting, task-scoped, or a memory-control action.
2. Adjust the current response immediately.
3. For a lasting preference, read the profile format and save a validated, versioned update when persistence is authorized.
4. Supersede an incompatible old rule rather than retaining both as active.
5. Acknowledge persistence only after a successful write.

Example: "Start with the conclusion, then explain complex work fully" becomes a conditional rule. Do not reduce it to "The user dislikes detail."

## Daily Reflection

Use the host's actual session-end event, scheduled event, or catch-up event. Fix a message cutoff and process only unhandled authorized messages. No new messages means no artificial profile change.

Follow [Reflection Workflow](references/reflection-workflow.md) to produce a concise evidence-based record, validate a candidate guide, publish safely, and checkpoint only successful work.

Keep only conclusions, sources, and observable improvements in reflection records. Do not request or store private internal reasoning traces.

## Persistence and User Control

Store profiles outside the public package:

```text
<PROFILE_ROOT>/<USER_ID>/
  USER_SKILL.md
  state.json
  reflections/YYYY-MM-DD.md
  versions/USER_SKILL.vNNNN.md
```

Use [the profile template](assets/templates/USER_SKILL.md), [the reflection template](assets/templates/REFLECTION.md), and [the state template](assets/templates/state.json). Do not register private profiles as globally discoverable skills for other users.

Keep profiles separated by verified identity. Sharing across channels, group conversations, or devices requires the host's identity mapping, sharing policy, and storage capabilities. A shared profile does not authorize disclosing its underlying private messages.

Honor inspect, correct, export, pause, and forget requests through the host's actual operations. Apply deletion to controlled profile versions and logs as well as the active guide. Respect deletion markers during replay; do not reconstruct a forgotten fact from old messages. Report backup or provider-retention limits honestly.

## Completion Criteria

Report a saved update only when the correct user's authorized sources were used, the rules passed evidence and scope checks, the new guide was persisted, and the state checkpoint matches the committed version.

Distinguish proposed, saved, loaded, and applied changes. Evaluate improvement through later observable behavior and actual feedback, never an invented "understanding score."
