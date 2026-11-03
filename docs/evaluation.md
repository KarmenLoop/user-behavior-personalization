# Evaluation — v0.4.0

[English](evaluation.md) · [中文](evaluation.zh-CN.md)

Conversation import, review, persistence, and deletion are executable local capabilities. The next-request forecaster is an **experimental lexical retrieval method** with limited coverage. Correct storage and passing unit tests do not establish that a system understands a person.

## Quality results, including the misses

| Evaluation stage | Result | Interpretation |
|---|---|---|
| Initial 11-query forecast diagnostic | Abstained on all 11; missed all 6 expected positive suggestions; 5 negative cases correctly abstained | The initial implementation did not cover the intended positive examples. This failed result is retained. |
| Original set after a generic development change | 6 correct suggestions and 5 correct abstentions | A development comparison on the original set, not fresh independent evidence of generalization. |
| New, previously unseen 18-query holdout | 4 correct suggestions from 12 positive cases; 8 positive cases abstained; all 6 negative cases correctly abstained | Positive coverage **33.3%**. English positive coverage **0/6**; Chinese **4/6**. |
| Explicit-cue extraction, 20 cases | 7 true positives, 0 false positives, 1 false negative | Recall **7/8 = 87.5%** on this small set of positive cases. One supported formulation was missed. |

The 4 emitted suggestions on the new set were correct within that set. **4/4 is not evidence of 100% general accuracy**: the method declined most positive cases. Conditional precision, coverage, and abstention must be reported together. No user-satisfaction, psychological, or educational-outcome study was conducted.

The comparison baseline chooses the most frequent annotated follow-up group in the current context. On the new set, it suggested 16 times: 12 correct suggestions and 4 false positives. Including abstentions, it got 14/18 cases right versus 10/18 for the forecaster. The forecaster avoided those false positives but missed more valid suggestions. This label-assisted baseline is a reference point, and these results do not establish overall superiority for our method.

The implementation was improved using separate development examples, not the new held-out queries. Frozen fixture manifests bind the datasets and fixed clock. The original failure, the development comparison, and the new holdout are distinct records. See the [sanitized result summary](evaluation-results-v0.4.0.json).

## Reproduce local behavior

From the package directory, using Python 3.11+:

```sh
python3 -B scripts/check_package.py
python3 -B -m unittest discover -s tests -v
python3 -B scripts/check_publication.py
python3 -B scripts/demo_conversations.py --root ../new-conversation-acceptance
```

The demo uses actual local CLI processes and SQLite writes with synthetic text: import, open-text proposal, portrait, review, restart/recall, a two-session forecast, model-proposal staging, deletion, abstention after evidence removal, replay blocking, and reset. It does not call a provider. Choose a new private directory.

The [tutorial](tutorial.en.md) contains a second executable walkthrough. The earlier structured-feedback demo remains available as `scripts/demo_learning.py`.

## Reproduce the quality diagnostic

```sh
python3 -B scripts/evaluate_conversations.py
python3 -B scripts/evaluate_conversations.py \
  --holdout heldout-v2.json --manifest manifest-v2.json
```

The default fixture directory is `examples/evaluation`; `--holdout` and `--manifest` are filenames within it. Use `--output /path/outside/package/report.json` to preserve a new report without overwriting an existing one. The report records fixture/source hashes, coverage, conditional precision, abstentions, extraction misses, and failed case IDs.

Normal exit 0 means the evaluation completed, **not that every quality case passed**. Add `--require-all` for a strict gate; the retained misses cause exit 1. Do not change expected labels, weaken the checks, or discard failed cases to make that gate green.

## Behavioral acceptance

| Path | Observable evidence |
|---|---|
| Import | Correct subject/context; only retained user evidence; duplicate input adds no support; changed/reordered history is rejected |
| Extraction | Original statement, source key and quote; quoted/code/temporary content excluded as tested; pending until review |
| Portrait | Writing features and source examples describe imported messages; confirmed preferences remain distinct |
| Proposal review | Current revision, actual decision, persisted rule; correction explicitly identifies a replaced rule |
| Model bridge | Known retained source and exact quote required; invalid/mismatched evidence rejected; valid proposals remain pending |
| Forecast | Only original transitions; per-session contribution limit; inspectable examples; weak/conflicting evidence abstains |
| Deletion | Dependent proposals/rules/features/edges removed; no synthetic A→C edge after deleting B; old sources cannot replay |
| Pause/reset | Ordinary use stops; export and deletion remain possible; reset ends paused |
| Host response | A real answer applies a confirmed preference and changes after correction; evaluate separately from transport |

Use synthetic data in public receipts. Full privacy detection, arbitrary semantic conflict resolution, background ingestion, and cross-device synchronization are not established by these checks.

## Host/provider evidence retained from earlier work

The preceding v0.3.0 work on 2026-11-03 exercised actual MCP pipes and generated Codex/Cursor configurations. A Codex model attempt loaded the rule, then timed out at 55 seconds (exit 124; owned child reaped). Cursor loaded the rule but required authentication (exit 1). Neither produced an accepted model response. These are historical attempts, **not new v0.4.0 model tests**.

No live DeepSeek API call or native desktop GUI acceptance is claimed. Building model context, generating configuration, and validating MCP calls are useful local checks; they do not certify model behavior or user benefit.

## What to improve next

Improve paraphrase coverage with new independent evaluation data, particularly English. Keep difficult negative cases and context changes. Evaluate retrieval changes against a simple baseline and report both what is suggested and what is missed. For actual usefulness, compare similar tasks with and without a confirmed preference and ask the user whether the change helped; do not invent approval from silence.
