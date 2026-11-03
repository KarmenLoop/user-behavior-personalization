#!/usr/bin/env python3
"""Check the current bilingual publication and its bound media."""
import hashlib
import json
from pathlib import Path
import re
import sys

root=Path(__file__).resolve().parents[1]
data=json.loads((root/'publication.json').read_text(encoding='utf-8'))
errors=[]
expected_sources={path.relative_to(root).as_posix() for path in (root/'scripts').rglob('*.py') if path.is_file()}
expected_sources.update(path.relative_to(root).as_posix() for path in (root/'web').rglob('*') if path.is_file() and path.suffix in {'.js','.css','.html'})
expected_media={path.relative_to(root).as_posix() for path in (root/'docs/images').rglob('*') if path.is_file() and path.suffix.lower() in {'.svg','.jpg'}}
for field,expected in [('source_files',expected_sources),('media_files',expected_media)]:
    declared=set(data[field])
    for name in sorted(expected-declared): errors.append('Missing '+field+' hash: '+name)
    for name in sorted(declared-expected): errors.append('Unexpected '+field+' entry: '+name)
if data['version'] != (root/'VERSION').read_text(encoding='utf-8').strip():
    errors.append('Publication version does not match VERSION')
host_text=(root/'scripts/host.py').read_text(encoding='utf-8')
if "main('user_behavior_personalization', '"+data['version']+"'" not in host_text:
    errors.append('Host server version does not match publication')
for name in data['documents']:
    path=root/name
    text=path.read_text(encoding='utf-8')
    if data['version'] not in text: errors.append('Missing version: '+name)
    for link in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in link or link.startswith(('#','mailto:')): continue
        if not (path.parent/link.split('#',1)[0]).exists(): errors.append('Broken link: '+name+' -> '+link)
for name,digest in data['media_files'].items():
    if name not in expected_media: continue
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        errors.append('Media drift: '+name)
for name,digest in data['source_files'].items():
    if name not in expected_sources: continue
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        errors.append('Capture source drift: '+name)
for name in data['documents']+list(data['media_files'])+list(data['source_files']):
    if ' ' in name: errors.append('Space in publication filename: '+name)
print(json.dumps({'ok':not errors,'version':data['version'],'errors':errors,'scope':'bilingual documents, version, complete Python/web source coverage and media identity'},indent=2))
sys.exit(bool(errors))
