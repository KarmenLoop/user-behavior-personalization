# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Deterministic, reviewable evidence aggregation; never a personality model."""
import datetime as dt
import hashlib
import json

from host_support import need, identifier, content

UTC = dt.timezone.utc
DIMENSIONS = {
    'response_length': ('concise', 'balanced', 'detailed'),
    'structure': ('conclusion_first', 'steps', 'examples', 'code_first', 'bullets'),
    'teaching': ('explain_back', 'worked_example', 'practice'),
    'initiative': ('ask_first', 'suggest_next'),
    'workflow_next_step': ('clarify', 'plan', 'implement', 'test', 'review', 'summarize'),
    'language': ('en', 'zh'),
}
STATEMENTS = {
    'response_length': {'concise': 'Keep responses concise.', 'balanced': 'Give a short answer with the details needed to use it.', 'detailed': 'Include detailed reasoning, examples, and verification where useful.'},
    'structure': {'conclusion_first': 'Start with the conclusion, then explain.', 'steps': 'Organize instructions into clear sequential steps.', 'examples': 'Include a concrete example when explaining a concept.', 'code_first': 'Show the relevant code before explaining it.', 'bullets': 'Use concise bullet points when the content is a list.'},
    'teaching': {'explain_back': 'Offer an optional explain-back exercise to check understanding.', 'worked_example': 'Teach with a worked example before independent practice.', 'practice': 'Offer optional retrieval practice with corrective feedback.'},
    'initiative': {'ask_first': 'Ask before proposing a change in task direction; preserve existing permissions.', 'suggest_next': 'Offer a useful next step as a suggestion; do not execute it without authorization.'},
    'workflow_next_step': {value: 'In this task context, suggest the next step "' + value + '"; do not execute it automatically.' for value in DIMENSIONS['workflow_next_step']},
    'language': {'en': 'Respond in English unless the current request asks otherwise.', 'zh': 'Respond in Simplified Chinese unless the current request asks otherwise.'},
}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def fingerprint(value):
    return digest(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')))


def now_utc():
    return dt.datetime.now(UTC)


def timestamp(value, code='INVALID_TIMESTAMP'):
    try:
        date = dt.datetime.fromisoformat(value.replace('Z', '+00:00'))
        need(date.tzinfo is not None and date.utcoffset() is not None, code, 'Use an ISO timestamp with a timezone.')
        return date.astimezone(UTC)
    except (ValueError, TypeError, AttributeError, OverflowError):
        need(False, code, 'Use an ISO timestamp with a timezone.')


def context_key(value):
    return content(value, 'context', 200).casefold()


def typed_value(dimension, value):
    need(dimension in DIMENSIONS, 'INVALID_DIMENSION', 'Choose a documented collaboration dimension.')
    need(value in DIMENSIONS[dimension], 'INVALID_VALUE', 'Choose a documented value for this dimension.')


def normalize_event(event, now=None):
    now = now or now_utc()
    identifier(event['id'])
    content(event['source_id'], 'source_id', 200)
    content(event['session_id'], 'session_id', 200)
    key = context_key(event['context'])
    need(key != '*', 'INVALID_CONTEXT', 'Observations need a specific task context, not a global wildcard.')
    typed_value(event['dimension'], event['value'])
    when = timestamp(event['occurred_at'])
    need(when <= now + dt.timedelta(minutes=5), 'FUTURE_OBSERVATION', 'Observation time is more than five minutes in the future.')
    return {**event, 'context': key, 'occurred_at': when.isoformat()}


def active(rule, now=None):
    return not rule.get('expires_at') or timestamp(rule['expires_at'], 'INVALID_EXPIRY') > (now or now_utc())


def matching_rules(profile, context, now=None):
    """Exact context matching. A typed contextual rule overrides its global peer."""
    key = context_key(context)
    rules = [r for r in profile['rules'].values() if active(r, now) and (r['scope'] == '*' or context_key(r['scope']) == key)]
    specific = {r['dimension'] for r in rules if r.get('dimension') and r['scope'] != '*'}
    return sorted((r for r in rules if not (r['scope'] == '*' and r.get('dimension') in specific)), key=lambda r: (r['scope'] == '*', r['id']))


def insights(profile, context, now=None):
    now = now or now_utc()
    key = context_key(context)
    result = {'subject_id': profile['subject_id'], 'revision': profile['revision'], 'paused': profile['paused'], 'context': key, 'confidence_kind': 'heuristic_not_probability', 'candidates': []}
    if profile['paused']:
        return result
    # Repeating feedback within one session cannot manufacture independent support.
    latest = {}
    for event in profile['observations'].values():
        when = timestamp(event['occurred_at'])
        if event['context'] != key or now - when > dt.timedelta(days=90) or when > now + dt.timedelta(minutes=5):
            continue
        slot = (event['session_id'], event['dimension'])
        prior = latest.get(slot)
        if prior is None or (when, event['id']) > (timestamp(prior['occurred_at']), prior['id']):
            latest[slot] = event
    explicit = {r['dimension']: r for r in matching_rules(profile, context, now) if r.get('dimension')}
    for dimension in DIMENSIONS:
        events = sorted((e for e in latest.values() if e['dimension'] == dimension), key=lambda e: e['id'])
        values = sorted({e['value'] for e in events if e['signal'] == 'positive'})
        for value in values:
            support = [e for e in events if e['value'] == value and e['signal'] == 'positive']
            oppose = [e for e in events if (e['value'] == value and e['signal'] == 'negative') or (e['value'] != value and e['signal'] == 'positive')]
            weight = lambda e: 0.5 ** (max(0, (now - timestamp(e['occurred_at'])).total_seconds()) / (30 * 86400))
            yes, no = sum(map(weight, support)), sum(map(weight, oppose))
            score = yes / (yes + no) if yes + no else 0.0
            recent = any(now - timestamp(e['occurred_at']) <= dt.timedelta(days=30) for e in support)
            candidate_id = 'candidate-' + fingerprint({'context': key, 'dimension': dimension, 'value': value, 'events': events, 'confirmed': explicit.get(dimension)})[:32]
            if candidate_id in profile['dismissed_candidates']:
                continue
            reasons = ['One latest signal per session and dimension.', 'Evidence has a 30-day half-life and a 90-day window.', 'The support score is a review heuristic, not a probability or psychological assessment.']
            if dimension in explicit:
                status = 'confirmed_preference_exists'
                reasons.append('An applicable confirmed preference already owns this dimension. Correct it explicitly to change it.')
            elif len(support) < 3 or not recent:
                status = 'insufficient_evidence'
                reasons.append('Review needs at least three supporting sessions and support within the last 30 days.')
            elif score < 0.75:
                status = 'conflicted'
                reasons.append('Recent disagreement leaves weighted support below 0.75.')
            else:
                status = 'ready_to_review'
                reasons.append('Ask the user to confirm this scoped preference before saving an active rule.')
            result['candidates'].append({'candidate_id': candidate_id, 'context': key, 'dimension': dimension, 'value': value, 'status': status, 'supporting_sessions': len(support), 'opposing_sessions': len(oppose), 'weighted_support': round(yes, 6), 'weighted_opposition': round(no, 6), 'score': round(score, 6), 'source_event_ids': [e['id'] for e in events], 'last_observed_at': max(e['occurred_at'] for e in events), 'reasons': reasons})
    return result


def blank_profile(subject):
    return {'schema_version': 2, 'subject_id': subject, 'revision': 0, 'paused': False, 'rules': {}, 'source_hashes': {}, 'deleted_source_hashes': [], 'history': [], 'observations': {}, 'deleted_observation_hashes': [], 'dismissed_candidates': {}, 'conversation_messages': {}, 'conversation_proposals': {}, 'conversation_transitions': [], 'conversation_sessions': {}, 'dismissed_habits': {}, 'prepared_plans': {}, 'plan_outcomes': {}, 'updated_at': None}


def upgrade(profile):
    """Add fields without rewriting any existing 0.2.0 rule or provenance."""
    for key, value in blank_profile(profile['subject_id']).items():
        profile.setdefault(key, value)
    profile['schema_version'] = 2
    return profile


def check_source(profile, source_id, payload):
    content(source_id, 'source_id', 200)
    source = digest(source_id)
    need(source not in profile['deleted_source_hashes'], 'SOURCE_FORGOTTEN', 'This deleted source cannot recreate a preference.')
    # Preserve the 0.2.0 source fingerprint encoding for backwards-compatible replay.
    value = digest(json.dumps(payload, sort_keys=True))
    if source in profile['source_hashes']:
        need(profile['source_hashes'][source] == value, 'SOURCE_CONFLICT', 'A processed source was changed. Supply a genuinely new source.')
        return source, value, True
    return source, value, False


def tombstone(profile, source):
    profile['source_hashes'].pop(source, None)
    profile['deleted_source_hashes'] = sorted(set(profile['deleted_source_hashes']) | {source})


def purge(profile, rule_ids=(), event_ids=(), conversation_keys=()):
    """Remove the full dependency closure, including superseded derived rules."""
    rules = list(profile['rules'].values()) + [h['rule'] for h in profile['history']]
    rule_ids, event_ids, conversation_keys = set(rule_ids), set(event_ids), set(conversation_keys)
    forgotten_dimensions = set()
    while True:
        before = (len(rule_ids), len(event_ids), len(forgotten_dimensions), len(conversation_keys))
        for rule in rules:
            sources = set(rule.get('evidence_ids', []))
            lineage = set(rule.get('supersedes_rule_ids', []))
            dialogue = set(rule.get('conversation_source_keys', []))
            if rule['id'] in rule_ids or sources & event_ids or lineage & rule_ids or dialogue & conversation_keys:
                rule_ids.add(rule['id'])
                rule_ids.update(lineage)
                event_ids.update(sources)
                conversation_keys.update(dialogue)
                if rule.get('dimension'):
                    forgotten_dimensions.add((context_key(rule['scope']), rule['dimension']))
        # The latest-per-session filter is a scoring rule, not a deletion
        # boundary. Older shadowed signals must not become new evidence after
        # their newer siblings are deleted. The same applies to evidence that
        # existed before an explicit typed correction suppressed a candidate.
        for event_id, event in profile['observations'].items():
            if any(dimension == event['dimension'] and (scope == '*' or scope == event['context'])
                   for scope, dimension in forgotten_dimensions):
                event_ids.add(event_id)
        if forgotten_dimensions:
            from behavior_learning import extract_feedback
            for key, message in profile.get('conversation_messages', {}).items():
                dimensions = {cue['dimension'] for cue in extract_feedback(message['excerpt'])}
                if any(dimension in dimensions and (scope == '*' or scope == message['context'])
                       for scope, dimension in forgotten_dimensions):
                    conversation_keys.add(key)
        for proposal in profile.get('conversation_proposals', {}).values():
            sources = set(proposal['source_keys'])
            if sources & conversation_keys or proposal.get('rule_id') in rule_ids:
                conversation_keys.update(sources)
                if proposal.get('rule_id'):
                    rule_ids.add(proposal['rule_id'])
        if before == (len(rule_ids), len(event_ids), len(forgotten_dimensions), len(conversation_keys)):
            break
    for rule in rules:
        if rule['id'] in rule_ids:
            tombstone(profile, rule['source_hash'])
    for event_id in event_ids:
        event = profile['observations'].pop(event_id, None)
        if event:
            tombstone(profile, event['source_hash'])
            profile['deleted_observation_hashes'] = sorted(set(profile['deleted_observation_hashes']) | {digest(event_id)})
    profile['rules'] = {k: v for k, v in profile['rules'].items() if k not in rule_ids}
    profile['history'] = [h for h in profile['history'] if h['rule']['id'] not in rule_ids]
    for key in conversation_keys:
        message = profile.get('conversation_messages', {}).pop(key, None)
        if message:
            tombstone(profile, message['source_hash'])
    for pid, proposal in list(profile.get('conversation_proposals', {}).items()):
        if set(proposal['source_keys']) & conversation_keys:
            if proposal.get('review_source_hash'):
                tombstone(profile, proposal['review_source_hash'])
            del profile['conversation_proposals'][pid]
    profile['conversation_transitions'] = [edge for edge in profile.get('conversation_transitions', [])
        if edge['from_key'] not in conversation_keys and edge['to_key'] not in conversation_keys]
    for candidate_id, dismissal in list(profile.get('dismissed_habits', {}).items()):
        if set(dismissal.get('source_keys', [])) & conversation_keys:
            tombstone(profile, dismissal['source_hash'])
            del profile['dismissed_habits'][candidate_id]
    from outcomes import forget_plans
    removed_plans = [pid for pid, plan in profile.get('prepared_plans', {}).items()
                     if set(plan['rule_versions']) & rule_ids]
    forget_plans(profile, removed_plans)
    # Content-free dismissals stay intact: forgetting unrelated evidence must not
    # revive a candidate the user already rejected. Reset removes all dismissals.
    return {'removed_rule_ids': sorted(rule_ids), 'removed_observation_ids': sorted(event_ids), 'removed_message_keys': sorted(conversation_keys), 'removed_plan_ids': removed_plans}
