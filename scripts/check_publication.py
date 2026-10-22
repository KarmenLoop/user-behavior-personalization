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
for name in data['documents']:
    path=root/name
    text=path.read_text(encoding='utf-8')
    if data['version'] not in text: errors.append('Missing version: '+name)
    for link in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in link or link.startswith(('#','mailto:')): continue
        if not (path.parent/link.split('#',1)[0]).exists(): errors.append('Broken link: '+name+' -> '+link)
for name,digest in data['media_files'].items():
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        errors.append('Media drift: '+name)
for name,digest in data['source_files'].items():
    path=root/name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:
        errors.append('Capture source drift: '+name)
for name in data['documents']+list(data['media_files']):
    if ' ' in name: errors.append('Space in publication filename: '+name)
print(json.dumps({'ok':not errors,'version':data['version'],'errors':errors,'scope':'bilingual documents, version and media identity'},indent=2))
sys.exit(bool(errors))
