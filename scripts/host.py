#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Subject-bound preference storage and reviewable behavioral evidence."""
import json

from host_support import Database, need, identifier, content, stamp, atomic, schema, string, integer, main, validate
from learning import DIMENSIONS, STATEMENTS, active, blank_profile, check_source, context_key, digest, insights, matching_rules, normalize_event, purge, timestamp, typed_value, upgrade
from conversation_store import import_conversation, review_proposal, portrait, model_context, import_model_proposals
from forecast import forecast

RULE = schema({
    'id': string(80), 'statement': string(1000), 'scope': string(200),
    'source_id': string(200), 'source_summary': string(1000),
    'kind': {'type': 'string', 'enum': ['explicit', 'correction']},
    'expires_at': string(50), 'dimension': {'type': 'string', 'enum': list(DIMENSIONS)}, 'value': string(80),
}, ['id', 'statement', 'scope', 'source_id', 'source_summary', 'kind'])
EVENT = schema({
    'id': string(80), 'source_id': string(200), 'session_id': string(200),
    'context': string(200), 'dimension': {'type': 'string', 'enum': list(DIMENSIONS)},
    'value': string(80), 'signal': {'type': 'string', 'enum': ['positive', 'negative']}, 'occurred_at': string(50),
}, ['id', 'source_id', 'session_id', 'context', 'dimension', 'value', 'signal', 'occurred_at'])
MESSAGE = schema({'id': string(80), 'role': {'type': 'string', 'enum': ['user', 'assistant', 'system', 'tool']},
                  'text': string(4000), 'at': string(50)}, ['id', 'role', 'text', 'at'])
CONVERSATION = schema({'session_id': string(80), 'context': string(200),
    'messages': {'type': 'array', 'items': MESSAGE, 'minItems': 1, 'maxItems': 100}}, ['session_id', 'context', 'messages'])
MODEL_PROPOSAL = schema({'statement': string(500), 'scope': string(200),
    'category': {'type': 'string', 'enum': ['communication', 'workflow', 'goal', 'constraint']},
    'evidence': {'type': 'array', 'minItems': 1, 'maxItems': 3,
        'items': schema({'source_key': string(80), 'quote': string(240)}, ['source_key', 'quote'])}},
    ['statement', 'scope', 'category', 'evidence'])


def tool(name, description, fields, required=(), read_only=False):
    result = {'name': name, 'description': description, 'inputSchema': schema(fields, required)}
    if read_only:
        result['annotations'] = {'readOnlyHint': True}
    return result


TOOLS = [
    tool('profile_read', 'Read active confirmed preferences in the configured subject and exact context. Paused profiles return no rules.', {'context': string(200)}, ['context'], True),
    tool('profile_correct', 'Save an explicit sourced preference; source identifiers are host attestations, not proof of consent.', {'expected_revision': integer(), 'rule': RULE}, ['expected_revision', 'rule']),
    tool('profile_pause', 'Pause or resume ordinary recall, evidence collection, and updates.', {'expected_revision': integer(), 'paused': {'type': 'boolean'}}, ['expected_revision', 'paused']),
    tool('profile_forget', 'Purge a rule, its history and supporting observations; retain only replay suppression hashes.', {'expected_revision': integer(), 'rule_id': string(80)}, ['expected_revision', 'rule_id']),
    tool('profile_export', 'Export private state for the bound subject, including while paused.', {}),
    tool('profile_observe', 'Record an authorized user feedback signal when observation collection is enabled by the host. No raw conversations.', {'expected_revision': integer(), 'event': EVENT}, ['expected_revision', 'event']),
    tool('profile_insights', 'Explain scoped evidence and tentative suggestions. Scores are heuristics, not probabilities or psychological assessments.', {'context': string(200)}, ['context'], True),
    tool('profile_review', 'Record the user acceptance or rejection of a current candidate. The host must obtain the user response first.', {'expected_revision': integer(), 'candidate_id': string(80), 'decision': {'type': 'string', 'enum': ['accept', 'reject']}, 'source_id': string(200)}, ['expected_revision', 'candidate_id', 'decision', 'source_id']),
    tool('profile_forget_observations', 'Purge selected observations and dependent active or historical rules.', {'expected_revision': integer(), 'observation_ids': {'type': 'array', 'items': string(80), 'minItems': 1, 'maxItems': 200}}, ['expected_revision', 'observation_ids']),
    tool('profile_reset', 'Forget all profile content, retain replay suppression hashes, and pause personalization.', {'expected_revision': integer()}, ['expected_revision']),
    tool('conversation_import', 'Import authorized conversation excerpts, extract open-text proposals and preserve original request transitions. Requires host conversation opt-in.', {'expected_revision': integer(), 'conversation': CONVERSATION}, ['expected_revision', 'conversation']),
    tool('profile_proposal_review', 'Record a user review of a sourced open-text proposal. An optional existing rule id makes an explicit correction.', {'expected_revision': integer(), 'proposal_id': string(80), 'decision': {'type': 'string', 'enum': ['accept', 'reject']}, 'source_id': string(200), 'replace_rule_id': string(80)}, ['expected_revision', 'proposal_id', 'decision', 'source_id']),
    tool('profile_portrait', 'Describe imported writing patterns, confirmed working preferences and pending proposals with evidence; never diagnose personality.', {'context': string(200)}, ['context'], True),
    tool('profile_forecast', 'Retrieve what followed similar historical requests, with sources and abstention. Suggestions never execute.', {'context': string(200), 'request': string(2000)}, ['context', 'request'], True),
    tool('profile_forget_conversation', 'Delete a conversation and all dependent proposals, rules, writing features and original transitions.', {'expected_revision': integer(), 'session_id': string(80)}, ['expected_revision', 'session_id']),
    tool('profile_forget_messages', 'Delete selected user-message evidence and its dependent proposals, rules, style contributions and transitions.', {'expected_revision': integer(), 'source_keys': {'type': 'array', 'items': string(80), 'minItems': 1, 'maxItems': 100}}, ['expected_revision', 'source_keys']),
    tool('profile_model_context', 'Build a local extraction request from authorized stored excerpts; this tool sends nothing to a provider.', {'context': string(200)}, ['context'], True),
    tool('profile_model_propose', 'Validate host-model proposals against exact stored user quotes and stage them for human review; cannot confirm a rule.', {'expected_revision': integer(), 'proposals': {'type': 'array', 'items': MODEL_PROPOSAL, 'minItems': 1, 'maxItems': 20}}, ['expected_revision', 'proposals']),
]


def subject_key(args):
    return 'profile:' + identifier(args.subject)


def load(db, args):
    return upgrade(db.get(subject_key(args)) or blank_profile(args.subject))


def source_hash(value):
    return digest(value)


def recall(db, args, context):
    profile = load(db, args)
    rules = [] if profile['paused'] else matching_rules(profile, context)
    return {'subject_id': profile['subject_id'], 'revision': profile['revision'], 'paused': profile['paused'], 'rules': rules[:30]}


def save_rule(profile, rule):
    identifier(rule['id'])
    replaced = [rid for rid, existing in profile['rules'].items() if rid != rule['id'] and rule.get('dimension') and existing.get('dimension') == rule['dimension'] and context_key(existing['scope']) == context_key(rule['scope'])]
    need(rule['id'] in profile['rules'] or replaced or len(profile['rules']) < 30, 'RULE_LIMIT', 'Review the existing 30 rules before adding another.')
    previous = profile['rules'].get(rule['id'])
    if previous:
        profile['history'].append({'rule': previous, 'superseded_at': stamp()})
    # A typed correction replaces a conflicting active typed rule in the same scope.
    if replaced:
        rule['supersedes_rule_ids'] = sorted(set(replaced))
        for rid in replaced:
            profile['history'].append({'rule': profile['rules'].pop(rid), 'superseded_at': stamp()})
    profile['rules'][rule['id']] = rule


def clear_managed_files(db, args):
    # Local import lets the storage module own its platform-specific deletion rules.
    from host_support import purge_subject_files
    purge_subject_files(db.root, args.subject)


def dispatch(name, values, args):
    selected = next((item for item in TOOLS if item['name'] == name), None)
    need(selected is not None, 'UNKNOWN_TOOL', 'Choose a listed tool.')
    validate(values, selected['inputSchema'])
    need(args.subject, 'SUBJECT_REQUIRED', 'Bind --subject to a locally verified account mapping; tool arguments cannot change it.')
    identifier(args.subject)
    db = Database(args.root)
    try:
        if name == 'profile_read':
            return recall(db, args, values['context'])
        if name == 'profile_insights':
            return insights(load(db, args), values['context'])
        if name == 'profile_portrait':
            return portrait(load(db, args), values['context'])
        if name == 'profile_model_context':
            return model_context(load(db, args), values['context'])
        if name == 'profile_forecast':
            profile = load(db, args)
            result = {'status': 'paused', 'candidates': [], 'reasons': ['Personalization is paused.']} if profile['paused'] else forecast(profile['conversation_messages'], profile['conversation_transitions'], values['context'], values['request'])
            return {'subject_id': args.subject, 'revision': profile['revision'], **result}
        if name == 'profile_export':
            def export():
                profile = load(db, args)
                path = db.root / (args.subject + '-profile-export.json')
                atomic(path, json.dumps(profile, indent=2) + '\n')
                return {'path': str(path), 'profile': profile, 'backup_note': 'External copies, provider logs, and legacy unbound host output are outside this export and deletion boundary.'}
            return db.transaction(export)

        def update():
            profile = load(db, args)
            need(profile['revision'] == values['expected_revision'], 'STALE_REVISION', 'Read the current profile before changing it.')
            replayed = False
            details = {}
            if name in ('profile_correct', 'profile_observe', 'profile_review', 'conversation_import', 'profile_proposal_review', 'profile_model_propose'):
                need(not profile['paused'], 'MEMORY_PAUSED', 'Resume memory before saving ordinary updates.')
            if name == 'profile_pause':
                profile['paused'] = values['paused']
            elif name == 'conversation_import':
                need(getattr(args, 'enable_conversations', False), 'CONVERSATIONS_DISABLED', 'The operator must explicitly enable authorized conversation import.')
                details = import_conversation(profile, values['conversation'])
                replayed = details.pop('replayed')
            elif name == 'profile_proposal_review':
                details = review_proposal(profile, values, save_rule)
            elif name == 'profile_model_propose':
                need(getattr(args, 'enable_conversations', False), 'CONVERSATIONS_DISABLED', 'Conversation learning must be enabled in host configuration.')
                details = import_model_proposals(profile, values['proposals'])
                replayed = details.pop('replayed')
            elif name == 'profile_forget_conversation':
                session_key = 'session-' + digest(identifier(values['session_id']))
                need(session_key in profile['conversation_sessions'], 'SESSION_MISSING', 'This conversation session does not exist.')
                keys = [key for key, message in profile['conversation_messages'].items() if message['session_key'] == session_key]
                details = purge(profile, conversation_keys=keys)
                del profile['conversation_sessions'][session_key]
                clear_managed_files(db, args)
            elif name == 'profile_forget_messages':
                keys = values['source_keys']
                need(len(keys) == len(set(keys)) and all(key in profile['conversation_messages'] for key in keys), 'SOURCE_MISSING', 'Choose distinct source keys from the current profile.')
                details = purge(profile, conversation_keys=keys)
                clear_managed_files(db, args)
            elif name == 'profile_correct':
                raw = values['rule']
                identifier(raw['id'])
                for field in ('statement', 'scope', 'source_id', 'source_summary'):
                    content(raw[field], field, 1000 if field in ('statement', 'source_summary') else 200)
                need(('dimension' in raw) == ('value' in raw), 'INVALID_DIMENSION', 'Supply both dimension and value, or neither.')
                if 'dimension' in raw:
                    typed_value(raw['dimension'], raw['value'])
                source, hashed, replayed = check_source(profile, raw['source_id'], raw)
                if not replayed:
                    rule = {**raw, 'confirmed_at': stamp(), 'source_hash': source}
                    if raw.get('expires_at'):
                        rule['expires_at'] = timestamp(raw['expires_at'], 'INVALID_EXPIRY').isoformat()
                    save_rule(profile, rule)
                    profile['source_hashes'][source] = hashed
            elif name == 'profile_observe':
                need(getattr(args, 'enable_observations', False), 'OBSERVATIONS_DISABLED', 'The account owner must enable observation collection in host configuration.')
                raw = values['event']
                event = normalize_event(raw)
                need(digest(event['id']) not in profile['deleted_observation_hashes'], 'SOURCE_FORGOTTEN', 'This deleted observation identifier cannot be reused.')
                source, hashed, replayed = check_source(profile, event['source_id'], raw)
                if not replayed:
                    need(event['id'] not in profile['observations'], 'OBSERVATION_CONFLICT', 'Use a new observation identifier.')
                    need(len(profile['observations']) < 200, 'OBSERVATION_LIMIT', 'Review or forget existing observations before adding more than 200.')
                    profile['observations'][event['id']] = {**event, 'source_hash': source}
                    profile['source_hashes'][source] = hashed
            elif name == 'profile_review':
                candidate = None
                for context in sorted({e['context'] for e in profile['observations'].values()}):
                    candidate = next((c for c in insights(profile, context)['candidates'] if c['candidate_id'] == values['candidate_id']), None)
                    if candidate:
                        break
                need(candidate is not None, 'CANDIDATE_STALE', 'Read current insights and review a current candidate.')
                need(candidate['status'] == 'ready_to_review', 'CANDIDATE_NOT_READY', 'This candidate does not meet the review threshold or conflicts with a confirmed preference.')
                source, hashed, replayed = check_source(profile, values['source_id'], {k: v for k, v in values.items() if k != 'expected_revision'})
                if not replayed:
                    if values['decision'] == 'reject':
                        profile['dismissed_candidates'][candidate['candidate_id']] = {'source_hash': source}
                    else:
                        rid = 'learned-' + digest(candidate['context'] + '\0' + candidate['dimension'])[:24]
                        rule = {'id': rid, 'statement': STATEMENTS[candidate['dimension']][candidate['value']], 'scope': candidate['context'], 'kind': 'explicit', 'source_id': values['source_id'], 'source_summary': 'The host recorded the user confirmation of a scoped evidence candidate.', 'source_hash': source, 'dimension': candidate['dimension'], 'value': candidate['value'], 'evidence_ids': candidate['source_event_ids'], 'confirmed_at': stamp()}
                        save_rule(profile, rule)
                        details['rule_id'] = rid
                    profile['source_hashes'][source] = hashed
            elif name == 'profile_forget':
                rid = identifier(values['rule_id'])
                need(rid in profile['rules'], 'RULE_MISSING', 'This active rule does not exist.')
                details = purge(profile, rule_ids=[rid])
                clear_managed_files(db, args)
            elif name == 'profile_forget_observations':
                event_ids = values['observation_ids']
                need(event_ids and len(event_ids) == len(set(event_ids)), 'INVALID_INPUT', 'Provide a nonempty list of distinct observation identifiers.')
                need(all(identifier(eid) in profile['observations'] for eid in event_ids), 'OBSERVATION_MISSING', 'A selected observation does not exist.')
                details = purge(profile, event_ids=event_ids)
                clear_managed_files(db, args)
            elif name == 'profile_reset':
                sources = set(profile['source_hashes']) | set(profile['deleted_source_hashes'])
                old_ids = set(profile['deleted_observation_hashes']) | {digest(eid) for eid in profile['observations']}
                revision = profile['revision']
                profile = blank_profile(args.subject)
                profile.update(revision=revision, paused=True, deleted_source_hashes=sorted(sources), deleted_observation_hashes=sorted(old_ids))
                clear_managed_files(db, args)
            if replayed:
                return {'profile': profile, 'replayed': True, **details}
            profile['revision'] += 1
            profile['updated_at'] = stamp()
            db.put(subject_key(args), profile)
            db.event(name, {'subject_hash': digest(args.subject), 'revision': profile['revision']})
            return {'profile': profile, 'replayed': False, **details}
        return db.transaction(update)
    finally:
        db.close()


if __name__ == '__main__':
    raise SystemExit(main('user_behavior_personalization', '0.4.0', TOOLS, dispatch))
