# Twenty practical questions — v0.7.0

[English](faq.en.md) · [中文](faq.zh-CN.md)

## 1. What can I actually try without a model account?

Open the local workspace, import the synthetic three-session example, review a habit, preview a task, override it once, and record a prompt-review rating. These operations use the real local store. A preview is the prompt your host can use, not an invented model answer.

## 2. Does “automatic learning” mean it reads all my chats?

No. You select a conversation or one append-only JSONL feed. The watcher imports complete new records while its foreground process runs. The learner examines retained user excerpts for supported feedback cues; it does not discover accounts, read screens, or install a background service.

## 3. Why do repeated corrections need three sessions?

Independent sessions reduce the effect of repeating one instruction in a single conversation. Recency, competing evidence, and a weighted support threshold also matter. The thresholds are engineering heuristics, not psychological confidence levels. A ready habit still needs your review.

## 4. Must a direct preference wait for repetition?

No. “From now on, include rollback checks” can become an open-text proposal immediately. Review that explicit proposal instead of manufacturing more sessions. Recurring habits and direct instructions share the final profile but have different evidence paths.

## 5. What if I usually want short answers but need detail today?

Choose a detailed response under “Just for this task,” or use --override response_length=detailed. The resolver excludes the saved brevity rule for this request and explains why. Your long-term default is unchanged.

## 6. Does the task preview match what the host receives?

The workspace, build_context.py, and run_host.py share one preference resolver. They produce the same selected preference content for the same task and options. A host may add its own higher-priority instructions; previewing does not prove a provider executed or followed the request.

## 7. How can I tell whether a preference helped?

Save a plan, then give an explicit rating. Distinguish reviewing the prompt from using a resulting response. Compare similar tasks and keep unhelpful or mixed results. The summary tracks exact rule versions; successful commands and silence do not count as positive feedback.

## 8. Will an old positive rating follow a corrected rule?

No. Each plan identifies exact preference-version fingerprints. The revised rule starts without inherited ratings. Updating a plan’s rating replaces its current assessment rather than adding another vote.

## 9. Can it learn our terminology and unusual workflow?

Use an explicit sourced proposal for a project term, goal, constraint, or custom workflow. The recurring-cue learner supports a bounded set of collaboration dimensions; it does not infer every custom concept. An optional host model can stage broader proposals with exact source quotes, followed by your review.

## 10. Can it imitate my writing?

The portrait exposes writing examples, length, lists, questions, and language mix. Those observations describe how you wrote, not automatically how you want answers written. Confirm the specific aspects you want your host to use. The package does not train a style-cloning model.

## 11. How does it handle changing preferences?

Make an explicit correction for a new lasting default, or use a task-only exception. Habit evidence decays over time and conflicting evidence can prevent adoption. The portrait can compare request-length windows when both have enough sessions, but that observation never automatically changes a preference.

## 12. What belongs in the watched JSONL file?

Each line is a full conversation object with session_id, context, and messages, followed by a newline. To extend a session, append a snapshot containing its unchanged original prefix plus new messages. The separate learn_conversation.py --format jsonl command instead accepts one message per line.

## 13. Will the watcher repeat everything after a restart?

It saves a progress cursor and verifies the already-consumed prefix. Complete imported records are not treated as new support. A partial last line waits; a rejected record stops processing before that line. Changed earlier bytes raise FEED_HISTORY_CHANGED rather than silently rewriting history.

## 14. Can Codex and Cursor share the same profile?

Yes, on one machine with the same private root and correctly bound subject. The MCP helpers configure both hosts; the wrapper applies preferences before a new CLI invocation. Real host tool use, accounts, and model responses require separate checks. No cross-device sync service is included.

## 15. Where does DeepSeek fit?

Your client can send messages built by build_context.py to its chosen chat API. For learning, profile_model_context supplies retained excerpts and profile_model_propose validates returned sourced proposals. Neither tool calls DeepSeek itself, and source validation does not automatically confirm a proposal.

## 16. Does it predict what I will think next?

No. The retained experimental forecaster retrieves actual follow-ups after similar historical requests. It does not execute them. Its v0.4.0 unseen test covered 4/12 positive cases, including 0/6 in English; that limitation is unchanged by the new habit workflow.

## 17. What gets stored, and what stays in the browser?

Conversation storage retains bounded sanitized excerpts and source metadata. Prepared plans retain hashes and rule versions, not raw tasks or model output. Browser storage keeps the language choice, not the profile. Known-secret redaction is incomplete; keep the root private and inspect imported evidence.

## 18. Can I remove one message or stop learning?

Yes. Delete a source message, a conversation, a preference, or a plan. Related derived records and ratings are removed where necessary. Pause stops ordinary use; reset clears profile content and ends paused. Minimal replay hashes and feed cursors remain. External source files, provider logs, and backups need their own cleanup.

## 19. What do psychology and explain-back contribute?

They inform the interaction: offer an optional explanation in the user’s own words, identify a concrete gap, then try an example or practice. Store an explicitly preferred teaching format. This is not personality diagnosis, a fixed learning-style label, or a validated educational-outcome claim.

## 20. How should I judge this release?

Try your own authorized corrections, inspect false positives and misses, test temporary exceptions and deletion, and evaluate an actual host response. Read the preserved failed diagnostics as well as later independent results. Working storage, a successful browser demo, language coverage, and usefulness are separate evidence.

[Tutorial](tutorial.en.md) · [Evaluation](evaluation.md)
