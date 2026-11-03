#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Evaluate frozen synthetic conversations without training on held-out queries.

This is a small reproducible diagnostic, not a benchmark or evidence of human
benefit. It makes no provider calls and writes no profile. Failed quality cases
remain in the report; --require-all is an optional strict diagnostic gate.
"""
import argparse
from collections import Counter, defaultdict
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

from conversations import normalize_conversation
from forecast import forecast


ROOT = Path(__file__).resolve().parents[1]


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def state_digest(messages, transitions):
    return digest_bytes(json.dumps([messages, transitions], sort_keys=True,
                                  ensure_ascii=True).encode())


def source_pins():
    paths = {Path(module.__file__).resolve() for module in tuple(sys.modules.values())
             if getattr(module, '__file__', None)
             and Path(module.__file__).suffix == '.py'
             and Path(module.__file__).resolve().parent == ROOT / 'scripts'}
    return {path.relative_to(ROOT).as_posix(): {
        'sha256': digest_bytes(path.read_bytes()), 'bytes': path.stat().st_size}
        for path in sorted(paths)}


def load_frozen(directory, manifest_name, holdout_name):
    if any(Path(name).name != name for name in (manifest_name, holdout_name)):
        raise ValueError('Manifest and holdout names must be plain filenames.')
    manifest_raw = (directory / manifest_name).read_bytes()
    manifest = json.loads(manifest_raw)
    result = {}
    for name in ('train.json', holdout_name, 'extraction.json'):
        raw = (directory / name).read_bytes()
        pin = manifest['files'][name]
        if len(raw) != pin['bytes'] or digest_bytes(raw) != pin['sha256']:
            raise ValueError('Frozen fixture differs from its manifest: ' + name)
        result[name] = json.loads(raw)
        if result[name]['fixed_now'] != manifest['fixed_now']:
            raise ValueError('Fixtures must use the same fixed clock.')
    now = dt.datetime.fromisoformat(manifest['fixed_now'])
    if now.tzinfo is None:
        raise ValueError('The fixed clock needs a timezone.')
    return manifest, result, now, digest_bytes(manifest_raw)


def matches(text, patterns):
    folded = text.casefold()
    return any(all(word.casefold() in folded for word in terms)
               for terms in patterns)


def measure(rows):
    emitted = [r for r in rows if r['emitted']]
    expected_positive = [r for r in rows if r['expected'] == 'suggested']
    expected_negative = [r for r in rows if r['expected'] == 'abstain']
    divide = lambda numerator, denominator: round(numerator / denominator, 6) if denominator else None
    return {
        'cases': len(rows),
        'suggestions_emitted': len(emitted),
        'coverage': divide(len(emitted), len(rows)),
        'precision_conditional_on_suggestion': divide(sum(r['correct'] for r in emitted), len(emitted)),
        'top_3_precision_conditional_on_suggestion': divide(sum(r['top_3_match'] for r in emitted), len(emitted)),
        'abstentions': len(rows) - len(emitted),
        'correct_abstentions': sum(r['correct'] for r in expected_negative),
        'abstention_specificity': divide(sum(r['correct'] for r in expected_negative), len(expected_negative)),
        'positive_case_coverage': divide(sum(r['emitted'] for r in expected_positive), len(expected_positive)),
        'correct_cases_including_abstentions': sum(r['correct'] for r in rows),
        'failed_case_ids': [r['id'] for r in rows if not r['correct']],
    }


def score_forecast(case, result):
    status = result.get('status')
    if status not in ('suggested', 'insufficient_evidence', 'conflicted'):
        raise ValueError('Unexpected forecast status: ' + str(status))
    candidates = result.get('candidates', [])
    emitted = status == 'suggested'
    if emitted and not candidates:
        raise ValueError('A suggested forecast has no candidates.')
    texts = [str(c.get('suggestion', '')) for c in candidates[:3]]
    match = case['expected'] == 'suggested' and bool(texts) and matches(texts[0], case['match_any'])
    top_3 = case['expected'] == 'suggested' and any(matches(t, case['match_any']) for t in texts)
    correct = match if emitted else case['expected'] == 'abstain'
    return {
        'id': case['id'], 'expected': case['expected'], 'expected_group': case.get('expected_group'),
        'context': case['context'], 'request': case['request'], 'status': status,
        'emitted': emitted, 'correct': bool(correct), 'top_3_match': bool(emitted and top_3),
        'reason': case.get('reason'), 'candidates': candidates,
    }


def evaluate_forecasts(training, heldout, now):
    messages, transitions = {}, []
    baseline_counts = defaultdict(Counter)
    baseline_text = {}
    for example in training['examples']:
        # Only the conversation is passed to the learner. Evaluation group labels
        # are used by the explicitly label-assisted frequency baseline below.
        normalized = normalize_conversation(example['conversation'], now=now)
        for message in normalized['messages']:
            if message['key'] in messages:
                raise ValueError('Training contains a duplicate message key.')
            messages[message['key']] = message
        transitions.extend(normalized['transitions'])
        context, group = example['conversation']['context'], example['followup_group']
        baseline_counts[context][group] += 1
        baseline_text.setdefault((context, group), example['conversation']['messages'][-1]['text'])
    frozen_state = state_digest(messages, transitions)
    rows, baseline_rows = [], []
    for case in heldout['cases']:
        cold = case.get('training_filter') == 'none'
        training_messages, training_edges = ({}, []) if cold else (messages, transitions)
        # Expected groups and matching rules are deliberately absent here.
        prediction = forecast(training_messages, training_edges, case['context'],
                              case['request'], now=now)
        if state_digest(messages, transitions) != frozen_state:
            raise ValueError('Forecast changed the frozen training state.')
        rows.append(score_forecast(case, prediction))
        counts = {} if cold else baseline_counts.get(case['context'], {})
        if counts:
            group = sorted(counts, key=lambda item: (-counts[item], item))[0]
            baseline = {'status': 'suggested', 'candidates': [{
                'suggestion': baseline_text[(case['context'], group)],
                'group': group, 'supporting_sessions': counts[group]}]}
        else:
            baseline = {'status': 'insufficient_evidence', 'candidates': []}
        baseline_rows.append(score_forecast(case, baseline))
    return {
        'training_conversations': len(training['examples']), 'training_messages': len(messages),
        'training_transitions': len(transitions), 'training_state_sha256': frozen_state,
        'training_state_unchanged': True, 'metrics': measure(rows), 'cases': rows,
        'baseline': {
            'method': 'Most frequent annotated follow-up group within the current context; lexical tie break; no query similarity. Labels are training-only and make this a label-assisted reference baseline.',
            'metrics': measure(baseline_rows), 'cases': baseline_rows,
        },
    }


def evaluate_extraction(fixtures, now):
    rows = []
    tp = fp = fn = bad_evidence = 0
    for case in fixtures['cases']:
        normalized = normalize_conversation(case['conversation'], now=now)
        proposals = normalized['proposals']
        expected = case['expected_proposals']
        unmatched = set(range(len(expected)))
        messages = {m['key']: m for m in normalized['messages']}
        user_texts = [m['text'] for m in case['conversation']['messages'] if m['role'] == 'user']
        found = 0
        invalid = 0
        for proposal in proposals:
            evidence = proposal.get('evidence', [])
            valid_evidence = bool(evidence) and all(
                item.get('source_key') in messages
                and isinstance(item.get('quote'), str) and item['quote'].strip()
                and any(item['quote'] in text for text in user_texts)
                for item in evidence)
            if not valid_evidence:
                invalid += 1
            selected = next((i for i in sorted(unmatched)
                             if matches(proposal.get('statement', ''), expected[i]['match_any'])), None)
            if selected is not None and valid_evidence:
                unmatched.remove(selected)
                found += 1
        case_fp, case_fn = len(proposals) - found, len(unmatched)
        tp += found
        fp += case_fp
        fn += case_fn
        bad_evidence += invalid
        rows.append({'id': case['id'], 'expected_count': case['expected_count'],
                     'actual_count': len(proposals), 'matched_targets': found,
                     'false_positives': case_fp, 'false_negatives': case_fn,
                     'invalid_evidence': invalid, 'correct': case_fp == case_fn == invalid == 0,
                     'proposals': proposals, 'excluded': normalized.get('excluded', [])})
    return {
        'scoring': 'One-to-one matches against prewritten content patterns plus source-quote checks. This checks a narrow extraction task, not general semantic understanding.',
        'cases': rows, 'metrics': {
            'cases': len(rows), 'true_positives': tp, 'false_positives': fp,
            'false_negatives': fn, 'precision': round(tp/(tp+fp), 6) if tp+fp else None,
            'recall': round(tp/(tp+fn), 6) if tp+fn else None,
            'invalid_evidence': bad_evidence,
            'failed_case_ids': [r['id'] for r in rows if not r['correct']],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=ROOT / 'examples/evaluation')
    parser.add_argument('--manifest', default='manifest.json', help='Frozen manifest filename, for example manifest-v2.json.')
    parser.add_argument('--holdout', default='heldout.json', help='Held-out query filename pinned by the selected manifest.')
    parser.add_argument('--output', type=Path, help='Write an external JSON report; existing files are never overwritten.')
    parser.add_argument('--require-all', action='store_true', help='Exit 1 when any held-out quality case fails, while preserving the report.')
    args = parser.parse_args()
    try:
        code_before = source_pins()
        manifest, fixtures, now, manifest_sha = load_frozen(args.fixtures, args.manifest, args.holdout)
        report = {
            'schema_version': 1, 'synthetic_only': True, 'provider_calls': 0,
            'fixed_now': manifest['fixed_now'], 'fixture_pins': manifest['files'],
            'manifest': {'name': args.manifest, 'sha256': manifest_sha},
            'holdout': {'name': args.holdout, 'role': manifest.get('holdout_roles', {}).get(args.holdout, 'initial_independent_holdout')},
            'source_pins': code_before,
            'limitations': [
                'Small independently authored synthetic set; not a public benchmark or evidence of human benefit.',
                'Lexical retrieval is not general semantic understanding, personality analysis, or thought prediction.',
                'Held-out requests and labels do not train the algorithm or its vocabulary; failed cases are retained.',
                'Quality failures do not make an evaluation run incomplete. Use --require-all for a strict optional gate.',
            ],
            'forecast': evaluate_forecasts(fixtures['train.json'], fixtures[args.holdout], now),
            'extraction': evaluate_extraction(fixtures['extraction.json'], now),
        }
        if source_pins() != code_before:
            raise ValueError('An imported source file changed during evaluation; no stable-code report can be issued.')
        report['source_unchanged_during_evaluation'] = True
        failed = report['forecast']['metrics']['failed_case_ids'] + report['extraction']['metrics']['failed_case_ids']
        report['all_quality_cases_passed'] = not failed
        report['evaluation_completed'] = True
        if args.output:
            output = args.output.expanduser().resolve()
            if output == ROOT or ROOT in output.parents:
                raise ValueError('Keep mutable evaluation reports outside the public package.')
            with output.open('x', encoding='utf-8') as stream:
                json.dump(report, stream, ensure_ascii=False, indent=2)
                stream.write('\n')
            print(json.dumps({'report': str(output), 'forecast': report['forecast']['metrics'],
                              'baseline': report['forecast']['baseline']['metrics'],
                              'extraction': report['extraction']['metrics'],
                              'all_quality_cases_passed': not failed}, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 1 if args.require_all and failed else 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({'evaluation_completed': False, 'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
