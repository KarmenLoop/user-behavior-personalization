# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""One bounded, explicitly requested model job per local workspace."""
import copy
import threading
from types import SimpleNamespace

from host import PLAN_FIELDS
from host_support import identifier, need, Problem, schema, string, integer, validate
from learning import fingerprint
import model_workflows


class ModelJobs:
    def __init__(self,args):
        self.args=args
        self.lock=threading.Lock()
        self.cancelled=threading.Event()
        self.records={}
        self.active=None

    def submit(self,value):
        need(getattr(self.args,'enable_models',False),'MODELS_DISABLED','Restart this workspace with --enable-models and --model before sending selected data.')
        need(isinstance(value,dict) and value.get('kind') in ('learn','compare'),'INVALID_JOB','Choose a semantic learning or answer comparison job.')
        common={'kind':{'type':'string','enum':[value['kind']]},'request_id':string(80),'expected_revision':integer(),'context':string(200)}
        if value['kind']=='learn':
            fields={'source_keys':{'type':'array','minItems':1,'maxItems':20,'items':string(80)}}
            required=['source_keys']
            need(getattr(self.args,'enable_conversations',False),'CONVERSATIONS_DISABLED','Enable authorized conversation import before semantic analysis.')
        else:
            fields={k:v for k,v in PLAN_FIELDS.items() if k!='context'}
            required=['task']
        validate(value,schema({**common,**fields},[*common,*required]))
        job_id=identifier(value['request_id'])
        identity=fingerprint(value)
        with self.lock:
            old=self.records.get(job_id)
            if old is not None:
                need(old['identity']==identity,'REQUEST_CONFLICT','This request identifier already belongs to different arguments.')
                return copy.deepcopy(old['public'])
            need(self.active is None,'MODEL_JOB_BUSY','Wait for the current model job to finish before starting another.')
            need(not self.cancelled.is_set(),'MODEL_CANCELLED','This local workspace is closing.')
            # Reject a stale form before dispatch. Workflows recheck throughout IO.
            model_workflows.snapshot(self.args,value['context'],value['expected_revision'])
            while len(self.records)>=50:
                self.records.pop(next(iter(self.records)))
            row={'identity':identity,'public':{'job_id':job_id,'kind':value['kind'],'status':'running'}}
            self.records[job_id]=row
            self.active=job_id
            threading.Thread(target=self.run,args=(job_id,copy.deepcopy(value)),daemon=True).start()
            return copy.deepcopy(row['public'])

    def run(self,job_id,value):
        args=SimpleNamespace(**vars(self.args),model_cancelled=self.cancelled)
        try:
            operation=model_workflows.learn if value['kind']=='learn' else model_workflows.compare
            kwargs={k:v for k,v in value.items() if k not in ('request_id','kind')}
            result=operation(args,**kwargs)
            # Results contain IDs/counts only; private answers use live profile reads.
            public={'job_id':job_id,'kind':value['kind'],'status':'completed','result':result}
        except Problem as error:
            public={'job_id':job_id,'kind':value['kind'],'status':'failed','error':{'code':error.code,'message':str(error)}}
        except Exception:
            public={'job_id':job_id,'kind':value['kind'],'status':'failed',
                    'error':{'code':'MODEL_WORKFLOW_FAILED','message':'The model workflow could not finish. No completed result was saved.'}}
        finally:
            with self.lock:
                self.records[job_id]['public']=public
                self.active=None

    def read(self,job_id):
        identifier(job_id)
        with self.lock:
            need(job_id in self.records,'MODEL_JOB_MISSING','This job is no longer in the local workspace session.')
            return copy.deepcopy(self.records[job_id]['public'])

    def close(self):
        self.cancelled.set()
