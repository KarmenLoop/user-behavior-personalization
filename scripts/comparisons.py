# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Private real-answer comparisons; preference votes are not correctness labels."""
import secrets

from host_support import need, stamp
from learning import check_source, tombstone, context_key

ACCURACY_VALUES = ('not_checked','reported_correct','reported_incorrect')


def store_comparison(profile, plan, outputs, comparison_id):
    need(not profile['paused'],'MEMORY_PAUSED','Resume personalization before saving a comparison.')
    records = profile.setdefault('response_comparisons',{})
    need(len(records) < 20,'COMPARISON_LIMIT','Forget an older comparison before saving more than20.')
    need(plan['selected'],'NO_APPLICABLE_PREFERENCES','Confirm an applicable preference before comparing actual answers.')
    need(set(outputs)=={'baseline','personalized'},'COMPARISON_INCOMPLETE','Both actual responses must complete before saving.')
    need(all(isinstance(out.get('text'),str) and 0<len(out['text'])<=32000 for out in outputs.values()),
         'COMPARISON_INCOMPLETE','Both actual responses must contain bounded text.')
    arms = ['baseline','personalized']
    secrets.SystemRandom().shuffle(arms)
    record = {'comparison_id':comparison_id,'plan_id':plan['plan_id'],'context':plan['context'],
              'task_sha256':plan['task_sha256'],'task_conditions':plan.get('task_conditions',{}),
              'profile_revision':plan['revision'],'created_at':stamp(),
              'judgment_policy':{key:plan['judgment_policy'][key] for key in ('version','fingerprint')},
              'rule_versions':{r['id']:r['version_fingerprint'] for r in plan['selected']},
              'selected_preferences':plan['selected'],'outputs':outputs,
              'mapping':dict(zip(('a','b'),arms)),'revealed':False,'feedback_history':[]}
    records[comparison_id] = record
    return record


def get_record(profile, comparison_id):
    need(not profile['paused'],'MEMORY_PAUSED','Resume personalization before reading comparison answers.')
    record = profile.get('response_comparisons',{}).get(comparison_id)
    need(record is not None,'COMPARISON_MISSING','This comparison no longer exists.')
    return record


def read_comparison(profile, comparison_id):
    record = get_record(profile,comparison_id)
    result = {key:record[key] for key in ('comparison_id','plan_id','context','task_sha256','task_conditions',
                                        'profile_revision','created_at','judgment_policy','revealed')}
    result['revision'] = profile['revision']
    result['answers'] = {side:record['outputs'][arm]['text'] for side,arm in record['mapping'].items()}
    # Per-side prompt hashes/token counts would reveal the arm before a vote.
    result['model'] = record['outputs']['baseline']['metadata']['requested_model']
    result['feedback'] = record['feedback_history'][-1] if record['feedback_history'] else None
    result['learning_use'] = 'experience_report_not_truth_or_training_reward'
    if record['revealed']:
        result['mapping'] = record['mapping']
        result['selected_preferences'] = record['selected_preferences']
        result['execution_metadata'] = {side:record['outputs'][arm]['metadata'] for side,arm in record['mapping'].items()}
    return result


def list_comparisons(profile, context):
    result = {'context':context_key(context),'revision':profile['revision'],'paused':profile['paused'],'comparisons':[]}
    if profile['paused']: return result
    records = profile.get('response_comparisons',{}).values()
    for record in sorted(records,key=lambda row:row['created_at'],reverse=True):
        if record['context'] != result['context']: continue
        row = {key:record[key] for key in ('comparison_id','plan_id','created_at','task_conditions','revealed')}
        row['feedback'] = record['feedback_history'][-1] if record['feedback_history'] else None
        row['preference_count'] = len(record['rule_versions'])
        result['comparisons'].append(row)
    return result


def reveal_comparison(profile, comparison_id):
    record = get_record(profile,comparison_id)
    replayed = record['revealed']
    if not replayed:
        record['revealed'],record['revealed_at'],record['reveal_reason'] = True,stamp(),'explicit_reveal'
    return {'replayed':replayed,'comparison_id':comparison_id}


def vote_comparison(profile, values):
    record = get_record(profile,values['comparison_id'])
    payload = {key:values[key] for key in ('comparison_id','source_id','choice','accuracy_a','accuracy_b')}
    source,hashed,replayed = check_source(profile,values['source_id'],payload)
    if replayed: return {'replayed':True,'comparison_id':values['comparison_id']}
    need(values['choice'] in ('a','b','tie','neither'),'INVALID_CHOICE','Choose A, B, tie, or neither.')
    need(all(values[key] in ACCURACY_VALUES for key in ('accuracy_a','accuracy_b')),'INVALID_ACCURACY','Keep correctness reports separate from preference.')
    need(len(record['feedback_history'])<100,'OUTCOME_LIMIT','Forget this comparison before saving more than100 feedback revisions.')
    feedback = {key:values[key] for key in ('choice','accuracy_a','accuracy_b')}
    feedback.update(recorded_at=stamp(),source_hash=source,blinded=not record['revealed'],
                    evidence_kind='explicit_user_report_not_independent_verification')
    record['feedback_history'].append(feedback)
    record['revealed'],record['revealed_at'],record['reveal_reason'] = True,stamp(),'vote'
    profile['source_hashes'][source] = hashed
    return {'replayed':False,'comparison_id':values['comparison_id'],'feedback':feedback}


def forget_comparisons(profile, comparison_ids):
    records = profile.setdefault('response_comparisons',{})
    for cid in comparison_ids:
        record = records.pop(cid,None)
        for feedback in record.get('feedback_history',[]) if record else []:
            tombstone(profile,feedback['source_hash'])
