#!/usr/bin/env python3
"""Emit the paper's continuous reward separately from task acceptance."""
import json,math,sys
from pathlib import Path

def number(record,key):
 value=float(record[key])
 if not math.isfinite(value):raise ValueError('Nonfinite metric: '+key)
 return value
def fraction(record,key):
 value=number(record,key)
 if not 0<=value<=1:raise ValueError('Out-of-range fraction: '+key)
 return value
def normalize(form,record,coverage=None):
 out=dict(record);native=fraction(record,'reward')
 if form.startswith('OPS-'):
  ratios=[]
  for group in ['G','P','F']:
   total=number(record,group+'_total');passed=number(record,group+'_passed')
   if total<=0 or not 0<=passed<=total:raise ValueError('Invalid check counts: '+group)
   ratios.append(passed/total)
  reward=math.prod(ratios);full=ratios[0]>=.9 and ratios[1]>=.9 and ratios[2]==1 and not record.get('intermediate_failure',0)
 elif form=='FIN-ACCT':
  total=number(record,'hard_checks_total') if 'hard_checks_total' in record else 0
  if total<0:raise ValueError('Invalid hard-check count')
  hard=number(record,'hard_checks_passed')/total if total else 1.0
  if not 0<=hard<=1:raise ValueError('Invalid hard-check fraction')
  reward=hard*(fraction(record,'branch_score')+fraction(record,'merge_score'))/2;full=bool(record['full_success'])
 elif form.startswith('LAW-'):
  reward=(fraction(record,'branch_score')+fraction(record,'merge_score'))/2;full=bool(record['full_success'])
 elif form.startswith('MATH-'):
  clean=bool(record['build_ok']) and not record.get('forbidden_hits',0)
  reward=fraction(record,'fraction') if clean else 0.0;full=bool(native)
 elif form=='SWE-FEAT':
  clean=bool(record['build_ok']) and not record.get('tampered',0)
  reward=fraction(record,'pass_fraction') if clean else 0.0;full=bool(native)
  if coverage is not None:
   passed=number(record,'passed');skipped=number(record,'skipped')
   full=full and passed>=coverage['reference_passed'] and skipped<=coverage['reference_skipped'] and passed+skipped>=coverage['reference_total']
 else:raise ValueError('Unsupported score form')
 out.update(native_reward=native,reward=reward,score=100*reward,normalized_score=reward,partial_score=reward,full_success=full)
 return out

def main():
 logs=Path('/logs/verifier');reward=logs/'reward.json';text=logs/'reward.txt'
 try:
  if len(sys.argv)>2 and int(sys.argv[2])!=0:raise ValueError('Native evaluator exited with an error')
  coverage=json.loads(Path(__file__).with_name('coverage.json').read_text()) if sys.argv[1]=='SWE-FEAT' else None
  out=normalize(sys.argv[1],json.loads(reward.read_text()),coverage)
  reward.write_text(json.dumps(out,indent=2,allow_nan=False)+'\n');text.write_text(str(out['reward'])+'\n')
 except Exception as e:
  reward.unlink(missing_ok=True);text.unlink(missing_ok=True)
  (logs/'grading_error.json').write_text(json.dumps({'stage':'paper_score','error':str(e)})+'\n');raise
 print(json.dumps(out))
if __name__=='__main__':main()
