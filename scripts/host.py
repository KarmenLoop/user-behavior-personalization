#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""A subject-bound transactional profile adapter for local hosts."""
import json,hashlib
from host_support import Database,need,identifier,content,stamp,atomic,schema,string,integer,main

RULE=schema({'id':string(80),'statement':string(1000),'scope':string(200),'source_id':string(200),'source_summary':string(1000),'kind':{'type':'string','enum':['explicit','correction']},'expires_at':string(50)},['id','statement','scope','source_id','source_summary','kind'])
TOOLS=[
 {'name':'profile_read','description':'Read active preferences for the configured subject and context. Paused profiles return no rules.','inputSchema':schema({'context':string(200)},['context']),'annotations':{'readOnlyHint':True}},
 {'name':'profile_correct','description':'Atomically commit an explicit, sourced preference or correction for the configured subject.','inputSchema':schema({'expected_revision':integer(),'rule':RULE},['expected_revision','rule'])},
 {'name':'profile_pause','description':'Pause or resume ordinary recall and updates.','inputSchema':schema({'expected_revision':integer(),'paused':{'type':'boolean'}},['expected_revision','paused'])},
 {'name':'profile_forget','description':'Purge one rule and its historical content while retaining a source hash to prevent replay.','inputSchema':schema({'expected_revision':integer(),'rule_id':string(80)},['expected_revision','rule_id'])},
 {'name':'profile_export','description':'Export current data for the configured subject, including while paused.','inputSchema':schema({})}]

def subject_key(args):return 'profile:'+identifier(args.subject)
def load(db,args):return db.get(subject_key(args)) or {'subject_id':args.subject,'revision':0,'paused':False,'rules':{},'source_hashes':{},'deleted_source_hashes':[],'history':[],'updated_at':None}
def source_hash(value):return hashlib.sha256(value.encode()).hexdigest()

def recall(db,args,context):
 p=load(db,args);rules=[]
 if not p['paused']:
  for rule in p['rules'].values():
   if rule.get('expires_at') and rule['expires_at']<=stamp():continue
   if rule['scope']=='*' or rule['scope'].casefold() in context.casefold():rules.append(rule)
 return {'subject_id':p['subject_id'],'revision':p['revision'],'paused':p['paused'],'rules':rules[:30]}

def dispatch(name,a,args):
 need(args.subject,'SUBJECT_REQUIRED','Bind --subject to a locally verified account mapping; it cannot come from a tool argument.');identifier(args.subject)
 db=Database(args.root)
 try:
  if name=='profile_read':return recall(db,args,a['context'])
  if name=='profile_export':
   p=load(db,args);path=db.root/(args.subject+'-profile-export.json');atomic(path,json.dumps(p,indent=2)+'\n');return {'path':str(path),'profile':p,'backup_note':'Explicit exports are private offline copies; the adapter cannot erase copies outside its data root.'}
  def update():
   p=load(db,args);need(p['revision']==a['expected_revision'],'STALE_REVISION','Read the current profile before changing it.')
   if name=='profile_pause':p['paused']=a['paused']
   elif name=='profile_correct':
    need(not p['paused'],'MEMORY_PAUSED','Resume memory before saving an ordinary correction.');r=a['rule'];identifier(r['id']);source=source_hash(r['source_id'])
    need(source not in p['deleted_source_hashes'],'SOURCE_FORGOTTEN','This deleted source cannot recreate a preference.')
    if source in p['source_hashes']:
     need(p['source_hashes'][source]==source_hash(json.dumps(r,sort_keys=True)),'SOURCE_CONFLICT','A processed source was changed. Supply a genuinely new correction source.');return {'profile':p,'replayed':True}
    if r.get('expires_at'):
     import datetime
     try:date=datetime.datetime.fromisoformat(r['expires_at'].replace('Z','+00:00'));need(date.tzinfo is not None,'INVALID_EXPIRY','Use a timezone-qualified expiry.');r={**r,'expires_at':date.astimezone(datetime.timezone.utc).isoformat()}
     except ValueError:need(False,'INVALID_EXPIRY','Use an ISO timestamp with a timezone.')
    need(r['id'] in p['rules'] or len(p['rules'])<30,'RULE_LIMIT','Review the existing 30 rules before adding another.')
    p['source_hashes'][source]=source_hash(json.dumps(a['rule'],sort_keys=True));previous=p['rules'].get(r['id'])
    if previous:p['history'].append({'rule':previous,'superseded_at':stamp()})
    p['rules'][r['id']]={**r,'confirmed_at':stamp(),'source_hash':source}
   else:
    rid=identifier(a['rule_id']);need(rid in p['rules'],'RULE_MISSING','This active rule does not exist.')
    removed=[p['rules'].pop(rid)]+[x['rule'] for x in p['history'] if x['rule']['id']==rid]
    for rule in removed:
     value=rule['source_hash'];p['deleted_source_hashes'].append(value);p['source_hashes'].pop(value,None)
    p['deleted_source_hashes']=sorted(set(p['deleted_source_hashes']));p['history']=[x for x in p['history'] if x['rule']['id']!=rid]
    # Remove controlled exports that could reintroduce the deleted content. External copies remain the user's responsibility.
    for path in db.root.glob(args.subject+'-profile-export.json'):path.unlink()
   p['revision']+=1;p['updated_at']=stamp();db.put(subject_key(args),p)
   # Audit identifiers only: no deleted statement or source summary is retained here.
   db.event(name,{'subject_hash':source_hash(args.subject),'revision':p['revision']});return {'profile':p,'replayed':False}
  return db.transaction(update)
 finally:db.close()

if __name__=='__main__':raise SystemExit(main('user_behavior_personalization','0.2.0',TOOLS,dispatch))
