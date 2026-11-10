#!/usr/bin/env python3
"""Verify a WorkflowArena delivery without importing task or evaluator code."""
import argparse,collections,hashlib,json,sys,tomllib
from pathlib import Path
EXPECTED={'SWE':17,'OPS':18,'SCI':16,'MATH':24,'FIN':16,'LAW':22,'CDN':14,'3D':18}
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while chunk:=f.read(4*1024*1024):h.update(chunk)
 return h.hexdigest()
def verify(root):
 errors=[];rows=[json.loads(line) for line in (root/'tasks/manifest.jsonl').read_text().splitlines()]
 if len(rows)!=145 or dict(collections.Counter(r['domain'] for r in rows))!=EXPECTED:errors.append('Task/domain counts differ from the paper.')
 ids={f'WFA-{d}-{i:03d}' for d,n in EXPECTED.items() for i in range(1,n+1)}
 if {r['task_id'] for r in rows}!=ids:errors.append('Task IDs are incomplete or noncanonical.')
 if len({r['task_form'] for r in rows})!=17:errors.append('Expected 17 task forms.')
 for row in rows:
  p=root/row['path']
  if not p.resolve().is_relative_to(root.resolve()):errors.append('Task path escapes dataset.');continue
  cfg=tomllib.loads((p/'task.toml').read_text());meta=json.loads((p/'metadata.json').read_text())
  if cfg['task']['name']!=row['task_id'] or meta['task_id']!=row['task_id']:errors.append(row['task_id']+': inconsistent identity')
  if cfg['agent']['timeout_sec']!=14400 or meta['budget_seconds']!=14400:errors.append(row['task_id']+': inconsistent budget')
 files=0;listed=set()
 for line in (root/'provenance/files.jsonl').read_text().splitlines():
  record=json.loads(line);p=root/record['path'];files+=1
  if record['path'] in listed:errors.append('Duplicate checksum record: '+record['path'])
  listed.add(record['path'])
  if not p.resolve().is_relative_to(root.resolve()):errors.append('File path escapes dataset.');continue
  if not p.is_file() or p.stat().st_size!=record['bytes'] or digest(p)!=record['sha256']:errors.append(record['path']+': missing or checksum mismatch')
 actual={str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() and '.git' not in p.relative_to(root).parts}
 for extra in sorted(actual-listed-{'provenance/files.jsonl'}):errors.append(extra+': unmanifested file')
 return {'tasks':len(rows),'files_checked':files,'passed':not errors,'errors':errors}
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);args=parser.parse_args()
 result=verify(args.root);print(json.dumps(result,indent=2));sys.exit(not result['passed'])
