# Architecture

## The Unit of Evolution

The unit of evolution is a scoped, evidence-backed rule about collaboration. A rule connects a user statement or repeated pattern to a useful observable action.

For example, "Prefers technical detail" is too broad. "For implementation plans, include exact steps, validation, and unresolved limits" tells the agent when and how to adapt.

The process updates persisted instructions for the individual user. It does not train model weights, modify host policy, or grant additional authority.

## Components

| Component | Responsibility |
| --- | --- |
| `SKILL.md` | Stable controller and workflow routing |
| `references/` | Evidence, profile, and reflection mechanics |
| `assets/templates/` | Blank output formats |
| Private `USER_SKILL.md` | Current active personalization guide |
| Private reflection logs | Minimal evidence and change records |
| Private state | Source checkpoints and committed profile version |
| Agent host | Identity, storage, tool access, lifecycle, synchronization, and enforcement |

One user guide remains current. Daily records describe how it changed. The agent reads historical detail only when the current task needs it.

## Learning Loop

1. Observe newly available authorized messages.
2. Separate facts, preferences, behavioral observations, task instructions, and temporary states.
3. Check sources, independent repetition, scope, and counterevidence.
4. Propose the smallest useful profile change.
5. Validate and publish through the host's persistence mechanism.
6. Load relevant rules for a subsequent interaction.
7. Use real feedback to keep, refine, or withdraw the affected rule.

An explicit correction can enter this loop immediately without waiting for the daily event.

## Evidence and Confidence

Confirmed and tentative are operational evidence categories. They are not numeric probabilities, diagnoses, or personality scores.

Directly stated lasting preferences can be confirmed immediately. Repeated patterns are tentative until the user confirms them. An observation copied into several contexts is not independent support.

The guide records scope so a new request can override an old default without erasing unrelated preferences. "Be brief today" and "Explain complex proposals fully" can coexist when their scopes are represented correctly.

## Context Use

Load the compact current guide, then select the few rules relevant to the response. Retrieve original evidence only for a conflict, inspection request, or justified review.

This reduces unnecessary history loading. It does not change a model's supported context length, bypass provider limits, or replace the host's context management.

## Isolation and Sharing

The host maps verified users to private namespaces. A display name is not proof of identity. Cross-channel continuity needs an explicit identity mapping; cross-device continuity also needs a working synchronization service.

The host defines which preferences may be used in a group. Using a presentation preference in a shared conversation does not authorize repeating its private source message.

## Failure Boundaries

A proposed change can fail before publication. A published guide can fail to load later. A loaded rule can fail to affect the response. A response can follow a rule without receiving confirming feedback.

The package keeps these stages separate so reports remain meaningful. The actual host must enforce authorization, atomic storage behavior, synchronization, deletion, and scheduling.

See [Host Integration](host-integration.md) for the execution contract and [Evaluation](evaluation.md) for observable checks.
