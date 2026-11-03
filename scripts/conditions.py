# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Validated task conditions and one deterministic confirmed-preference resolver."""
import json

from host_support import need, schema
from judgment import preference_conflict

CONDITION_VALUES = {
    'task_type': ('coding', 'debugging', 'writing', 'learning', 'planning', 'status'),
    'audience': ('self', 'team', 'client', 'public'),
    'stage': ('explore', 'draft', 'review', 'deliver'),
}
CONDITION_SCHEMA = schema({key: {'type': 'string', 'enum': list(values)}
                           for key, values in CONDITION_VALUES.items()})


def normalize_conditions(value):
    if value is None:
        return {}
    need(isinstance(value, dict), 'INVALID_CONDITIONS', 'Conditions must be an object.')
    need(all(key in CONDITION_VALUES for key in value), 'INVALID_CONDITIONS', 'Choose documented condition keys.')
    for key, item in value.items():
        need(isinstance(item, str) and item in CONDITION_VALUES[key], 'INVALID_CONDITIONS', 'Choose a documented condition value.')
    return {key: value[key] for key in CONDITION_VALUES if key in value}


def conditions_match(rule_conditions, task_conditions):
    rule = normalize_conditions(rule_conditions)
    task = normalize_conditions(task_conditions)
    return all(task.get(key) == value for key, value in rule.items())


def condition_key(value):
    return json.dumps(normalize_conditions(value), sort_keys=True, separators=(',', ':'))


def replacement_rule_ids(rules, rule):
    """Canonical typed replacement set, including inherited correction conditions."""
    from learning import DIMENSIONS, context_key
    previous = rules.get(rule['id'], {})
    conditions = rule.get('conditions', previous.get('conditions'))
    return sorted(rid for rid, existing in rules.items()
                  if rid != rule['id'] and rule.get('dimension') in DIMENSIONS
                  and existing.get('dimension') == rule['dimension']
                  and context_key(existing['scope']) == context_key(rule['scope'])
                  and condition_key(existing.get('conditions')) == condition_key(conditions))


def preference_selection(rules, context, task_conditions=None, now=None, *, omit_rule_ids=()):
    """Return (selected original rules, excluded rule copies with stable reasons).

    Context outranks condition specificity. Conflicting values at the winning
    specificity abstain for that dimension, including its lower-priority peers.
    """
    from learning import active, context_key
    key = context_key(context)
    task = normalize_conditions(task_conditions)
    eligible, excluded = [], []
    rows = rules.values() if isinstance(rules, dict) else rules
    for rule in sorted(rows, key=lambda r: (r['scope'] == '*', r['id'])):
        reason = None
        if not active(rule, now):
            reason = 'expired'
        elif rule['scope'] != '*' and context_key(rule['scope']) != key:
            reason = 'different_context'
        elif preference_conflict(rule['statement']):
            reason = 'independent_judgment_conflict'
        elif rule['id'] in omit_rule_ids:
            reason = 'omitted_for_this_task'
        elif not conditions_match(rule.get('conditions'), task):
            reason = 'conditions_not_matched'
        if reason:
            excluded.append({**rule, 'reason': reason})
        else:
            eligible.append(rule)
    groups = {}
    for rule in eligible:
        if rule.get('dimension') and rule['dimension'] != 'custom':
            groups.setdefault(rule['dimension'], []).append(rule)
    reasons = {}
    for peers in groups.values():
        rank = lambda r: (r['scope'] != '*', len(normalize_conditions(r.get('conditions'))))
        best = max(map(rank, peers))
        winners = [r for r in peers if rank(r) == best]
        conflict = len({r.get('value') for r in winners}) > 1
        for rule in peers:
            if rank(rule) != best:
                reasons[rule['id']] = ('context_preference_takes_priority' if rank(rule)[0] != best[0]
                                       else 'more_specific_conditions_take_priority')
            elif conflict:
                reasons[rule['id']] = 'conflicting_equal_specificity'
    selected = []
    for rule in eligible:
        if rule['id'] in reasons:
            excluded.append({**rule, 'reason': reasons[rule['id']]})
        else:
            selected.append(rule)
    excluded.sort(key=lambda r: (r['scope'] == '*', r['id']))
    return selected, excluded
