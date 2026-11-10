#!/usr/bin/env python3
"""Prepare frozen scientific inputs from companion assets or the publisher."""
import argparse,hashlib,json,os,shutil,tempfile,urllib.request
from pathlib import Path

def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(4*1024*1024):h.update(b)
 return h.hexdigest()
def prepare(manifest,destination,assets=None):
 config=json.loads(manifest.read_text())
 if assets is None:
  root=next((p for p in manifest.resolve().parents if (p/'benchmark/manifest.jsonl').is_file()),None)
  if root:assets=root.parent/'WorkflowArena-assets'
 checked=0
 for row in config['files']:
  target=destination/row['target']
  if not target.resolve().is_relative_to(destination.resolve()):raise ValueError('Unsafe destination')
  if target.is_file() and target.stat().st_size==row['bytes'] and digest(target)==row['sha256']:
   checked+=1;continue
  candidate=assets/row['asset'] if assets else None
  target.parent.mkdir(parents=True,exist_ok=True)
  with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as f:tmp=Path(f.name)
  try:
   if candidate and candidate.is_file():
    if candidate.stat().st_size!=row['bytes'] or digest(candidate)!=row['sha256']:raise ValueError('Companion input checksum mismatch: '+row['asset'])
    tmp.unlink()
    try:os.link(candidate,tmp)
    except OSError:shutil.copyfile(candidate,tmp)
   else:
    try:
     with urllib.request.urlopen(row['url'],timeout=120) as response,tmp.open('wb') as f:
      while b:=response.read(4*1024*1024):f.write(b)
    except Exception as e:raise RuntimeError('Publisher download unavailable; provide WorkflowArena-assets/'+row['asset']+' from the companion delivery.') from e
   if tmp.stat().st_size!=row['bytes'] or digest(tmp)!=row['sha256']:raise ValueError('Prepared input checksum mismatch: '+row['target'])
   tmp.replace(target);checked+=1
  finally:
   if tmp.exists():tmp.unlink()
 print('Verified',checked,'scientific input files',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--assets-dir',type=Path);a=p.parse_args();prepare(a.manifest,a.destination,a.assets_dir)
