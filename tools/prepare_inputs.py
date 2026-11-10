#!/usr/bin/env python3
"""Hydrate publisher-fetched inputs and verify the frozen output hashes."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path

def digest(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  while chunk:=f.read(4*1024*1024):h.update(chunk)
 return h.hexdigest()
def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
 parser.add_argument('--tasks',nargs='+',help='Restrict to canonical task IDs')
 parser.add_argument('--check-only',action='store_true')
 parser.add_argument('--assets-dir',type=Path,help='Companion asset directory; defaults to ../WorkflowArena-assets')
 args=parser.parse_args();root=args.root.resolve()
 hashes={r['path']:r['sha256'] for r in map(json.loads,(root/'provenance/files.jsonl').read_text().splitlines())}
 tasks=[json.loads(l) for l in (root/'tasks/manifest.jsonl').read_text().splitlines()]
 if args.tasks and set(args.tasks)-{r['task_id'] for r in tasks}:parser.error('Unknown task ID')
 outcomes=[]
 for row in tasks:
  if args.tasks and row['task_id'] not in args.tasks:continue
  task=root/row['path']
  for manifest in sorted(task.glob('*/fetch/sources.json')):
   config=json.loads(manifest.read_text());destination=manifest.parent.parent/config.get('destination','inputs')
   files=config.get('files',[])+[f for a in config.get('archives',[]) for f in a['files']]
   def missing():
    bad=[]
    for f in files:
     p=destination/f['target'];key=str(p.relative_to(root))
     if not p.resolve().is_relative_to(root):raise ValueError('Unsafe manifest path')
     if not p.is_file() or digest(p)!=hashes[key]:bad.append(f['target'])
    return bad
   bad=missing()
   if bad and not args.check_only:
    command=[sys.executable,'-B',str(manifest.with_name('fetch_inputs.py')),'--manifest',str(manifest),'--destination',str(destination)]
    if config.get('distribution')=='companion-assets':command+=['--assets-dir',str((args.assets_dir or root.parent/'WorkflowArena-assets').resolve())]
    subprocess.run(command,check=True)
    bad=missing()
   outcomes.append({'task_id':row['task_id'],'context':manifest.parent.parent.name,'files':len(files),'passed':not bad,'missing_or_changed':bad})
 print(json.dumps(outcomes,indent=2));return all(r['passed'] for r in outcomes)
if __name__=='__main__':sys.exit(not main())
