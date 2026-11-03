# Twenty practical questions — v0.3.0

[English](faq.en.md) · [中文](faq.zh-CN.md)

## 1. How does an assistant learn my working style?

You can save a direct preference immediately. If you enable observations, the host can record authorized feedback with a context, source, and session. The adapter proposes a pattern only after evidence review; you decide whether it becomes a default.

## 2. Will it know what I am thinking?

No. It can explain observed collaboration patterns and suggest a next step in a known context. It cannot establish private motives, predict every decision, or read thoughts. Weak or conflicting evidence should produce no adopted inference.

## 3. Can I use it without uploading conversations?

Yes. The local demo, storage, review, and privacy tools need no network call. A connected cloud model may receive the selected rules and task under that host’s own policy; the adapter does not crawl or upload your whole history.

## 4. What does it actually remember?

Explicit rules and structured feedback about response length, structure, teaching, initiative, workflow next steps, and language. The host supplies source identifiers and minimal summaries for explicit rules. Full chat archives and psychological labels are not required.

## 5. How do I keep work and personal preferences separate?

Use distinct subjects or separate private roots where the identity and permissions require isolation. Within one subject, choose stable contexts such as code-review and travel-planning. Matching is exact and case-insensitive; * is an explicit global scope for rules.

## 6. Can Codex and Cursor share a preference?

On one machine, configure both with the same private root and correctly bound subject. Their MCP calls then use the same committed profile. This does not link online accounts or synchronize another device.

## 7. Does DeepSeek connect directly to this MCP server?

A chat API is not itself an MCP client. Use build_context.py to generate scoped messages for your own chat client. A tool-using client must also implement an allowlisted bridge and user authorization. This release does not include a live DeepSeek tool loop.

## 8. What is the difference from a system prompt or custom instructions?

A prompt can carry a preference, but it does not by itself provide source tracking, revisions, context-specific recall, review, or deletion. This adapter adds those operations; the host still decides how to load its results within the instruction hierarchy.

## 9. Is it RAG, fine-tuning, or a new model?

None of those. This is structured preference memory and a deterministic review workflow. Updating a profile does not retrain weights, increase context length, or create an embedding index over your conversations.

## 10. Why does it require three sessions?

That is an engineering guard against adopting a one-off response as a habit. There must also be sufficient recency-weighted support and a recent supporting event. The threshold is not a statistical or psychological guarantee.

## 11. Can repeating one message make the score increase?

Replaying the same source is deduplicated. Within a context and dimension, only the latest observation from a session contributes. The host must not fabricate source/session IDs; the adapter cannot independently verify real-world interactions.

## 12. What happens when I change my mind?

Correct the existing rule with a new source and current revision. A temporary request still overrides an old default for the task at hand. New feedback can oppose an old pattern; confirmed preferences should be explicitly reviewed or corrected, not silently overwritten.

## 13. Why does it sometimes decline to suggest a preference?

Too few independent sessions, old evidence, counterevidence, or an applicable confirmed preference can prevent review. Inspect profile_insights for the actual reasons. Abstaining is an intended outcome.

## 14. Can it imitate my writing?

It can apply confirmed choices such as language, length, and structure. It does not clone a person’s identity, reproduce a private writing corpus, or guarantee stylistic imitation. Avoid turning a style request into broad assumptions about the person.

## 15. How does explain-back or Feynman-style learning fit?

The user may choose to explain a concept in their own words, see a worked example, or practice. The host supplies the lesson; the adapter remembers confirmed format preferences. This is an educational interaction, not a personality assessment.

## 16. Will the next-step feature act for me?

No. A workflow_next_step preference can suggest testing after implementation or reviewing before delivery. It does not execute tools, send messages, purchase anything, or increase permissions.

## 17. How do I stop learning without losing my data?

Use profile_pause. Ordinary recall and learning stop, while export and deletion remain available. To stop new observations at configuration level, remove --enable-observations as well. Neither action alone deletes existing content.

## 18. Does “forget” remove everything everywhere?

It removes the specified controlled profile content and related learning data, plus managed artifacts. Minimal source hashes suppress replay. Copied exports, old unbound wrapper output, provider logs, and external backups require separate cleanup. No physical disk-erasure guarantee is made.

## 19. Why did a write fail with a stale revision?

Another update changed the profile after you read it. Read the current revision and inspect the change before deciding whether to resubmit. Do not retry blindly or replace a newer user correction.

## 20. How can I tell whether this improves my assistant?

Run the local tutorial, then test an actual host response, a correction, and a deletion using synthetic data. Compare similar tasks and ask whether fewer style corrections are needed. Local tests or a support score do not prove user satisfaction; see the evaluation guide.

[Tutorial](tutorial.en.md) · [Evaluation](evaluation.md) · [Privacy controls](privacy-and-memory-control.md)
