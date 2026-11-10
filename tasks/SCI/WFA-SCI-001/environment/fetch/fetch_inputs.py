#!/usr/bin/env python3
"""Restore exact frozen docking models from the original publisher archive.

The manifest stores model selection, rigid coordinate transforms and corrections
for PDB decimal rounding. Every restored model must match its frozen SHA-256.
"""
import argparse,hashlib,json,os,tarfile,tempfile,urllib.request
from pathlib import Path

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while data:=f.read(4*1024*1024):h.update(data)
 return h.hexdigest()
def models(stream):
 ident=None;lines=[]
 for line in stream:
  if line.startswith(b'MODEL '):ident=None;lines=[]
  elif line.startswith(b'REMARK   4 FROM '):ident=line.split()[3].decode()
  elif line.startswith((b'ATOM  ',b'HETATM')):lines.append(line)
  elif line.startswith(b'ENDMDL'):
   if ident is not None:yield ident,lines
   ident=None;lines=[]
def reconstruct(raw,record):
 matrix=record['matrix'];fixes={int(k):v for k,v in record['rounding'].items()};chains=set(record['chains']);out=[]
 lines=[line for line in raw if line[21:22].decode() in chains]
 for i,line in enumerate(lines):
  x=[float(line[30:38]),float(line[38:46]),float(line[46:54]),1.0]
  xyz=[sum(x[j]*matrix[j][k] for j in range(4)) for k in range(3)]
  field=fixes.get(i,''.join(f'{v:8.3f}' for v in xyz))
  out.extend(v.encode() for v in record['separators'].get(str(i),[]))
  out.append(line[:30]+field.encode()+line[54:])
 out.extend(v.encode() for v in record['separators'].get(str(len(lines)),[]))
 return b''.join(out)
def prepare(manifest,destination,cache=None,verify_only=False):
 source=json.loads(manifest.read_text())['archives'][0]
 if not verify_only:
  valid=True
  for row in source['files']:
   target=destination/row['target']
   if not target.resolve().is_relative_to(destination.resolve()):raise ValueError('Unsafe output path')
   if not target.is_file() or digest(target)!=row['sha256']:valid=False;break
  if valid:
   print('Verified',len(source['files']),'prepared models',flush=True);return
 with tempfile.TemporaryDirectory(prefix='workflowarena-capri-') as tmp:
  archive=(cache or Path(tmp))/source['archive']
  if not archive.exists():
   archive.parent.mkdir(parents=True,exist_ok=True);download=archive.with_suffix(archive.suffix+'.download')
   with urllib.request.urlopen(source['url'],timeout=180) as response,download.open('wb') as out:
    while data:=response.read(4*1024*1024):out.write(data)
   download.replace(archive)
  if digest(archive)!=source['sha256']:raise ValueError('Publisher archive checksum mismatch')
  groups={};written=set()
  for row in source['files']:groups.setdefault(row['member'],{})[row['identification']]=row
  with tarfile.open(archive,'r|bz2') as tar:
   for member in tar:
    if member.name not in groups:continue
    records=groups[member.name]
    for ident,lines in models(tar.extractfile(member)):
     if ident not in records:continue
     record=records[ident];data=reconstruct(lines,record)
     if hashlib.sha256(data).hexdigest()!=record['sha256']:raise ValueError('Prepared model checksum mismatch: '+record['target'])
     target=destination/record['target']
     if not target.resolve().is_relative_to(destination.resolve()):raise ValueError('Unsafe output path')
     if not verify_only:
      target.parent.mkdir(parents=True,exist_ok=True)
      with tempfile.NamedTemporaryFile(dir=target.parent,delete=False) as out:out.write(data);name=out.name
      os.replace(name,target)
     written.add(record['target'])
    print('Prepared',len(records),'models from',member.name,flush=True)
  if written!={r['target'] for r in source['files']}:raise ValueError('Missing model records')
  print('Verified',len(written),'exact models',flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--manifest',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--cache-dir',type=Path);p.add_argument('--verify-only',action='store_true');a=p.parse_args();prepare(a.manifest,a.destination,a.cache_dir,a.verify_only)
