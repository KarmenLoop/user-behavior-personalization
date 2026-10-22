#!/usr/bin/env python3
"""Package one clean committed source with both languages and legal notices."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

root=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,required=True,help='New directory outside the repository')
args=parser.parse_args()
target=args.output.expanduser().resolve()
if target.exists() or target==root or root in target.parents:parser.error('choose a new output directory outside the source tree')
if subprocess.check_output(['git','status','--porcelain'],cwd=root).strip():parser.error('commit changes before packaging')
subprocess.run([sys.executable,'-B','scripts/check_publication.py'],cwd=root,check=True)
version=(root/'VERSION').read_text().strip()
name='user-behavior-personalization'
stem=name+'-v'+version
target.mkdir(parents=True)
archive=target/(stem+'.zip')
names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as output:
    for filename in sorted(filter(None,names)):output.write(root/filename,stem+'/'+filename)
assets=[archive]

receipt={'version':version,'commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=root).decode().strip(),'artifacts':[]}
for asset in assets:
    with zipfile.ZipFile(asset) as output:assert output.testzip() is None
    receipt['artifacts'].append({'file':asset.name,'bytes':asset.stat().st_size,'sha256':hashlib.sha256(asset.read_bytes()).hexdigest()})
(target/'SHA256SUMS.txt').write_text(''.join(x['sha256']+'  '+x['file']+'\n' for x in receipt['artifacts']))
(target/'release-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
print(json.dumps(receipt,indent=2))
