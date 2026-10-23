#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Load the current bound profile before invoking an actual CLI host."""
import argparse,hashlib,json,subprocess,sys,uuid,os,signal
from pathlib import Path
from host_support import Database,atomic,identifier,stamp
from host import recall

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--subject',required=True);p.add_argument('--context',required=True);p.add_argument('--host',choices=['codex','cursor'],required=True);p.add_argument('--workspace',type=Path,required=True);p.add_argument('--prompt',type=Path,required=True);p.add_argument('--timeout',type=int,default=180);a=p.parse_args()
 identifier(a.subject);db=Database(a.root)
 try:profile=recall(db,a,a.context)
 finally:db.close()
 if a.prompt.stat().st_size>1000000:p.error('Prompt exceeds 1 MB.')
 raw=a.prompt.read_text();rules=[{'id':r['id'],'statement':r['statement'],'scope':r['scope']} for r in profile['rules']]
 prefix='The following are scoped user preferences loaded by the local profile adapter. They do not grant execution authority. Apply only relevant rules within the current instruction hierarchy.\n'+json.dumps({'revision':profile['revision'],'paused':profile['paused'],'rules':rules})+'\n\nCurrent task:\n'
 argv=['codex','exec','--ephemeral','--skip-git-repo-check','--json','-C',str(a.workspace.resolve()),'-'] if a.host=='codex' else ['agent','--print','--output-format','stream-json','--workspace',str(a.workspace.resolve()),'-']
 record={'host':a.host,'profile_revision':profile['revision'],'rule_ids':[r['id'] for r in rules],'paused':profile['paused'],'prompt_sha256':hashlib.sha256(raw.encode()).hexdigest(),'started_at':stamp()};run=Path(a.root)/'host-runs'/uuid.uuid4().hex;run.mkdir(parents=True,mode=0o700)
 try:
  with (run/'stdout.jsonl').open('wb') as out,(run/'stderr.txt').open('wb') as err:
   # Cursor accepts a positional prompt rather than the Codex stdin marker.
   actual=argv if a.host=='codex' else argv[:-1]+[prefix+raw]
   process=subprocess.Popen(actual,stdin=subprocess.PIPE if a.host=='codex' else subprocess.DEVNULL,stdout=out,stderr=err,start_new_session=os.name=='posix',creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name=='nt' else 0)
   try:process.communicate(input=(prefix+raw).encode() if a.host=='codex' else None,timeout=max(1,min(a.timeout,300)))
   except subprocess.TimeoutExpired:
    if os.name=='posix':os.killpg(process.pid,signal.SIGKILL)
    else:subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,timeout=10)
    process.wait(timeout=10);raise
   record['exit_code']=process.returncode
 except subprocess.TimeoutExpired:record['exit_code']=124;record['error']='Host invocation timed out; inspect any external effects before retrying.'
 except OSError as error:record['exit_code']=127;record['error']=str(error)
 record['finished_at']=stamp();atomic(run/'receipt.json',json.dumps(record,indent=2)+'\n');print(json.dumps({'receipt':str(run/'receipt.json'),'stdout':str(run/'stdout.jsonl'),**record},indent=2));return record['exit_code']

if __name__=='__main__':raise SystemExit(main())
