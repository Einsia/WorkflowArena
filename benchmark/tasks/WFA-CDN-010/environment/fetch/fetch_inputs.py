#!/usr/bin/env python3
"""Fetch exact publisher files identified by URLs and SHA-256 digests."""
import argparse,hashlib,json,os,tempfile,urllib.request
from pathlib import Path

def prepare(manifest,destination):
 destination.mkdir(parents=True,exist_ok=True)
 for row in json.loads(manifest.read_text())['files']:
  path=destination/row['target']
  if not path.resolve().is_relative_to(destination.resolve()):raise ValueError('Unsafe output path')
  path.parent.mkdir(parents=True,exist_ok=True)
  name=None
  try:
   h=hashlib.sha256()
   with urllib.request.urlopen(urllib.request.Request(row['url'],headers={'User-Agent':'Mozilla/5.0 (compatible; WorkflowArenaSource/1.0)'}),timeout=180) as response,tempfile.NamedTemporaryFile(dir=path.parent,delete=False) as out:
    name=out.name
    while data:=response.read(1024*1024):h.update(data);out.write(data)
   if h.hexdigest()!=row['sha256']:raise ValueError('Publisher file checksum mismatch: '+row['target'])
   os.replace(name,path);name=None
  finally:
   if name:Path(name).unlink(missing_ok=True)
  print('Prepared',row['target'],flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);a=p.parse_args();prepare(a.manifest,a.destination)
