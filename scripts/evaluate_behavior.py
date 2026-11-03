#!/usr/bin/env python3
"""Run frozen synthetic behavior diagnostics through the real local host.

No provider calls. Fixtures and source files are read, never rewritten.
Each case gets a disposable subject/store. Only the clock is fixed, to keep
dated evidence eligible when this diagnostic is rerun months later.
"""
import argparse
from contextlib import ExitStack
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

SUITES = ('initial', 'fresh-v2', 'fresh-v3', 'fresh-v4')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def state_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def ratio(numerator, denominator):
    return {'numerator': numerator, 'denominator': denominator,
            'value': numerator / denominator if denominator else None}


def load_suite(directory):
    manifest = json.loads((directory / 'manifest.json').read_text())
    for name, expected in manifest['files'].items():
        if name not in ('inputs.json', 'expected.json', 'acceptance.json'):
            raise ValueError('Unexpected fixture filename in manifest')
        path = directory / name
        if sha(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            raise ValueError('Frozen fixture hash/size mismatch: ' + name)
    inputs = json.loads((directory / 'inputs.json').read_text())
    targets = json.loads((directory / 'expected.json').read_text())['expectations']
    ids = [case['id'] for case in inputs['cases']]
    oracle = {target['id']: target for target in targets}
    if len(ids) != len(set(ids)) or len(oracle) != len(targets) or set(ids) != set(oracle):
        raise ValueError('Duplicate or mismatched fixture case IDs')
    return manifest, inputs, oracle


def primary_target(case, expected):
    if not expected['expected_recurring_candidates']:
        return None
    if expected.get('primary_typed_target'):
        return tuple(expected['primary_typed_target'])
    # The first frozen suite used prose targets. This mapping was declared in
    # its initial evaluator before outputs were inspected, and is unchanged.
    return {'brief': ('response_length', 'concise'),
            'code': ('structure', 'code_first'),
            'example': ('teaching', 'worked_example')}[case['id'].split('-')[1]]


def fixed_clock(stack, source_directory, moment):
    import learning
    import host_support
    old_now, old_stamp = learning.now_utc, host_support.stamp
    replaced = []
    for name, module in sorted(sys.modules.copy().items()):
        filename = getattr(module, '__file__', None)
        if not filename or Path(filename).resolve().parent != source_directory:
            continue
        if getattr(module, 'now_utc', None) is old_now:
            stack.enter_context(patch.object(module, 'now_utc', lambda: moment))
            replaced.append(name + '.now_utc')
        if getattr(module, 'stamp', None) is old_stamp:
            stack.enter_context(patch.object(module, 'stamp', lambda: moment.isoformat()))
            replaced.append(name + '.stamp')
    return replaced


def run_case(case, expected, dispatch, Problem):
    enabled = case['behavior_learning_enabled']
    receipts = []
    with tempfile.TemporaryDirectory(prefix='karmen-behavior-eval-') as temp:
        args = SimpleNamespace(root=Path(temp) / 'private', subject='evaluation-' + case['id'],
                               enable_conversations=enabled)
        for conversation in case['conversations']:
            current = dispatch('profile_read', {'context': case['target_context']}, args)
            try:
                receipt = dispatch('conversation_import',
                                   {'expected_revision': current['revision'], 'conversation': conversation}, args)
                receipts.append({'status': 'imported', 'session_id': conversation['session_id'],
                                 'receipt': {k: v for k, v in receipt.items() if k != 'profile'},
                                 'revision_after': receipt['profile']['revision'],
                                 'active_rules_after': len(receipt['profile']['rules'])})
            except Problem as error:
                receipts.append({'status': 'rejected', 'session_id': conversation['session_id'], 'code': error.code})
        before = dispatch('profile_export', {}, args)['profile']
        result = dispatch('profile_habits', {'context': case['target_context']}, args)
        after = dispatch('profile_export', {}, args)['profile']
    offers = [c for c in result['candidates'] if c['status'] == 'ready_to_review']
    target = primary_target(case, expected)
    matches = [c for c in offers if (c['dimension'], c['value']) == target]
    # Concise/conclusion-first were both supported by the first suite's prose
    # target. Conclusion-first alone never satisfies primary concise coverage.
    extra = [('structure', 'conclusion_first')] if target == ('response_length', 'concise') and case['id'].startswith('p-') else []
    correct = [c for c in offers if (c['dimension'], c['value']) == target or (c['dimension'], c['value']) in extra]
    import_ok = (all(r['status'] == 'imported' and r['active_rules_after'] == 0 for r in receipts) if enabled
                 else not after['conversation_messages'] and all(r.get('code') == 'CONVERSATIONS_DISABLED' for r in receipts))
    no_mutation = state_hash(before) == state_hash(after)
    no_auto_apply = not after['rules']
    support_ok = all(c['supporting_sessions'] >= 3 for c in offers)
    precision_ok = len(correct) == len(offers)
    passed = (bool(matches) if target else not offers) and precision_ok and import_ok and no_mutation and no_auto_apply and support_ok
    failures = []
    if target and not matches:
        failures.append('Expected recurring preference was not offered for review.')
    if not target and offers:
        failures.append('Negative control produced an offered preference.')
    if not precision_ok:
        failures.append('An incorrect extra preference was offered for review.')
    if not import_ok:
        failures.append('Import authorization or automatic-application boundary failed.')
    if not no_mutation:
        failures.append('Reading habits changed persisted profile state.')
    if not no_auto_apply:
        failures.append('An active preference appeared without review.')
    if not support_ok:
        failures.append('An offer had fewer than three supporting sessions.')
    return {'id': case['id'], 'locale': case['locale'], 'primary_typed_target': target,
            'expected': expected, 'passed': passed, 'failure_reasons': failures,
            'target_offered': bool(matches), 'offered_count': len(offers), 'correct_offered_count': len(correct),
            'retained_user_messages': len(after['conversation_messages']),
            'import_boundary_passed': import_ok, 'discovery_read_only': no_mutation,
            'pending_review_boundary_passed': no_auto_apply, 'independent_session_threshold_passed': support_ok,
            'import_receipts': receipts, 'raw_result': result}


def metrics(results):
    positives = [r for r in results if r['primary_typed_target']]
    negatives = [r for r in results if not r['primary_typed_target']]
    conflicts = [r for r in negatives if r['expected']['conflict_expected']]
    offered = sum(r['offered_count'] for r in results)
    return {'positive_case_coverage': ratio(sum(r['target_offered'] for r in positives), len(positives)),
            'candidate_precision_given_emission': ratio(sum(r['correct_offered_count'] for r in results), offered),
            'negative_control_false_positive_rate': ratio(sum(r['offered_count'] > 0 for r in negatives), len(negatives)),
            'conflict_abstention_rate': ratio(sum(r['offered_count'] == 0 for r in conflicts), len(conflicts)),
            'offered_candidates': offered,
            'all_candidates_including_not_ready': sum(len(r['raw_result']['candidates']) for r in results),
            'cases_passing': ratio(sum(r['passed'] for r in results), len(results)),
            'locale_positive_coverage': {locale: ratio(sum(r['target_offered'] for r in positives if r['locale'] == locale), sum(r['locale'] == locale for r in positives)) for locale in ('en', 'zh')},
            'import_boundary_passed': all(r['import_boundary_passed'] for r in results),
            'pending_review_boundary_passed': all(r['pending_review_boundary_passed'] for r in results),
            'discovery_read_only': all(r['discovery_read_only'] for r in results),
            'independent_session_threshold_passed': all(r['independent_session_threshold_passed'] for r in results)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--suite', choices=(*SUITES, 'all'), default='fresh-v4')
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1], help=argparse.SUPPRESS)
    parser.add_argument('--output', type=Path, help='Write a new report outside the repository; otherwise print JSON.')
    parser.add_argument('--require-all', action='store_true', help='Return exit 1 if any positive is missed or any control fails.')
    parser.add_argument('--expected-learner-sha', help='Optional source pin; reject a different learner revision.')
    args = parser.parse_args()
    if sys.version_info < (3, 11):
        parser.error('Python 3.11 or newer is required.')
    repo = args.repo.resolve()
    output = args.output.expanduser().resolve() if args.output else None
    if output and (output == repo or repo in output.parents):
        parser.error('--output must be outside the repository.')
    if output and output.exists():
        parser.error('--output already exists; reports are never overwritten.')
    scripts = repo / 'scripts'
    source_before = {str(p.relative_to(repo)): sha(p) for p in sorted(scripts.glob('*.py'))}
    if args.expected_learner_sha and source_before['scripts/behavior_learning.py'] != args.expected_learner_sha:
        parser.error('Learner source does not match --expected-learner-sha.')
    sys.path.insert(0, str(scripts))
    import behavior_learning  # Load lazy modules before installing the clock fixture.
    from host import dispatch
    from host_support import Problem
    suites = []
    for name in SUITES if args.suite == 'all' else (args.suite,):
        directory = repo / 'examples' / 'behavior-evaluation' / name
        manifest, inputs, oracle = load_suite(directory)
        moment = dt.datetime.fromisoformat(inputs['evaluation_now'])
        with ExitStack() as stack:
            clock_targets = fixed_clock(stack, scripts, moment)
            results = [run_case(case, oracle[case['id']], dispatch, Problem) for case in inputs['cases']]
        suites.append({'suite': name, 'fixture_manifest_sha256': sha(directory / 'manifest.json'),
                       'fixture_files': manifest['files'], 'evaluation_now': inputs['evaluation_now'],
                       'clock_overrides': clock_targets, 'metrics': metrics(results),
                       'all_quality_cases_passed': all(r['passed'] for r in results),
                       'failed_case_ids': [r['id'] for r in results if not r['passed']], 'cases': results})
    unchanged = source_before == {name: sha(repo / name) for name in source_before}
    report = {'schema_version': 1, 'synthetic_only': True, 'provider_calls': False,
              'evaluated_at': dt.datetime.now(dt.timezone.utc).isoformat(),
              'method': 'Actual host imports and habit discovery in isolated disposable SQLite stores; only UTC clock functions are fixed to each manifest reference date.',
              'limits': ['Not a real-user benefit benchmark or unrestricted semantic-learning test.',
                         'Only ready_to_review candidates count as offers; safe abstention is not positive coverage.',
                         'No model response, watcher, UI, or habit-acceptance flow is exercised by this diagnostic.',
                         'Three session IDs are synthetic host attestations, not proof of three independent people.',
                         'Historical result hashes identify recorded runs; reruns evaluate the checked-out source.'],
              'evaluator_sha256': sha(Path(__file__)), 'source_sha256': source_before,
              'sources_unchanged_during_run': unchanged,
              'all_quality_cases_passed': all(s['all_quality_cases_passed'] for s in suites), 'suites': suites}
    if output:
        with output.open('x', encoding='utf-8') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print(json.dumps({'sources_unchanged': unchanged, 'all_quality_cases_passed': report['all_quality_cases_passed'],
                          'suites': [{k: s[k] for k in ('suite', 'metrics', 'failed_case_ids')} for s in suites]}, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 2 if not unchanged else (1 if args.require_all and not report['all_quality_cases_passed'] else 0)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (ValueError, OSError, KeyError) as error:
        print('Evaluation error: ' + str(error), file=sys.stderr)
        raise SystemExit(2)
