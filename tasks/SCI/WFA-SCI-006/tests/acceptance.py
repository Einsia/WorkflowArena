#!/usr/bin/env python3
"""Apply the fixed paper acceptance baseline independently of continuous reward."""
import argparse,json,math
from pathlib import Path

def value(obj,path):
 for key in path.split('.'):
  if not isinstance(obj,dict) or key not in obj:raise ValueError('Missing grading evidence: '+path)
  obj=obj[key]
 return obj
def number(x):return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def evaluate(rule,details,valid):
 if valid is not True or details.get('valid') is False or details.get('complete') is False:return {'passed':False,'reason':'invalid_or_incomplete_submission'}
 coverage=rule.get('coverage')
 if coverage:
  if value(details,coverage['metric'])!=coverage['required']:return {'passed':False,'reason':'required_targets_not_covered'}
  if coverage.get('invalid_ids'):
   ids=value(details,coverage['invalid_ids'])
   if not isinstance(ids,dict):raise ValueError('Invalid coverage evidence')
   if any(ids.values()):return {'passed':False,'reason':'invalid_model_identifiers'}
 checks=[]
 def check(path,op,threshold):
  result=value(details,path)
  if not number(result):raise ValueError('Nonfinite or missing metric: '+path)
  if op not in ['le','ge']:raise ValueError('Unsupported metric comparison')
  checks.append({'metric':path,'value':result,'threshold':threshold,'operator':op,'passed':result<=threshold if op=='le' else result>=threshold})
 if rule.get('thresholds'):
  for metric,spec in rule['thresholds'].items():
   if len(spec)!=1:raise ValueError('Ambiguous baseline')
   op,threshold=next(iter(spec.items()));check(rule['metric']+'.'+metric,op,threshold)
 elif rule['operator']=='lex_ge':
  values=[value(details,p) for p in rule['metric']]
  if not all(number(x) for x in values):raise ValueError('Nonfinite metric')
  checks.append({'metric':rule['metric'],'value':values,'threshold':rule['threshold'],'operator':'lex_ge','passed':tuple(values)>=tuple(rule['threshold'])})
 else:check(rule['metric'],rule['operator'],rule['threshold'])
 return {'passed':all(c['passed'] for c in checks),'reason':'fixed_task_baseline','checks':checks}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--rule',type=Path,default=Path(__file__).with_name('acceptance.json'));parser.add_argument('--log-dir',type=Path,default=Path('/logs/verifier'));a=parser.parse_args();log=a.log_dir
 try:
  rule=json.loads(a.rule.read_text());reward=json.loads((log/'reward.json').read_text());valid=reward.get('valid')
  if valid not in [True,False,0,1]:raise ValueError('Missing validity evidence')
  details=json.loads((log/'details.json').read_text()) if (log/'details.json').exists() else {}
  result=evaluate(rule,details,bool(valid));reward.update(full_success=result['passed'],score=100*reward['reward']);details['acceptance']=result
  (log/'reward.json').write_text(json.dumps(reward,indent=2)+'\n');(log/'details.json').write_text(json.dumps(details,indent=2)+'\n');(log/'acceptance.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(reward))
 except (OSError,ValueError,KeyError,TypeError) as error:
  for name in ['reward.txt','reward.json']:(log/name).unlink(missing_ok=True)
  (log/'grading_error.json').write_text(json.dumps({'error':str(error),'task_pass_recorded':False})+'\n');raise SystemExit(1)
if __name__=='__main__':main()
