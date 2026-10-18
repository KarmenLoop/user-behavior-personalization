# Host Integration

This document is an integration contract. The pseudocode describes host behavior; it is not a bundled implementation or an existing API endpoint.

## Host Operations

| Operation | Required behavior |
| --- | --- |
| Resolve identity | Return a verified user identity and safe storage key |
| Check authorization | Determine whether profile access and source analysis are allowed |
| Read current guide | Return the current committed version for that user |
| Read new messages | Return authorized messages after per-conversation checkpoints |
| Resolve a source | Locate a message for evidence inspection when needed |
| Commit an update | Preserve consistency between the guide, reflection, and state |
| Serialize writers | Use a lock, transaction, or compare-and-swap version check |
| Trigger reflection | Emit a session-end, scheduled, or catch-up event |
| Manage memory | Inspect, correct, export, pause, and delete within actual capabilities |

Avoid advertising a workflow until its required operations exist. For example, a host without private storage can offer current-session adaptation but cannot claim durable personalization.

## Before a Response

```text
identity = resolve_verified_identity(session)
authorization = check_memory_authorization(identity, session)
if authorization permits ordinary recall:
    guide = read_current_guide(identity)
    verify owner and committed version
    select applicable active rules
apply current instructions and applicable personalization
continue the user's task
```

Instruction discovery alone is not a guaranteed per-turn hook. If every conversation must load the user guide, wire the step into the host's response lifecycle.

## On Explicit Correction

```text
classify the correction and its scope
apply it to the current interaction
if persistence is authorized and supported:
    read the latest committed guide
    revise only the affected records
    validate and commit using the expected version
report the actual persistence result when relevant
```

Never require the user to wait until the next day for an explicit correction to affect the current response.

## On a Reflection Event

The event must identify its user, timezone, conversation range, and fixed cutoff. Read only accessible messages within that scope.

Use per-conversation cursors. A host may use sequence numbers, opaque continuation tokens, or message IDs according to its source API. Do not sort opaque IDs to invent ordering.

If a batch is too large for the available context, split it into bounded input ranges and commit successful ranges separately. Keep evidence identities so chunking does not inflate repetition counts.

## Commit and Recovery

Prefer a host transaction covering the guide, reflection record, and processing checkpoint. A file-backed host should use a same-filesystem temporary file and atomic replacement for the guide, plus a documented recovery protocol for the remaining files.

Minimum invariants:

- A failed candidate does not advance the processed-message checkpoint.
- The state names the current committed guide version.
- A stale writer cannot overwrite a later correction.
- Replaying a batch does not duplicate evidence or create repeated rules.
- Interrupted updates can be reconciled before ordinary recall resumes.
- A rollback does not restore a deleted preference.

Define lock scope and stale-lock recovery in the adapter. This Markdown package does not provide those mechanisms.

## Channel and Group Identity

Map channel identities to one profile only after verification. Account linking, enterprise identity mapping, or an explicit host-admin mapping may provide that verification; matching names do not.

Keep identity sharing separate from content sharing. The host should define which profile fields may influence a group response and whether the underlying private evidence is accessible. An invitation to a group is not an automatic grant to every participant's private history.

## Cross-Device Synchronization

A local file alone does not synchronize devices. A synchronized adapter needs:

1. Authenticated access to the same user's namespace.
2. An authoritative committed version or reliable conflict protocol.
3. Offline handling that prevents a stale device from overwriting new corrections.
4. Propagation of deletions and any replay-suppression metadata.
5. A retention policy for remote copies and backups.

Do not synchronize API keys or execution permissions as part of a preference profile. Report synchronization status using actual receipts or readback, not the existence of an integration plan.

## Scheduling

Use the configured user timezone. Store actual run timestamps separately from the source date being reflected upon. A catch-up run may process yesterday's messages today without claiming it executed yesterday.

If users keep chatting after the daily cutoff, leave later messages for a subsequent batch. Session-end signals should come from the host or an explicit user event, not a guess that a short silence means the day is over.

This skill does not create cron jobs, system services, automation registrations, or messaging connections.

## Installation Adapter Status

The package supplies portable instructions and optional UI metadata. It does not ship a certified adapter for a named host. When contributing one, document the exact host version, capabilities used, setup commands, verification results, and remaining limits.
