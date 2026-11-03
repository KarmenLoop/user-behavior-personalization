# Changelog

## 0.4.0 — 2026-11-03

- Import selected JSON/JSONL conversations and extract open-text English/Chinese preferences, workflows, goals, and constraints for review.
- Add an inspectable portrait with source examples, writing features, and eligible recent/older request-length comparisons.
- Add experimental historical next-request retrieval with original sequence evidence, recency weighting, context boundaries, and abstention.
- Add local host-model proposal staging with known-source and exact-quote validation; user review remains required.
- Add message-level and conversation-level deletion cascading to dependent proposals, rules, writing features, and original transitions.
- Retain failed evaluations: the new 18-query holdout produced 4/12 expected positive suggestions (English 0/6, Chinese 4/6) and correctly abstained on all 6 negative cases. Forecast coverage remains limited.
- Publish original bilingual conversation-learning diagrams, an actual import/review/delete tutorial, and a reproducible frozen diagnostic. No online DeepSeek call or new successful model-host certification is claimed.

## 0.3.0 — 2026-11-03 (merged intermediate source; not released)

- Add opt-in structured observations, recency-weighted evidence, candidate explanations, and explicit accept/reject review.
- Add observation deletion and profile reset, including dependent learned rules and source replay suppression.
- Match context labels exactly; normalize expiry times and serialize managed exports with profile changes.
- Keep wrapper receipts free of raw prompts and model output; add a local chat-request builder and a reproducible synthetic CLI walkthrough.
- Publish original bilingual learning diagrams, practical host guides, research notes, and twenty answered usage questions.
- Preserve the limits of host acceptance: the current Codex model attempt timed out, Cursor required authentication, and no live DeepSeek call or native desktop GUI test was run.

## 0.2.0 — 2026-10-23

- Add a local SQLite profile adapter, five CLI/MCP tools, Codex/Cursor configuration, and a pre-invocation wrapper.
- Preserve the original acceptance claims and scope in the archived v0.2.0 overview; they are not current-version model acceptance.

## 0.1.1 — 2026-10-23

- Add selectable English and Simplified Chinese project and user guides.
- Align download names and workflow illustrations with this release; retain historical evidence at its original version.


## 0.1.0 — Initial Package

### Added

- An English-language skill for evidence-backed user personalization.
- Immediate correction, daily reflection, selective recall, and memory-control workflows.
- Private user guide, reflection, and checkpoint templates.
- Host integration, identity, synchronization, and recovery guidance.
- Synthetic conversations and evaluation scenarios.
- Contribution, support, security reporting, and Apache-2.0 licensing documents.

### Scope

This version is an instruction and documentation package. It does not include a background scheduler, an agent runtime, a synchronization service, or a production-certified host adapter. Release publication and host validation are separate steps.
