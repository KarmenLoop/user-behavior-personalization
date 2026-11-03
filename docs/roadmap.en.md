# Personalization roadmap — v0.7.0

[English](roadmap.en.md) · [中文](roadmap.zh-CN.md)

This roadmap covers user-behavior-personalization only. Directions 1–3 are implemented with documented local and actual-provider acceptance. Release checks and public delivery are recorded separately. Directions 4–6 remain planned.

| Direction | Status | Scope and evidence boundary |
| --- | --- | --- |
| 1. Real semantic learning loop | Implemented; scoped acceptance recorded | Analyze explicitly selected, authorized excerpts with the configured model. Keep exact source quotes, stage proposals, and require user review. Offline literal learning remains available. A completed call does not prove the interpretation correct. |
| 2. Conditional preferences | Implemented; scoped acceptance recorded | Apply confirmed preferences by task type, audience, and stage. Preserve conditions on correction, explain exclusions, and abstain on equally specific conflicts. Missing task conditions do not match conditional rules. |
| 3. Actual model-answer comparisons | Implemented; scoped acceptance recorded | Generate two actual answers using the same model and judgment policy. Randomize A/B identities, support tie and neither, and keep preference votes separate from user-reported correctness. Reveal and deletion are explicit controls. |
| 4. Persistent multi-turn anti-sycophancy evaluation | Planned | Evaluate real, sustained conversations against independent evidence. Current judgment instructions and individual comparisons do not establish resistance to sycophancy across turns. |
| 5. Full native host integration | Planned | Validate actual supported Codex and Cursor host sessions end to end. Existing configuration, wrapper, and workspace evidence covers narrower paths. |
| 6. Lower-friction feedback | Planned | Reduce the effort of reviewing and giving feedback while preserving explicit source selection, user control, and a clear distinction between preference and correctness. Current controls do not constitute acceptance of this wider direction. |

A comparison vote records experience. It is not a training reward, a factual verdict, or an automatic instruction to change saved preferences. No roadmap item claims model training, measured quality improvement, or elimination of sycophancy.

Use the [semantic learning walkthrough](semantic-learning.en.md) for the implemented path. Existing [evaluation records](evaluation.md) retain earlier failed diagnostics and narrower acceptance results; new evidence must not overwrite them.
