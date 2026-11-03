# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Explicit user feedback bound to prepared plans and exact preference versions."""
from host_support import need, stamp
from learning import check_source, context_key, fingerprint, tombstone


def prepare(profile, plan):
    need(not profile['paused'], 'MEMORY_PAUSED', 'Resume personalization before preparing a saved plan.')
    plans = profile.setdefault('prepared_plans', {})
    if plan['plan_id'] in plans:
        return {'replayed': True, 'prepared': True, 'plan': plan}
    need(len(plans) < 100, 'PLAN_LIMIT', 'Forget old plans before saving more than 100.')
    plans[plan['plan_id']] = {'plan_id': plan['plan_id'], 'context': plan['context'],
        'task_sha256': plan['task_sha256'], 'profile_revision': plan['revision'],
        'rule_versions': {r['id']: r['version_fingerprint'] for r in plan['selected']},
        'judgment_policy': {key: plan['judgment_policy'][key] for key in ('version', 'fingerprint')},
        'created_at': stamp(), 'state': 'prepared'}
    return {'replayed': False, 'prepared': True, 'plan': plan}


def record_outcome(profile, values):
    plan = profile.setdefault('prepared_plans', {}).get(values['plan_id'])
    need(plan is not None, 'PLAN_MISSING', 'Prepare a real plan before rating it.')
    payload = {k: values[k] for k in ('plan_id', 'rating', 'basis', 'source_id')}
    source, hashed, replayed = check_source(profile, values['source_id'], payload)
    if replayed:
        return {'replayed': True, 'outcome': profile['plan_outcomes'].get(values['plan_id'])}
    need(values['rating'] in ('helpful', 'unhelpful', 'mixed', 'not_sure'), 'INVALID_RATING', 'Choose a documented rating.')
    need(values['basis'] in ('prompt_review', 'response_use'), 'INVALID_BASIS', 'Distinguish a prompt review from reported response use.')
    previous = profile.setdefault('plan_outcomes', {}).get(values['plan_id'])
    sources = list(previous.get('source_hashes', [])) if previous else []
    need(len(sources) < 100, 'OUTCOME_LIMIT', 'Forget this plan before recording more than 100 feedback revisions.')
    sources.append(source)
    outcome = {'plan_id': values['plan_id'], 'rating': values['rating'], 'basis': values['basis'],
               'recorded_at': stamp(), 'source_hashes': sources,
               'evidence_kind': 'explicit_user_report_not_independent_model_verification',
               'learning_use': 'experience_report_only_not_truth_or_reward'}
    profile['source_hashes'][source] = hashed
    profile['plan_outcomes'][values['plan_id']] = outcome
    return {'replayed': False, 'outcome': outcome}


def forget_plans(profile, plan_ids):
    from comparisons import forget_comparisons
    plan_ids = set(plan_ids)
    forget_comparisons(profile,[cid for cid,row in profile.get('response_comparisons',{}).items() if row['plan_id'] in plan_ids])
    plans, ratings = profile.setdefault('prepared_plans', {}), profile.setdefault('plan_outcomes', {})
    for pid in plan_ids:
        plans.pop(pid, None)
        rating = ratings.pop(pid, None)
        for source in rating.get('source_hashes', []) if rating else []:
            tombstone(profile, source)


def outcome_summary(profile, context):
    key = context_key(context)
    empty_counts = lambda: {rating: 0 for rating in ('helpful', 'unhelpful', 'mixed', 'not_sure')}
    result = {'context': key, 'revision': profile['revision'], 'paused': profile['paused'],
              'plans': [], 'rule_versions': [], 'counts': empty_counts(),
              'by_basis': {'prompt_review': empty_counts(), 'response_use': empty_counts()},
              'learning_use': 'experience_report_only_not_truth_or_reward',
              'notes': ['Ratings are explicit user reports, not a controlled study or an automatic quality score.',
                        'Prepared does not mean a model ran. A new rule version does not inherit earlier ratings.']}
    if profile['paused']:
        return result
    versions = {}
    for pid, plan in profile.get('prepared_plans', {}).items():
        if plan['context'] != key:
            continue
        outcome = profile.get('plan_outcomes', {}).get(pid)
        public_outcome = {k: outcome[k] for k in ('rating', 'basis', 'recorded_at', 'evidence_kind')} if outcome else None
        result['plans'].append({**plan, 'outcome': public_outcome})
        if outcome:
            result['counts'][outcome['rating']] += 1
            result['by_basis'][outcome['basis']][outcome['rating']] += 1
        for rid, version in plan['rule_versions'].items():
            row = versions.setdefault((rid, version), {'rule_id': rid, 'version_fingerprint': version,
                'current_version': rid in profile['rules'] and fingerprint(profile['rules'][rid]) == version,
                'prepared_count': 0, 'rated_count': 0, 'counts': empty_counts()})
            row['prepared_count'] += 1
            if outcome:
                row['rated_count'] += 1
                row['counts'][outcome['rating']] += 1
    result['rule_versions'] = list(versions.values())
    result['plans'].sort(key=lambda row: row['created_at'], reverse=True)
    return result
