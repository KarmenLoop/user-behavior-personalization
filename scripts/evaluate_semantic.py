#!/usr/bin/env python3
# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Run synthetic semantic cases; retain pending proposals for separate review."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
from types import SimpleNamespace

from host import dispatch
from host_support import need, Problem, private_root, atomic, identifier, stamp
from model_workflows import learn
from learning import fingerprint

ROOT=Path(__file__).resolve().parents[1]


def run_case(case,args,output):
    cid=identifier(case['id'])
    bound=SimpleNamespace(root=output/'private-state'/cid,subject='synthetic-'+cid,
                          enable_conversations=True,model=args.model,system_proxy=args.system_proxy,
                          model_timeout=args.timeout)
    text=case['text']
    imported=dispatch('conversation_import',{'expected_revision':0,'conversation':{'session_id':cid,'context':case['context'],
                 'messages':[{'id':'user','role':'user','text':text,'at':stamp()}]}},bound)
    before=imported['profile']
    row={'case_id':cid,'source_sha256':fingerprint(text),'input_scope':'synthetic_authored_message',
         'lexical_proposals':len(before['conversation_proposals']),'model':args.model,
         'measurement':'provider execution and pending extraction; not user benefit or model training'}
    try:
        row['execution']=learn(bound,context=case['context'],source_keys=list(before['conversation_messages']),expected_revision=before['revision'])
        after=dispatch('profile_export',{},bound)['profile']
        ids=row['execution']['proposal_ids']
        row['semantic_proposals']=[after['conversation_proposals'][pid] for pid in ids]
        row['confirmed_rule_count']=len(after['rules'])
        row['status']='completed'
    except (Problem,OSError,ValueError) as error:
        row.update(status='failed',error={'code':getattr(error,'code','ERROR'),'message':str(error)})
    atomic(output/(cid+'.json'),json.dumps(row,ensure_ascii=True,indent=2)+'\n')
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fixtures',type=Path,default=ROOT/'examples/semantic-evaluation/v0.7.0.inputs.json')
    p.add_argument('--output',type=Path,required=True,help='New private directory outside the package.')
    p.add_argument('--model',required=True);p.add_argument('--system-proxy',action='store_true')
    p.add_argument('--timeout',type=int,default=90);p.add_argument('--workers',type=int,choices=[1,2],default=1)
    args=p.parse_args()
    try:
        output=private_root(args.output)
        need(not output.exists(),'OUTPUT_EXISTS','Use a new output directory to preserve earlier evidence.')
        need(args.fixtures.stat().st_size<=1_000_000,'INPUT_TOO_LARGE','Fixtures exceed1 MB.')
        payload=json.loads(args.fixtures.read_text(encoding='utf-8'));cases=payload['cases']
        need(isinstance(cases,list) and 0<len(cases)<=50,'INVALID_FIXTURES','Use1–50 synthetic cases.')
        need(len({identifier(c['id']) for c in cases})==len(cases),'INVALID_FIXTURES','Case identifiers must be distinct.')
        output.mkdir(parents=True,mode=0o700)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            rows=list(pool.map(lambda case:run_case(case,args,output),cases))
        report={'model':args.model,'fixtures_sha256':fingerprint(payload),'scope':payload.get('scope'),
                'quality_grade':'NOT_GRADED','cases':len(rows),'completed':sum(row['status']=='completed' for row in rows),
                'records':[{'case_id':r['case_id'],'status':r['status'],'receipt':r['case_id']+'.json'} for r in rows]}
        atomic(output/'summary.json',json.dumps(report,indent=2)+'\n')
        print(json.dumps(report,indent=2))
        return 0 if report['completed']==len(rows) else 1
    except (Problem,OSError,ValueError,KeyError,TypeError) as error:
        print(json.dumps({'code':getattr(error,'code','ERROR'),'message':str(error)}));return 2


if __name__=='__main__':raise SystemExit(main())
