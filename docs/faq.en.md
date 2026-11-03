# Twenty practical questions — v0.4.0

[English](faq.en.md) · [中文](faq.zh-CN.md)

## 1. Can I give it actual conversations instead of manually tagging preferences?

Yes. Select an authorized JSON or JSONL conversation and import it with learn_conversation.py or conversation_import. The offline extractor examines user text for explicit English and Chinese cues, keeps source evidence, and proposes open-text preferences. You do not have to choose one of the older six dimensions.

## 2. What kinds of things can it learn?

Communication preferences, project terminology, recurring workflows, declared goals, and constraints. For example, a request to include rollback checks in release plans stays as that concrete rule. A learning goal is stored as a goal, not interpreted as evidence of ability or personality.

## 3. Will it learn private project names and terminology?

An explicit instruction such as “Please remember: call our staging environment rehearsal” can become a sourced proposal. The wording can remain specific to your context. Review it before accepting; known credential patterns are redacted, and private terminology should stay in your private profile.

## 4. Does it understand indirect hints or every paraphrase?

No. The bundled extractor uses conservative explicit-cue rules, so indirect preferences can be missed. The optional host-model bridge can propose broader interpretations from exact source quotes, but each proposal still needs user review. Check extraction misses separately from code correctness.

## 5. How does the working portrait differ from a list of settings?

profile_portrait combines confirmed preferences, pending open-text proposals, descriptive writing statistics, and source examples for one context. It can show what is established, what is merely suggested, and what the imported writing actually looks like.

## 6. Can it imitate how I write?

It exposes examples and observable features—length, lists, questions, and language mix—that you and a host can inspect. It does not automatically equate your writing with your desired reply style or train a style-cloning model. Confirm specific response rules if you want the assistant to mirror a chosen aspect.

## 7. How does it notice a change in my habits?

The portrait can compare request length in the last 30 days with days 31–90 when both windows contain at least three sessions. This is a descriptive comparison, not a diagnosis or automatic preference update. A new explicit correction remains the best way to change a confirmed default.

## 8. What does forecasting actually predict?

It retrieves what you previously asked for after requests similar to the current one, within the same context. The output contains original follow-up wording and matching historical examples. It suggests a plausible next request rather than predicting private thoughts or executing a plan.

## 9. Why can it miss a next step that seems obvious to me?

Lexical similarity is limited. Different wording, short or ambiguous requests, insufficient independent sessions, old evidence, or competing workflows can lead to abstention. A small diagnostic may reveal these gaps; its pass rate does not establish broad real-world accuracy.

## 10. Is the forecast limited to testing, planning, or six canned actions?

No. The conversation forecast returns actual retained follow-up requests, so it can include a project-specific checklist, a custom terminology question, or another concrete request. The older workflow_next_step label remains a separate structured-feedback option.

## 11. Can Codex and Cursor share the learned profile?

On one machine, configure both with the same private root and correctly bound subject. Their MCP calls use the same committed state. Identity mapping, actual host tool use, online account access, and cross-device synchronization are separate responsibilities.

## 12. Where does DeepSeek fit?

Your host may send profile_model_context output to an authorized model and return sourced proposals through profile_model_propose. The local adapter validates known source keys, exact quotes, scope, and basic bounds. It makes no DeepSeek call and never auto-confirms a model proposal.

## 13. How do I import new messages without duplicating old evidence?

Append to the original session prefix in order and submit that full prefix plus the new messages. Identical user records are deduplicated. Changed user text, a different context, or reordered history is rejected rather than silently rewriting the sources behind an accepted rule.

## 14. What is saved from a long conversation?

At most 400 user records across 80 sessions. Each retained excerpt contains up to 600 sanitized characters, plus features and hashes; import accepts up to 100 messages per batch and 4,000 characters per message. Non-user message text is not stored as user evidence. Automatic extraction can miss a preference beyond the retained excerpt.

## 15. Does redaction mean every private detail is removed?

No. Recognizable credential and email patterns are redacted. Novel secrets, personal descriptions, or obfuscated values may not be detected. Choose files deliberately, inspect the resulting portrait/export, and keep the store private. No background history crawler is installed.

## 16. How do I correct an inferred preference that is wrong?

Reject the pending proposal. If it was accepted, review a new sourced proposal with replace_rule_id pointing to the old rule, or use profile_correct with a genuine new source. Arbitrary free-text contradictions are not automatically resolved; inspect both statements.

## 17. Can I delete one message without losing the entire conversation?

Use profile_forget_messages with the source keys. The adapter removes dependent proposals, rules, writing contributions, and transitions. A broader linked cascade can be needed to prevent resurrection. It never invents a direct A-to-C transition when B was deleted.

## 18. What happens if I pause or reset it?

Pause stops ordinary recall and learning while export/deletion remain available. Reset clears profile content and ends paused, retaining minimal hashes to suppress old-source replay. Copied exports, provider histories, old unbound wrapper logs, and external backups require their own cleanup.

## 19. How do psychology and explain-back help?

They inform the interaction: offer an example or optional explain-back, identify a specific gap, and let the user choose what helps. The profile can retain an explicitly stated teaching preference or goal. It does not assign personality types, diagnose mental health, or claim a validated educational outcome.

## 20. How can I judge whether the new version is better?

Run the actual import/review/forecast/delete tutorial, then read the frozen diagnostic’s coverage, conditional precision, abstentions, and misses. Finally test an accepted preference in a real host and ask whether it helped. Keep initial failures and model-call failures visible; code tests alone do not measure personalization quality.

[Tutorial](tutorial.en.md) · [Evaluation](evaluation.md)
