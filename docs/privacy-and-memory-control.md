# Privacy and memory control — v0.5.0

[English](privacy-and-memory-control.md) · [中文](privacy-and-memory-control.zh-CN.md)

Profiles are private collaboration data. They do not authorize actions or reveal a person's inner state.

## Collection and consent

Structured observation is disabled unless the operator enables `--enable-observations`. Conversation import separately requires `--enable-conversations`. The host must obtain the user's permission, bind the right subject, and pass only authorized feedback. A flag is a technical setting, not proof of legal consent. The structured path accepts bounded dimensions and values. The conversation path accepts selected text, retains bounded sanitized user excerpts, and extracts open-text proposals. Neither path scrapes conversations, monitors a screen, reads keystrokes, or collects browsing history.

Do not create evidence from assistant messages, third-party quotes, silence, inferred mood, or fabricated sessions. Do not infer health diagnoses or sensitive identity attributes. Never put credentials or unrelated private text in source IDs, contexts, rule statements, or summaries. Structured fields reduce unnecessary storage but do not make user-provided strings harmless.

## Storage and host exposure

Keep `--root` outside public repositories. Local files use restricted modes where the OS supports them; Windows permissions still require appropriate account and ACL configuration. SQLite is not an encryption layer. A shared local account can access files that account can read; subject namespaces are not a substitute for OS isolation.

`profile_read` supplies selected confirmed rules to the host. A remote model may receive those rules and the task under the host/provider's own network and retention policy. `build_context.py` sends nothing, but its stdout contains private request content if you redirect it. Review the destination before sending anything.

The current wrapper streams model output to the terminal and retains metadata receipts. It does not persist prompt or raw output files. Terminal capture, host logs, external exports, provider history, and backups remain separate copies. v0.2.0 `host-runs` directories can contain unbound raw output; review and remove those manually after checking ownership and any records you need to keep.

## Inspect and correct

Use `profile_export` to inspect the actual profile, including while paused. Use `profile_insights` to distinguish observations and candidates from confirmed rules. It is better to say “three sessions support this style in code review” than to assign a personality label.

A correction uses the current revision and a new genuine source. Explicit instructions outrank inferred preferences. A free-text rule without structured dimensions may still need manual conflict review; no semantic diagnosis is performed.

## Pause

`profile_pause` stops ordinary recall, observations, and candidate adoption. Export and deletion remain available. Pause does not delete saved content; reset and forget are separate operations. Removing the observation flag prevents future collection but does not itself erase older observations.

## Delete and prevent replay

| Operation | Controlled content removed |
|---|---|
| `profile_forget` | Selected rule and history, linked learned evidence, managed export, and subject receipts. For a typed rule, evidence in that context/dimension is removed so an older same-session observation cannot recreate it; a global typed rule covers that dimension across contexts. |
| `profile_forget_observations` | Selected observations and dependent learned rules/history; affected learned context/dimension evidence is cleared as part of preventing resurrection. |
| `profile_reset` | Profile content and managed artifacts; the resulting profile is paused. |

The adapter retains minimal source hashes to suppress replay. These markers are still user-associated metadata; they are not the forgotten text and are not an anonymization guarantee. Do not re-import a forgotten source under a new ID. If you need to remove the entire data root, stop all writers and decide how your host will prevent old histories being ingested again.

Deletion does not promise physical SSD erasure or deletion from external copies. It cannot erase a provider's conversation, a screenshot someone took, a copied export, or an unrelated backup it never controlled.

## Shared and synchronized use

A common machine can share a store only with appropriate filesystem permissions and a trusted mapping for each subject. A group chat may use a style preference without disclosing its private source; the host must decide what is appropriate. Similar names do not prove two accounts belong to the same person. This release supplies no cross-device synchronization service.

Use profiles to reduce friction, preserve factual disagreement, and support the user's choices. Do not use them to exploit vulnerability, encourage dependency, or hide consequential decisions.

## Local process visibility

Codex receives the composed prompt on stdin. The current Cursor CLI path accepts it as a positional argument, so other tools running as the same local user may be able to inspect it in process arguments. Use the MCP path or an appropriate local account boundary when that exposure is unacceptable. Streaming output can still be captured by your terminal or host; metadata-only adapter receipts do not erase those separate copies.

## Conversation evidence and derived data

Conversation import keeps at most 400 user records across 80 sessions. Each record retains the first 600 sanitized characters plus surface features, source/content hashes, and original sequence references. Assistant/system/tool text is ignored as user evidence. Known credential and email patterns are redacted; other personal information may remain. Automatic extraction can miss statements beyond the retained excerpt. Inspect the portrait/export after an import.

`profile_forget_messages` deletes selected source keys; `profile_forget_conversation` deletes a session. Both cascade through dependent proposals, accepted rules, writing statistics, and original transitions, including linked evidence where needed to prevent resurrection. Deleting a middle message does not create a new neighbor-to-neighbor transition. Minimal hashes remain for replay suppression.

`profile_model_context` returns up to 20 recent user excerpts to the calling host. It performs no network call, but a host may forward them to an authorized provider. An exact quote check proves correspondence to the retained excerpt, not consent or correctness of an interpretation. Treat portraits, forecast examples, and model context as private user data rather than ordinary public response instructions.

## Local workspace and task plans

The workspace binds to `127.0.0.1`, checks Host/Origin, and requires a per-start token for API calls. It fixes the subject/root at startup and loads no external assets. It is a local tool, not a public multi-user hosting setup. User content is rendered as text. Browser storage saves the language preference; conversation state and task content are not persisted there.

A preview builds prompt content in memory. Preparing a plan saves its task hash, context, revision, and exact rule-version fingerprints, not the raw task or response. An explicit rating is a user report; its basis distinguishes prompt review from reported response use. Plan and rating metadata can still reveal usage patterns. `profile_plan_forget` removes the selected plan and feedback. Deleting dependent source evidence or rules removes affected plans and feedback as well.

## Selected-file watcher

The watcher reads only the regular file explicitly selected with `--input`. Its cursor stores the filename, byte offset, line/import counts, prefix hash, status, and timestamp—not a second copy of the conversation. Cursors are private metadata under `watchers/` and survive profile reset to avoid accidentally replaying old content. Pause prevents advancing over unread data.

The selected JSONL file is outside the profile's controlled copy; deletion and reset do not erase it. Stop its writer/watcher before deliberate source or cursor cleanup. Do not remove replay markers simply to re-ingest forgotten material. See [feed recovery](automatic-learning.en.md).
