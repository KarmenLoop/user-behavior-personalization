# Local tool reference — v0.5.1

[English](tools.en.md) · [中文](tools.zh-CN.md)

CLI calls, MCP stdio, and the local workspace share the same adapter. Identity is fixed by `--subject`; callers cannot change it in a tool argument. The runtime exposes **25 tools**. Read `scripts/host.py` for the complete current JSON schemas.

| Tool | Inputs (`?` = optional) | Result |
|---|---|---|
| `profile_read` | `context` | Read confirmed rules. |
| `profile_correct` | `expected_revision, rule` | Save an explicit preference or correction. |
| `profile_pause` | `expected_revision, paused` | Pause or resume ordinary use. |
| `profile_forget` | `expected_revision, rule_id` | Forget a rule and dependent evidence. |
| `profile_export` | `—` | Inspect private state, including while paused. |
| `profile_observe` | `expected_revision, event` | Record an authorized typed feedback event. |
| `profile_insights` | `context` | Inspect structured feedback candidates. |
| `profile_review` | `expected_revision, candidate_id, decision, source_id` | Review a structured candidate. |
| `profile_forget_observations` | `expected_revision, observation_ids` | Remove observations and dependent rules. |
| `profile_reset` | `expected_revision` | Clear content and end paused. |
| `conversation_import` | `expected_revision, conversation` | Import one authorized conversation snapshot. |
| `profile_proposal_review` | `expected_revision, proposal_id, decision, source_id; replace_rule_id?` | Review an open-text proposal; optionally replace a rule. |
| `profile_portrait` | `context` | Inspect confirmed preferences, proposals, and writing observations. |
| `profile_forecast` | `context, request` | Experimental historical follow-up retrieval. |
| `profile_forget_conversation` | `expected_revision, session_id` | Remove a conversation and derived content. |
| `profile_forget_messages` | `expected_revision, source_keys` | Remove selected source messages and dependencies. |
| `profile_model_context` | `context` | Build local source context for a host model. |
| `profile_model_propose` | `expected_revision, proposals` | Validate exact source quotes and stage proposals. |
| `profile_habits` | `context` | Find recurring feedback with evidence and conflicts. |
| `profile_habit_review` | `expected_revision, context, candidate_id, decision, source_id` | Review a ready conversation-derived habit. |
| `profile_plan` | `context, task; task_overrides?, omit_rule_ids?, max_preference_chars?` | Preview actual task prompt selection; no write or model call. |
| `profile_plan_prepare` | `expected_revision + profile_plan fields` | Save a plan manifest for later feedback. |
| `profile_outcome` | `expected_revision, plan_id, source_id, rating, basis` | Record the user’s explicit assessment. |
| `profile_outcome_summary` | `context` | Inspect ratings by basis and exact rule version. |
| `profile_plan_forget` | `expected_revision, plan_id` | Remove a plan and its feedback. |

## Revisions and decisions

Fetch the current revision with `profile_read` or `profile_export` immediately before a write. After `REVISION_CONFLICT`, reload and reconsider the change; do not blindly replay an old decision. Review decisions are `accept` or `reject`. A source identifier records a host attestation, not proof that a person consented.

Conversation collection needs `--enable-conversations`; structured event collection separately needs `--enable-observations`. Candidates remain inactive until reviewed. See the [conversation guide](conversation-guide.en.md) and [structured feedback guide](structured-feedback.en.md) for executable examples.

## Plan a temporary exception

This read-only call needs no revision and changes no saved preference:

```sh
printf '%s' '{"context":"writing","task":"Explain the release tradeoffs.","task_overrides":{"response_length":"detailed"}}' | \
  python3 -B scripts/host.py --root ../private-profile --subject owner call profile_plan
```

`task_overrides` supports the six collaboration dimensions below. `omit_rule_ids` accepts up to 30 existing rule IDs. `max_preference_chars` is 200–12000 (default 4000). Explicit controls override recognized task-text cues. These options are shared by `build_context.py` and `run_host.py` through `--override`, `--omit-rule`, and `--preference-budget`.

| Dimension | Values |
|---|---|
| `response_length` | `concise`, `balanced`, `detailed` |
| `structure` | `conclusion_first`, `steps`, `examples`, `code_first`, `bullets` |
| `teaching` | `explain_back`, `worked_example`, `practice` |
| `initiative` | `ask_first`, `suggest_next` |
| `workflow_next_step` | `clarify`, `plan`, `implement`, `test`, `review`, `summarize` |
| `language` | `en`, `zh` |

## Save and assess a plan

`profile_plan_prepare` takes the same fields plus the latest revision. Use the returned `plan.plan_id` with `profile_outcome`, again fetching a fresh revision. `rating` is `helpful`, `unhelpful`, `mixed`, or `not_sure`; `basis` is `prompt_review` or `response_use`. The latter records reported response use, not independently verified model execution.

At most 100 prepared plans are stored per subject. A plan keeps one current rating; updating it replaces that rating rather than adding a vote. Its source history is bounded to 100 feedback revisions. Use `profile_plan_forget` to remove a plan and associated feedback. Previewing a plan stores neither task text nor a plan record.
