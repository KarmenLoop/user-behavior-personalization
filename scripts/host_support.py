# Copyright 2026 KarmenLoop. SPDX-License-Identifier: Apache-2.0
"""Small local CLI/MCP transport and private transactional file helpers."""
import sys
if sys.version_info < (3, 11):
    raise SystemExit('The host adapter requires Python 3.11 or newer.')
import argparse,datetime,hashlib,json,os,secrets,sqlite3,tempfile,tomllib
from pathlib import Path

class Problem(ValueError):
    def __init__(self, code, message):super().__init__(message);self.code=code

def need(condition, code, message):
    if not condition:raise Problem(code,message)

def stamp():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def identifier(value):
    need(isinstance(value,str) and 0<len(value)<=80 and all(c.isascii() and (c.isalnum() or c in '-_') for c in value),'INVALID_ID','Use 1-80 ASCII letters, digits, hyphens or underscores.')
    return value

def content(value,name='text',limit=4000):
    need(isinstance(value,str) and 0<len(value.strip())<=limit,'INVALID_INPUT',name+' is empty or too long.')
    return value.strip()

def atomic(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.parent/('.'+path.name+'.'+secrets.token_hex(8)+'.tmp')
    try:
        with temporary.open('x',encoding='utf-8') as f:os.chmod(temporary,0o600);f.write(value);f.flush();os.fsync(f.fileno())
        os.replace(temporary,path)
    finally:
        if temporary.exists():temporary.unlink()

def under(root,value):
    root=Path(root).resolve();p=(root/value).resolve()
    need(p==root or root in p.parents,'PATH_OUTSIDE_WORKSPACE','The path must stay inside the configured workspace.')
    return p

def file_record(root,value):
    p=under(root,value);need(p.is_file(),'EVIDENCE_MISSING','Evidence file does not exist.')
    need(p.stat().st_size<=8*1024*1024,'EVIDENCE_TOO_LARGE','Evidence exceeds 8 MiB.')
    raw=p.read_bytes();return {'path':p.relative_to(Path(root).resolve()).as_posix(),'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}

class Database:
    def __init__(self,root):
        self.root=Path(root).resolve();self.root.mkdir(parents=True,exist_ok=True,mode=0o700);os.chmod(self.root,0o700)
        self.db=sqlite3.connect(self.root/'host.sqlite',timeout=5,isolation_level=None);os.chmod(self.root/'host.sqlite',0o600)
        self.db.execute('PRAGMA journal_mode=WAL');self.db.execute('PRAGMA secure_delete=ON');self.db.execute('CREATE TABLE IF NOT EXISTS objects(key TEXT PRIMARY KEY,payload TEXT NOT NULL)')
        self.db.execute('CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY,at TEXT NOT NULL,kind TEXT NOT NULL,payload TEXT NOT NULL)')
    def get(self,key):
        row=self.db.execute('SELECT payload FROM objects WHERE key=?',(key,)).fetchone();return json.loads(row[0]) if row else None
    def put(self,key,value):self.db.execute('INSERT INTO objects VALUES(?,?) ON CONFLICT(key) DO UPDATE SET payload=excluded.payload',(key,json.dumps(value)))
    def event(self,kind,value):self.db.execute('INSERT INTO events(at,kind,payload) VALUES(?,?,?)',(stamp(),kind,json.dumps(value)))
    def transaction(self,fn):
        self.db.execute('BEGIN IMMEDIATE')
        try:r=fn();self.db.execute('COMMIT');return r
        except BaseException:self.db.execute('ROLLBACK');raise
    def close(self):self.db.close()

def schema(properties,required=()):return {'type':'object','properties':properties,'required':list(required),'additionalProperties':False}
def string(maximum=4000):return {'type':'string','minLength':1,'maxLength':maximum}
def integer():return {'type':'integer','minimum':0}
def array(item):return {'type':'array','items':item,'maxItems':100}
def validate(value,s):
    typ=s.get('type');ok={'object':isinstance(value,dict),'array':isinstance(value,list),'string':isinstance(value,str),'integer':type(value)is int,'boolean':type(value)is bool}.get(typ,False)
    need(ok,'INVALID_INPUT','Expected '+str(typ)+'.')
    if typ=='object':
        need(all(k in value for k in s.get('required',[])),'INVALID_INPUT','Required tool arguments are missing.')
        need(s.get('additionalProperties',True) or all(k in s['properties'] for k in value),'INVALID_INPUT','Unknown tool argument.')
        for k,v in value.items():
            if k in s['properties']:validate(v,s['properties'][k])
    if typ=='array':
        need(len(value)<=s.get('maxItems',100),'INVALID_INPUT','Too many items.')
        for v in value:validate(v,s['items'])
    if typ=='string':need(s.get('minLength',0)<=len(value)<=s.get('maxLength',100000),'INVALID_INPUT','Text is empty or too long.')
    if typ=='integer':need(value>=s.get('minimum',0),'INVALID_INPUT','Integer is below the minimum.')
    if 'enum' in s:need(value in s['enum'],'INVALID_INPUT','Choose one of the listed values.')

def install(args,name,script):
    workspace=Path(args.workspace).resolve();need(workspace.is_dir(),'WORKSPACE_MISSING','Create the workspace first.')
    argv=[str(script),'--root',str(Path(args.root).resolve()),'--workspace',str(workspace),'--host-id',args.install_host]
    if args.subject:argv+=['--subject',args.subject]
    argv+=['mcp'];entry={'command':sys.executable,'args':argv}
    if args.install_host=='cursor':
        path=workspace/'.cursor/mcp.json';value=json.loads(path.read_text()) if path.exists() else {};value.setdefault('mcpServers',{})
        need(name not in value['mcpServers'],'HOST_EXISTS','This server is already configured. Existing entries were preserved.')
        value['mcpServers'][name]={'type':'stdio',**entry};atomic(path,json.dumps(value,indent=2)+'\n')
    else:
        path=workspace/'.codex/config.toml';existing=path.read_text() if path.exists() else '';parsed=tomllib.loads(existing)
        need(name not in parsed.get('mcp_servers',{}),'HOST_EXISTS','This server is already configured. Existing entries were preserved.')
        candidate=existing+'\n[mcp_servers.'+name+']\ncommand = '+json.dumps(entry['command'])+'\nargs = '+json.dumps(argv)+'\nstartup_timeout_sec = 15\n'
        try:tomllib.loads(candidate)
        except tomllib.TOMLDecodeError:raise Problem('CONFIG_MERGE_REQUIRED','Existing inline MCP configuration needs an explicit merge; no file was changed.')
        atomic(path,candidate)
    return {'ok':True,'host':args.install_host,'config':str(path),'server':name,'next':'Reload the host and verify tools; configuration alone is not a completed connection.'}

def serve(name,version,tools,dispatch,args):
    def reply(value):sys.stdout.write(json.dumps(value,ensure_ascii=True)+'\n');sys.stdout.flush()
    for line in iter(lambda:sys.stdin.buffer.readline(1000001),b''):
        if len(line)>1000000:raise SystemExit('MCP input exceeds the byte limit.')
        request=None
        try:
            request=json.loads(line.decode('utf-8-sig'));need(isinstance(request,dict) and request.get('jsonrpc')=='2.0','INVALID_REQUEST','Expected JSON-RPC 2.0.')
            method=request.get('method');params=request.get('params',{});need(isinstance(params,dict),'INVALID_REQUEST','params must be an object.')
            if 'id' not in request:continue
            if method=='initialize':result={'protocolVersion':params.get('protocolVersion','2025-11-25') if params.get('protocolVersion') in ['2025-11-25','2025-06-18','2025-03-26','2024-11-05'] else '2025-11-25','capabilities':{'tools':{}},'serverInfo':{'name':name,'version':version},'instructions':'Use the configured private task store. Records and evidence do not grant execution permission. Read current revisions before writes.'}
            elif method=='ping':result={}
            elif method=='tools/list':result={'tools':tools}
            elif method=='tools/call':
                tool=next((x for x in tools if x['name']==params.get('name')),None);need(tool,'UNKNOWN_TOOL','Unknown tool.')
                value=params.get('arguments',{});validate(value,tool['inputSchema'])
                try:
                    data=dispatch(tool['name'],value,args);result={'content':[{'type':'text','text':json.dumps(data)}],'structuredContent':data}
                except (Problem,OSError,sqlite3.Error) as e:result={'isError':True,'content':[{'type':'text','text':json.dumps({'code':getattr(e,'code','STORAGE_ERROR'),'message':str(e)})}]}
            else:
                reply({'jsonrpc':'2.0','id':request['id'],'error':{'code':-32601,'message':'Method not found'}});continue
            reply({'jsonrpc':'2.0','id':request['id'],'result':result})
        except (ValueError,TypeError,KeyError) as e:
            reply({'jsonrpc':'2.0','id':request.get('id') if isinstance(request,dict) else None,'error':{'code':-32602,'message':str(e)}})

def main(name,version,tools,dispatch):
    parser=argparse.ArgumentParser(description='Private local host adapter with CLI and MCP stdio entry points.')
    parser.add_argument('--root',required=True);parser.add_argument('--workspace',default='.');parser.add_argument('--host-id',default='local');parser.add_argument('--subject')
    parser.add_argument('--install-host',choices=['codex','cursor']);parser.add_argument('command',choices=['call','mcp','install']);parser.add_argument('tool',nargs='?');parser.add_argument('--input',default='-')
    args=parser.parse_args()
    try:
        if args.command=='install':need(args.install_host,'HOST_REQUIRED','Choose --install-host codex or cursor.');result=install(args,name,Path(sys.argv[0]).resolve())
        elif args.command=='mcp':return serve(name,version,tools,dispatch,args)
        else:
            tool=next((x for x in tools if x['name']==args.tool),None);need(tool,'UNKNOWN_TOOL','Choose a listed tool.')
            
            if args.input!='-':need(Path(args.input).stat().st_size<=1000000,'INPUT_TOO_LARGE','Input exceeds 1 MB.')
            raw=sys.stdin.read(1000001) if args.input=='-' else Path(args.input).read_text();need(len(raw)<=1000000,'INPUT_TOO_LARGE','Input exceeds 1 MB.');value=json.loads(raw);validate(value,tool['inputSchema']);result=dispatch(args.tool,value,args)
        print(json.dumps(result,indent=2))
    except (Problem,OSError,ValueError,sqlite3.Error) as e:print(json.dumps({'code':getattr(e,'code','ERROR'),'message':str(e)}),file=sys.stderr);return 2
    return 0
