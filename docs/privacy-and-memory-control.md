# Privacy and memory control — v0.3.0

[English](privacy-and-memory-control.md) · [中文](privacy-and-memory-control.zh-CN.md)

Profiles are private collaboration data. They do not authorize actions or reveal a person's inner state.

## Collection and consent

Observation is disabled unless the operator enables `--enable-observations`. The host must obtain the user's permission, bind the right subject, and pass only authorized feedback. A flag is a technical setting, not proof of legal consent. The adapter accepts bounded dimensions and values; it does not scrape conversations, monitor a screen, read keystrokes, or collect browsing history.

Do not create evidence from assistant messages, third-party quotes, silence, inferred mood, or fabricated sessions. Do not infer health diagnoses or sensitive identity attributes. Never put credentials or unrelated private text in source IDs, contexts, rule statements, or summaries. Structured fields reduce unnecessary storage but do not make user-provided strings harmless.

## Storage and host exposure

Keep `--root` outside public repositories. Local files use restricted modes where the OS supports them; Windows permissions still require appropriate account and ACL configuration. SQLite is not an encryption layer. A shared local account can access files that account can read; subject namespaces are not a substitute for OS isolation.

`profile_read` supplies selected confirmed rules to the host. A remote model may receive those rules and the task under the host/provider's own network and retention policy. `build_context.py` sends nothing, but its stdout contains private request content if you redirect it. Review the destination before sending anything.

The v0.3.0 wrapper streams model output to the terminal and retains metadata receipts. It does not persist prompt or raw output files. Terminal capture, host logs, external exports, provider history, and backups remain separate copies. v0.2.0 `host-runs` directories can contain unbound raw output; review and remove those manually after checking ownership and any records you need to keep.

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
