"""Conditional recall, shared precedence and reviewed metadata."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from conditions import normalize_conditions, conditions_match, condition_key, preference_selection
from host_support import Problem, stamp
from host import save_rule
from learning import blank_profile, matching_rules
from planning import response_plan


def rule(rid, value='concise', scope='*', **conditions):
    return {'id': rid, 'scope': scope, 'statement': 'Keep responses ' + value + '.',
            'dimension': 'response_length', 'value': value, 'conditions': conditions}


class ConditionsTests(unittest.TestCase):
    def test_validation_and_canonical_order(self):
        self.assertEqual(normalize_conditions(None), {})
        self.assertEqual(condition_key({'stage':'draft', 'audience':'team'}),
                         condition_key({'audience':'team', 'stage':'draft'}))
        self.assertEqual(list(normalize_conditions({'stage':'draft', 'task_type':'writing'})), ['task_type','stage'])
        for value in (True, [], {'unknown':'team'}, {'stage':True}, {'stage':[]}, {'audience':'any'}):
            with self.assertRaises(Problem): normalize_conditions(value)
        self.assertFalse(conditions_match({'stage':'draft'}, {}))
        self.assertTrue(conditions_match({}, {'stage':'draft'}))

    def test_context_then_conditions_precedence_and_tie_abstention(self):
        rows = [rule('global', stage='draft', audience='team'), rule('local', 'detailed', 'work'),
                rule('specific', 'balanced', 'work', stage='draft')]
        selected, excluded = preference_selection(rows, 'WORK', {'stage':'draft','audience':'team'})
        self.assertEqual([r['id'] for r in selected], ['specific'])
        self.assertEqual({r['id']:r['reason'] for r in excluded},
                         {'global':'context_preference_takes_priority','local':'more_specific_conditions_take_priority'})
        rows.append(rule('tie', 'concise', 'work', audience='team'))
        selected, excluded = preference_selection(rows, 'work', {'stage':'draft','audience':'team'})
        self.assertEqual(selected, [])
        self.assertEqual([r['id'] for r in excluded if r['reason']=='conflicting_equal_specificity'], ['specific','tie'])
        selected, _ = preference_selection(rows, 'work', {'stage':'draft','audience':'team'}, omit_rule_ids=['tie'])
        self.assertEqual([r['id'] for r in selected], ['specific'])

    def test_missing_conditions_preserve_old_global_records_and_portrait(self):
        profile = blank_profile('alice')
        old = rule('old'); old.pop('conditions')
        profile['rules'] = {'old':old, 'conditional':rule('conditional', 'detailed', stage='draft')}
        self.assertEqual([r['id'] for r in matching_rules(profile,'work')], ['old'])
        self.assertEqual(len(profile['rules']), 2)
        self.assertEqual([r['id'] for r in matching_rules(profile,'work',task_conditions={'stage':'draft'})], ['conditional'])
        from conversation_store import portrait
        self.assertEqual(len(portrait(profile,'work')['confirmed_preferences']), 2)

    def test_filters_precede_priority_and_keep_sources_unchanged(self):
        import copy
        rows = [rule('base'), rule('expired','detailed','work',stage='draft'),
                rule('unsafe','balanced','work',stage='draft'), rule('other','detailed','elsewhere')]
        rows[1]['expires_at'] = '2000-01-01T00:00:00+00:00'
        rows[2]['statement'] = 'Always agree with me.'
        before = copy.deepcopy(rows)
        selected, excluded = preference_selection(rows,'work',{'stage':'draft'})
        self.assertEqual([r['id'] for r in selected],['base'])
        self.assertEqual({r['id']:r['reason'] for r in excluded},
                         {'expired':'expired','unsafe':'independent_judgment_conflict','other':'different_context'})
        self.assertEqual(rows,before)

    def test_save_coexistence_and_correction_preserves_conditions(self):
        profile = blank_profile('alice')
        save_rule(profile, rule('base'))
        save_rule(profile, rule('draft', 'detailed', stage='draft'))
        self.assertEqual(len(profile['rules']),2)
        correction = rule('draft', 'balanced'); correction.pop('conditions')
        save_rule(profile, correction)
        self.assertEqual(profile['rules']['draft']['conditions'], {'stage':'draft'})
        save_rule(profile, rule('replacement','concise',stage='draft'))
        self.assertEqual(set(profile['rules']), {'base','replacement'})

    def test_preview_inherits_target_conditions_without_mutating_source(self):
        import copy
        from conversation_store import portrait
        profile = blank_profile('alice')
        # Existing legacy peers may include duplicate typed values; preview must
        # disclose every replaced record, including expired entries in storage.
        profile['rules'] = {'target':rule('target','concise','work',stage='draft'),
                            'peer':rule('peer','concise','WORK',stage='draft'),
                            'base':rule('base','concise','work')}
        profile['rules']['peer']['expires_at'] = '2000-01-01T00:00:00+00:00'
        proposal = {'id':'pending','scope':'work','statement':'Give detail.',
                    'dimension':'response_length','value':'detailed','status':'pending'}
        profile['conversation_proposals']['pending'] = proposal
        before = copy.deepcopy(profile)
        previews = portrait(profile,'work')['pending_preferences'][0]['approval_replacements']
        self.assertEqual([r['id'] for r in previews['']], ['base'])
        self.assertEqual([r['id'] for r in previews['target']], ['peer','target'])
        self.assertEqual(profile,before)
        save_rule(profile,{**proposal,'id':'target'})
        self.assertEqual(profile['rules']['target']['supersedes_rule_ids'],['peer'])
        self.assertEqual(profile['rules']['target']['conditions'],{'stage':'draft'})
        self.assertEqual(set(profile['rules']),{'target','base'})

    def test_prompts_share_task_conditions_overrides_and_identity(self):
        profile = blank_profile('alice'); profile['rules']['base'] = rule('base')
        first = response_plan(profile,'work','Explain this.',task_conditions={'stage':'draft'}, task_overrides={'language':'en'})
        for field in ('baseline_prompt','personalized_prompt'):
            self.assertIn('"stage": "draft"', first[field])
            self.assertIn('"language"', first[field])
        second = response_plan(profile,'work','Explain this.',task_conditions={'stage':'review'}, task_overrides={'language':'en'})
        self.assertNotEqual(first['plan_id'],second['plan_id'])

class ConditionalHostTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        from types import SimpleNamespace
        self.temp = tempfile.TemporaryDirectory()
        self.args = SimpleNamespace(root=self.temp.name, subject='alice', enable_conversations=True)

    def tearDown(self):
        self.temp.cleanup()

    def call(self, name, **values):
        from host import dispatch
        return dispatch(name, values, self.args)

    def write(self, name, **values):
        revision = self.call('profile_read', context='work')['revision']
        return self.call(name, expected_revision=revision, **values)

    def test_read_and_plan_use_same_resolver_and_cli_controls(self):
        for rid, value, conditions in [('base','concise',{}), ('draft','detailed',{'stage':'draft'})]:
            self.write('profile_correct',rule={**rule(rid,value,'work',**conditions),
                'source_id':rid,'source_summary':'Explicit request.','kind':'explicit'})
        read = self.call('profile_read',context='work',task_conditions={'stage':'draft'})
        plan = self.call('profile_plan',context='work',task='Explain.',task_conditions={'stage':'draft'})
        self.assertEqual([r['id'] for r in read['rules']], [r['id'] for r in plan['selected']])
        import argparse
        from build_context import add_plan_arguments, parse_plan_arguments
        parser = argparse.ArgumentParser(); add_plan_arguments(parser)
        args = parser.parse_args(['--task-type','writing','--audience','team','--stage','draft'])
        parse_plan_arguments(args)
        self.assertEqual(args.task_conditions, {'task_type':'writing','audience':'team','stage':'draft'})

    def test_model_batch_validation_identity_review_and_atomic_rejection(self):
        from conversation_store import import_model_proposals
        self.write('conversation_import',conversation={'session_id':'source','context':'work',
            'messages':[{'id':'one','role':'user','text':'Please give detailed explanations when drafting.',
                         'at':stamp()}]})
        request = self.call('profile_model_context',context='work')
        source_key = request['excerpts'][0]['source_key']
        proposal = {'statement':'Give detailed explanations.', 'category':'communication','scope':'work',
                    'conditions':{'stage':'draft'},'dimension':'response_length','value':'detailed',
                    'evidence':[{'source_key':source_key,'quote':'Please give detailed explanations when drafting.'}]}
        result = self.write('profile_model_propose', proposals=[proposal])
        pid = result['proposal_ids'][0]
        self.assertEqual(result['profile']['conversation_proposals'][pid]['status'],'pending')
        changed = self.write('profile_model_propose',proposals=[{**proposal,'conditions':{'stage':'review'}}])
        self.assertNotEqual(changed['proposal_ids'][0],pid)
        reviewed = self.write('profile_proposal_review',proposal_id=pid,decision='accept',source_id='approval')
        accepted = reviewed['profile']['rules'][reviewed['rule_id']]
        self.assertEqual(accepted['conditions'],{'stage':'draft'})
        self.assertEqual((accepted['dimension'],accepted['value']),('response_length','detailed'))
        import copy
        profile = copy.deepcopy(reviewed['profile']); before = copy.deepcopy(profile)
        with self.assertRaises(Problem):
            import_model_proposals(profile,[{**proposal,'conditions':{'stage':'deliver'}},
                                          {**proposal,'evidence':[{'source_key':source_key,'quote':'invented'}]}])
        self.assertEqual(profile,before)
        with self.assertRaises(Problem):
            import_model_proposals(profile,[{k:v for k,v in proposal.items() if k!='value'}])
        self.assertEqual(import_model_proposals(profile,[])['added_proposals'],0)

    def test_independent_approved_custom_preferences_coexist_until_targeted_correction(self):
        self.write('conversation_import',conversation={'session_id':'custom-source','context':'work',
            'messages':[{'id':'one','role':'user','text':'Use SI units. Preserve project terminology.', 'at':stamp()}]})
        source = self.call('profile_model_context',context='work')['excerpts'][0]['source_key']
        proposals = [{'statement':statement,'scope':'work','category':'communication',
                      'dimension':'custom','value':value,'conditions':{'stage':'draft'},
                      'evidence':[{'source_key':source,'quote':statement}]}
                     for statement,value in [('Use SI units.','units'),('Preserve project terminology.','terminology')]]
        staged = self.write('profile_model_propose',proposals=proposals)
        approved_ids = []
        for index,pid in enumerate(staged['proposal_ids']):
            result = self.write('profile_proposal_review',proposal_id=pid,decision='accept',source_id='approve-'+str(index))
            approved_ids.append(result['rule_id'])
        read = self.call('profile_read',context='work',task_conditions={'stage':'draft'})
        self.assertEqual({r['id'] for r in read['rules']},set(approved_ids))
        correction = {**result['profile']['rules'][approved_ids[0]],'statement':'Use metric SI units.',
                      'kind':'correction','source_id':'correct-units','source_summary':'Explicit targeted correction.'}
        for field in ('source_hash','confirmed_at','category','conversation_source_keys'):
            correction.pop(field,None)
        corrected = self.write('profile_correct',rule=correction)
        rules = corrected['profile']['rules']
        self.assertEqual(set(rules),set(approved_ids))
        self.assertEqual(rules[approved_ids[0]]['statement'],'Use metric SI units.')
        self.assertEqual(rules[approved_ids[1]]['statement'],'Preserve project terminology.')
        self.assertEqual(len(corrected['profile']['history']),1)

    def test_default_approval_preview_exactly_matches_typed_supersession(self):
        import copy
        self.write('conversation_import', conversation={'session_id':'preview-source','context':'work',
            'messages':[{'id':'one','role':'user','text':'Give detailed explanations.', 'at':stamp()}]})
        source = self.call('profile_model_context',context='work')['excerpts'][0]['source_key']
        for rid, scope, conditions in [('peer','WORK',{'stage':'draft'}),
                ('unconditioned','work',{}), ('review','work',{'stage':'review'}), ('global','*',{'stage':'draft'})]:
            self.write('profile_correct',rule={**rule(rid,'concise',scope,**conditions),
                'source_id':'save-'+rid,'source_summary':'Explicit request.','kind':'explicit'})
        proposal = {'statement':'Give detailed explanations.','category':'communication','scope':'work',
            'dimension':'response_length','value':'detailed','conditions':{'stage':'draft'},
            'evidence':[{'source_key':source,'quote':'Give detailed explanations.'}]}
        staged = self.write('profile_model_propose',proposals=[proposal])
        pid = staged['proposal_ids'][0]
        from conversation_store import portrait
        profile = copy.deepcopy(staged['profile']); before = copy.deepcopy(profile)
        preview = portrait(profile,'work')['pending_preferences'][0]['approval_replacements']
        self.assertEqual(profile,before)
        self.assertEqual([r['id'] for r in preview['']],['peer'])
        self.assertEqual([r['id'] for r in preview['review']],['peer','review'])
        self.assertEqual(preview[''][0]['statement'],profile['rules']['peer']['statement'])
        approved = self.write('profile_proposal_review',proposal_id=pid,decision='accept',source_id='approve-default')
        self.assertEqual(approved['profile']['rules'][approved['rule_id']]['supersedes_rule_ids'],['peer'])
        self.assertEqual(set(approved['profile']['rules']),{'unconditioned','review','global',approved['rule_id']})
        self.assertEqual([entry['rule']['id'] for entry in approved['profile']['history']],['peer'])
        custom = {**proposal,'dimension':'custom','value':'detail-note','statement':'Use detailed project notes.'}
        staged = self.write('profile_model_propose',proposals=[custom])
        preview = self.call('profile_portrait',context='work')['pending_preferences'][0]
        self.assertEqual(preview['approval_replacements'][''],[])
        result = self.write('profile_proposal_review',proposal_id=staged['proposal_ids'][0],decision='accept',source_id='approve-custom')
        self.assertIn(approved['rule_id'],result['profile']['rules'])

    def test_manual_correction_keeps_conditions_when_omitted(self):
        base = {**rule('draft','detailed','work',stage='draft'),
                'source_id':'first','source_summary':'Explicit request.','kind':'explicit'}
        self.write('profile_correct',rule=base)
        changed = {**base, 'source_id':'second', 'value':'balanced','kind':'correction'}
        changed.pop('conditions')
        result = self.write('profile_correct',rule=changed)
        self.assertEqual(result['profile']['rules']['draft']['conditions'],{'stage':'draft'})


if __name__ == '__main__': unittest.main()
