# How the workspace works — v0.7.0

[English](architecture.md) · [中文](architecture.zh-CN.md)

One private SQLite store connects four steps. You can inspect the evidence, change a decision, and see what a later task will actually receive.

## 1. Import selected feedback

The browser imports a supplied conversation. The foreground watcher follows one explicitly selected JSONL file. Both call the same conversation importer with a fixed subject, stable message IDs, chronological snapshots, and revision checks. Neither searches other histories.

The importer keeps bounded sanitized user excerpts, surface features, source hashes, and original request transitions. Assistant, system, and tool messages do not become user evidence. Known credential and email patterns are masked; this is not complete personal-information detection.

## 2. Review a useful preference

A direct lasting statement can become an open-text proposal: “From now on, include rollback checks.” Recurring feedback such as “Too long. Please keep it brief.” follows a separate habit learner. Its supported English/Chinese cues produce typed candidates after enough independent sessions, with competing evidence and recency considered. Repetition within one session does not create additional votes.

The user reviews candidates before they become confirmed rules. Custom terminology, goals, and workflow statements remain available through open-text proposals. Descriptions of how a user writes are distinct from preferences for how an assistant should answer.

## 3. Resolve the next task

The workspace, request builder, and CLI wrapper share one resolver. It considers confirmed scope, expiry, task-only overrides, omitted rules, and the preference budget. A context-specific typed preference takes precedence over a global preference for the same dimension. Current task controls take precedence over both.

The result contains the baseline task, actual personalized prompt, selected rules, and exclusion reasons. A preview does not modify the profile or call a model. Arbitrary semantic conflicts between free-text rules still need deliberate correction.

## 4. Check whether it helped

Saving a plan records a task hash, revision, and exact rule-version fingerprints. An explicit rating identifies whether the user reviewed the prompt or used a resulting response. The summary separates those two sources of feedback. A changed rule does not inherit old ratings; silence creates no rating.

These records help compare actual experiences. They do not automatically certify that a model ran or establish an improvement in user outcomes.

## Lifecycle and older capabilities

All writes use revisions. Forgetting source evidence cascades through affected proposals, rules, writing features, original transitions, and linked plans/ratings. A deleted middle message leaves a gap; it does not create a new A→C transition. Reset clears profile content and pauses personalization; minimal replay markers and selected-feed cursors remain.

The [conversation guide](conversation-guide.en.md) covers portraits, host-model proposals, and the unchanged experimental historical forecaster. Original [v0.4.0 conversation diagrams](images/conversation-learning-v0.4.0.en.svg) and [structured-feedback architecture](structured-architecture.en.md) remain as references. The [workspace tutorial](tutorial.en.md) is the starting point for current use.


## Selected-source semantic workflow and actual comparisons

The optional v0.7.0 model runner sends selected excerpts through an ephemeral, tool-disabled Codex subprocess. Exact authored source quotes, subject/context binding and a captured revision are checked before suggestions enter the existing pending-proposal store. A profile guard is checked before every dispatch and throughout IO; stale results never become new rules or saved answers. Network IO holds no SQLite transaction.

One resolver selects by context and matching task conditions before applying specificity. It preserves old unconditioned records and abstains on equally specific incompatible typed values. Baseline and personalized answer prompts share the task, policy, temporary choices and conditions; only saved preferences differ. Both must finish before a single transaction saves the prepared manifest and private pair.

The loopback job API keeps one active job and up to 50 metadata records in memory. A duplicate request ID with identical arguments replays; changed arguments reject. Persistent reveal state distinguishes blind votes from later revisions. Pair storage is bounded to20, and deletion follows source→rule→plan→comparison dependencies. These records are runtime state and user reports, not training data or a quality grade. [Walk through the workflow](semantic-learning.en.md).
