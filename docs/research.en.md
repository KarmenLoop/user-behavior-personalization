# Research and design choices — v0.4.0

[English](research.en.md) · [中文](research.zh-CN.md)

These sources informed the design. The implementation, thresholds, diagrams, and examples in this repository were developed independently. We do not bundle another project's memory engine, model weights, or benchmark results. A design reference is not an endorsement or evidence that this product has achieved the same results.

## What we took from agent tools and memory projects

| Primary source | Relevant idea | Our design choice |
|---|---|---|
| [Codex: AGENTS.md](https://developers.openai.com/codex/guides/agents-md) | Persistent instructions have discovery and scope rules. | Make context selection explicit; do not assume a running chat reloads a changed profile. |
| [Cursor: rules](https://cursor.com/docs/rules) | Project instructions have documented file formats and inclusion behavior. | Keep host configuration separate from stored user preferences; test actual loading. |
| [DeepSeek: JSON Output](https://api-docs.deepseek.com/guides/json_mode/) | Structured output controls formatting, with edge cases still requiring handling. | Validate typed fields and evidence sources independently; an API response cannot confirm a preference on the user's behalf. |
| [Mem0](https://github.com/mem0ai/mem0) | User-specific memory operations and retrieval. | Bind the subject outside tool arguments and store compact, inspectable preferences. We do not reuse its implementation or performance claims. |
| [LangMem conceptual guide](https://langchain-ai.github.io/langmem/concepts/conceptual_guide/) and [repository](https://github.com/langchain-ai/langmem) | Distinguish profile, episodic, and procedural information. | Keep explicit rules, behavioral observations, and suggestions separate instead of accumulating one undifferentiated summary. |
| [Letta repository](https://github.com/letta-ai/letta) | Explicit management of persisted agent state. | Load a small relevant set of confirmed rules; leave source inspection to a separate operation. |
| [DeepSeek-R1](https://github.com/deepseek-ai/DeepSeek-R1) | Model training is a different mechanism from application memory. | Updating this profile changes local state and instructions; it does not train a model or reproduce R1. |

The choices in the right column are our engineering interpretation. The package does not depend on those projects at runtime.

## Learning science, carefully applied

“Feynman-style learning” is a practical shorthand here: explain a concept in your own words, find a specific gap, work through an example, then try again. It is not a named psychological diagnosis or a way to identify a fixed type of learner.

| Research | What the source supports | What we can reasonably build |
|---|---|---|
| [Chi et al., 1989: Self-explanations](https://doi.org/10.1207/s15516709cog1302_1) | Research on learners generating explanations while studying examples. | Offer an explain-back prompt and identify a concrete missing step in the answer, with the user's permission. |
| [Roediger & Karpicke, 2006: Test-enhanced learning](https://pubmed.ncbi.nlm.nih.gov/16507066/) | Retrieval practice was studied as a contributor to later retention. | Offer optional recall questions and track actual task feedback; do not equate a quiz with intelligence or a product efficacy trial. |
| [Deci & Ryan, 2000: Self-determination theory](https://selfdeterminationtheory.org/SDT/documents/2000_DeciRyan_PIWhatWhy.pdf) | A framework involving autonomy, competence, and relatedness. | Let the user choose, skip, or change a learning mode. Do not optimize for dependence or pressure. |
| [Microsoft HAX: Adapt cautiously](https://www.microsoft.com/en-us/haxtoolkit/guideline/update-and-adapt-cautiously/) and [explain behavior](https://www.microsoft.com/en-us/haxtoolkit/guideline/make-clear-why-the-system-did-what-it-did/) | Human-AI interaction guidance favors careful adaptation and understandable behavior. | Show scope, counterevidence, and uncertainty; require review before adopting inferred preferences. |

These studies and guidelines do not validate this package's effectiveness. No clinical, educational-outcome, or user-satisfaction study is claimed for v0.4.0.

## A useful teaching interaction

1. The user chooses a topic and asks to try explaining it back.
2. The host offers one short explanation and a concrete example.
3. The user explains the idea in their own words, if they want to.
4. The host points out a specific gap, without scoring personality or intelligence.
5. The user decides whether an example or a practice question would help.
6. If the user explicitly praises that format and permits memory, record a scoped `teaching` observation. Repeated performance alone does not prove a permanent preference.

The runtime stores the selected teaching mode and evidence. It does not generate lessons by itself; the connected host/model supplies the actual teaching response. Learning goals, accessibility needs, factual accuracy, and current instructions take precedence over a saved style preference.

## What the support score means

The 3-session threshold, 30-day half-life, 90-day window, and 75% weighted-support threshold are chosen engineering heuristics. They are not parameters derived from the studies above. They prevent a single repeated event from automatically becoming a default, but they do not establish statistical independence or calibrated confidence.

A next-step suggestion asks whether a known workflow pattern is useful in the current context. It does not predict private thoughts. The system should abstain when evidence is weak or contradictory, and it must not execute an action simply because the profile suggests it.

## How to evaluate improvement

Measure observable outcomes: fewer repeated style corrections, fewer irrelevant rules loaded, fewer stale candidates accepted, successful corrections and deletion, and the user's own assessment of usefulness. Compare like-for-like tasks and retain negative results. Do not report invented “understanding,” personality, emotional-state, or thought-prediction scores.

## Conversation retrieval and honest comparison

[LaMP (Salemi et al., ACL 2024)](https://aclanthology.org/2024.acl-long.399/) studies personalized language tasks with user-specific information and retrieval augmentation, including term-, semantic-, and time-aware approaches. Our interpretation is to select a small relevant context with inspectable sources. We have not run the LaMP benchmark or reproduced its results.

[Ludewig and Jannach's session-based recommendation comparison](https://arxiv.org/abs/1803.09587) compares methods, including simpler nearest-neighbor approaches, on session recommendation tasks. It motivates testing a transparent historical-case baseline before assuming a more complex method is better. It does not validate this repository's request forecaster.

The v0.4.0 forecaster is an independent lexical case-retrieval implementation. A new holdout exposed poor paraphrase coverage, especially English (0/6 positive cases suggested). See [evaluation](evaluation.md) for initial failures, development comparisons, and the separate new holdout. The next development step needs broader independent data and improved retrieval, not a claim of reading the user's mind.
