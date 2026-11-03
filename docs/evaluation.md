# Evaluation — v0.5.0

[English](evaluation.md) · [中文](evaluation.zh-CN.md)

Conversation import, review, persistence, and deletion are executable local capabilities. The next-request forecaster is an **experimental lexical retrieval method** with limited coverage. Correct storage and passing unit tests do not establish that a system understands a person.

## v0.5.0: working tools and experimental recognition

The local workspace, selected-file importer, and task preference resolver are executable features. Automatic recognition of recurring feedback remains **experimental**: it can handle supported wording but misses many ordinary paraphrases. Recognition quality, prompt construction, user-reported usefulness, and actual provider responses need separate evidence.

### Known examples versus unseen wording

Only a correct `ready_to_review` candidate counts as positive coverage. A safe abstention still misses a positive case. The strict check also rejects incorrect extra offers; recognizing one expected preference does not excuse an unrelated suggestion.

| Stage | Positive cases covered | Negative cases with a false offer | What the result establishes |
|---|---:|---:|---|
| Initial detector, original set | 0/6 | 0/12 | Preserved initial failure. The simple workspace demo did not expose these gaps. |
| Earlier revision, original set | 1/6 | 0/12 | A development comparison on already-known cases. |
| First unseen `fresh-v2` run | 0/8 | 0/14 | Preserved failure on new wording. A later frozen revision reached 1/8 on this then-known set. |
| First unseen `fresh-v3` run | 1/8 | 0/8 | Preserved independent result from an earlier frozen learner. |
| Current learner, exposed `initial` + `fresh-v2` + `fresh-v3` | 22/22 | 0/34 | **Known-case regression**, after those fixtures were exposed during development. This is not unseen accuracy. |
| Current learner, first unseen `fresh-v4` run | **1/8 (12.5%)** | **0/8** | **English 1/4; Chinese 0/4. Strict quality gate failed.** Seven positive cases were missed. |

The sole emitted `fresh-v4` candidate was correct. A denominator of one does not establish broad accuracy, and the absence of false offers does not make the missing preferences useful. This set has no separately labeled conflict control, so it provides no conflict-abstention estimate. The public runner reproduced the same result and failed case IDs on the frozen learner; that repeat is a reproduction, not another independent first evaluation.

The [v0.5.0 result record](evaluation-results-v0.5.0.json) preserves source/fixture hashes, earlier failures, development comparisons, the first unseen result, and its reproduction. All cases are synthetic. No real-user benefit study or unrestricted semantic-understanding claim follows from these results.

### Reproduce the current habit diagnostic

```sh
python3 -B scripts/evaluate_behavior.py --suite fresh-v4 --require-all
```

For this release, **exit 1 is expected** because seven positive cases are missed. Exit 0 without `--require-all` only means the diagnostic completed. Exit 2 indicates an evaluation or source-integrity problem. Use `--output /path/outside/package/new-report.json` to save a new report; an existing file is never overwritten.

`--suite initial`, `--suite fresh-v2`, and `--suite fresh-v3` now run exposed regression data. `--suite all` includes both the known cases and the independent-origin set; do not combine them into one generalization score. The runner verifies frozen fixture hashes and fixes only the clock. Imports, persisted state, collection opt-in, and habit discovery use the real local host. It does not recreate earlier source versions when run against current code.

### Local transport and provider acceptance

Independent actual MCP stdio acceptance listed all **25 tools** and passed **15 checks**. Both language versions of the selected-feed Python walkthrough ran successfully through separate importer processes and a persisted restart cursor. These checks establish their local behavior, not recognition coverage or the quality of a generated answer.

The v0.5.0 Codex preflight timed out after **80 seconds (exit 124)** with three extra MCP services disabled. It did not produce an accepted model answer. Browser prompt previews are not an actual before/after response comparison. No live DeepSeek provider call is claimed.

For local acceptance, follow the [workspace tutorial](tutorial.en.md) and [restartable feed example](automatic-learning.en.md). Check source quotes, review, temporary overrides without profile mutation, corrections, explicit rating basis, and deletion of dependent records. A saved plan does not certify provider execution; an explicit rating does not constitute a controlled effectiveness study.

## Retained v0.4.0 quality results

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

The [conversation guide](conversation-guide.en.md) contains a second executable walkthrough. The earlier structured-feedback demo remains available as `scripts/demo_learning.py`.

## Reproduce the retained conversation diagnostic

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

Use synthetic data in public receipts. Full privacy detection, arbitrary semantic conflict resolution, arbitrary account-history ingestion, and cross-device synchronization are not established by these checks.

## Host/provider evidence retained from earlier work

The preceding v0.3.0 work on 2026-11-03 exercised actual MCP pipes and generated Codex/Cursor configurations. A Codex model attempt loaded the rule, then timed out at 55 seconds (exit 124; owned child reaped). Cursor loaded the rule but required authentication (exit 1). Neither produced an accepted model response. These are historical attempts, **not v0.4.0 or v0.5.0 model acceptance**.

No live DeepSeek API call or native desktop GUI acceptance is claimed. Building model context, generating configuration, and validating MCP calls are useful local checks; they do not certify model behavior or user benefit.

## What to improve next

Improve paraphrase coverage with new independent evaluation data, particularly English. Keep difficult negative cases and context changes. Evaluate retrieval changes against a simple baseline and report both what is suggested and what is missed. For actual usefulness, compare similar tasks with and without a confirmed preference and ask the user whether the change helped; do not invent approval from silence.
