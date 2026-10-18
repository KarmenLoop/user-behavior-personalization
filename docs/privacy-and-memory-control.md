# Privacy and Memory Control

Profiles describe how to assist a person. They are private user data, not public skill documentation or a source of extra execution authority.

## Authorization and Minimum Necessary Data

Use only conversations available under the host's authorization. Make the memory setting visible and honor changes to it. Analyze the current user, not people mentioned in quoted material.

Store a compact preference with a source reference and minimal supporting excerpt or summary. Avoid full conversation copies when a short record is sufficient. Never store credentials, tokens, API keys, passwords, or unrelated private material in a guide.

Do not infer sensitive attributes or health diagnoses from language, mood, habits, or interests. If a user explicitly requests storing a necessary sensitive fact, follow the host's authorization and retention rules and minimize its scope.

## Storage and Exposure

Place live memory outside the public repository. The repository's `.gitignore` patterns are a fallback, not an access-control system or a complete secret scanner.

Filesystem permissions, encryption, backups, model-provider retention, and synchronized copies are the host operator's responsibilities. The skill does not independently guarantee them. Use synthetic fixtures in public reports and evaluations.

## Inspection and Correction

For "What do you remember about me?", show the actual saved guide, distinguishing confirmed rules, tentative patterns, temporary instructions, and explicit background facts.

For a correction, change the current behavior immediately. Persist through the supported update mechanism, remove the incompatible active rule, and report whether the write actually succeeded.

## Pause and Disable

For "Stop analyzing my habits" or "Stop remembering my preferences", determine the requested scope. Disable ordinary analysis and profile access for that scope through the host's supported controls. Do not silently continue writing daily observations.

An explicitly requested export or deletion can still be performed as an authorized memory-maintenance operation. Disabling ordinary personalization does not require denying the user control of their stored data.

## Forgetting and Deletion

Apply a forget request to all controlled copies containing the affected content:

- The current guide.
- Previous profile versions.
- Reflection records and exported copies under the host's control.
- Search indexes or caches maintained by an adapter.
- Synchronized replicas where the host supports propagation.

Do not reconstruct a deleted preference by replaying an older conversation. Where supported and permitted, retain only the minimum content-free source or record identifiers needed to suppress that replay. Such markers are still subject to the user's deletion requirements and the host's retention policy.

If the user requests deletion of all memory, explain any supported choice between retaining a minimal suppression marker and disabling future analysis of the old source range. Do not retain the forgotten fact inside a tombstone.

Original chat records, provider logs, or backups may be outside this skill's control. State exactly which stores were changed and which remain subject to other systems. Do not promise deletion from systems that were not actually accessed.

## Export

Export only data owned by the requesting user and within their access scope. Include clear evidence categories and timestamps. Avoid including third-party private source text simply because a preference references it.

## Shared Conversations

The host determines whether a private preference can be used in a group. It separately determines whether its source evidence may be disclosed. A response can adopt a preferred concise style without telling the group what the user said in a private chat.

Cross-device or cross-channel use requires verified identity and an explicit storage or sharing policy. The skill does not link accounts based on similar names.

## Limits of Personalization

Use personalization to improve collaboration. Preserve factual accuracy and the ability to disagree with a claim when evidence warrants it. Do not use the profile to pressure the user, exploit vulnerabilities, create emotional dependence, or hide consequential choices.
