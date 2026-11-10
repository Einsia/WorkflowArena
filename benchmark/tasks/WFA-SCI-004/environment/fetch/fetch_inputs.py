#!/usr/bin/env python3
"""Reconstruct frozen inputs from hash-locked publisher archives, using only stdlib."""
import argparse,collections,hashlib,json,os,tarfile,tempfile,urllib.request,zipfile
from pathlib import Path

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while data:=f.read(4*1024*1024):h.update(data)
 return h.hexdigest()
def prepare(manifest,destination,cache=None):
 destination.mkdir(parents=True,exist_ok=True)
 for source in json.loads(manifest.read_text())['archives']:
  with tempfile.TemporaryDirectory(prefix='workflowarena-source-') as tmp:
   archive=cache/source['archive'] if cache else Path(tmp)/source['archive']
   if not archive.exists():
    archive.parent.mkdir(parents=True,exist_ok=True);download=archive.with_suffix(archive.suffix+'.download')
    with urllib.request.urlopen(source['url'],timeout=180) as response,download.open('wb') as out:
     while data:=response.read(1024*1024):out.write(data)
    download.replace(archive)
   if digest(archive)!=source['sha256']:raise ValueError('Publisher archive checksum mismatch: '+source['archive'])
   groups=collections.defaultdict(list)
   for row in source['files']:groups[row['member']].append(row)
   container=zipfile.ZipFile(archive) if source['format']=='zip' else tarfile.open(archive,'r|*')
   written=set()
   with container:
    for entry in (container.namelist() if source['format']=='zip' else container):
     member=entry if source['format']=='zip' else entry.name
     if member not in groups:continue
     rows=groups[member]
     data=container.read(member) if source['format']=='zip' else container.extractfile(entry).read()
     if source.get('transform')=='pdb-records':data=b''.join(line for line in data.splitlines(keepends=True) if line.startswith((b'ATOM  ',b'HETATM',b'TER',b'END')))
     elif source.get('transform') not in (None,'identity'):raise ValueError('Unsupported input transformation')
     for row in rows:
      if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('Prepared input checksum mismatch: '+row['target'])
      target=destination/row['target']
      if not target.resolve().is_relative_to(destination.resolve()):raise ValueError('Input destination escapes package')
      target.parent.mkdir(parents=True,exist_ok=True)
      with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as out:out.write(data);name=out.name
      os.replace(name,target);written.add(row['target'])
   if written!={row['target'] for row in source['files']}:raise ValueError('Missing archive members')
   print('Prepared',len(source['files']),'inputs from',source['archive'],flush=True)
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True);parser.add_argument('--destination',type=Path,required=True);parser.add_argument('--cache-dir',type=Path);a=parser.parse_args();prepare(a.manifest,a.destination,a.cache_dir)
