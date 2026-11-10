#!/usr/bin/env python3
"""comp-kaggle-champs 判分器。
用法: python3 verify.py --submission submission.csv --truth <data_test.csv(.gz)> [--json out.json]
 - truth: 组织方公开的测试集真值 data_test.csv（tests/reference/data_test.csv.gz）
指标（官方）: 8 种耦合类型上 log(max(MAE_type, 1e-9)) 的平均（越低越好）。
名次:
 (a) 主: 与组织方对前 400 队最终提交的逐类型分数表(top400_scores_organizer_half_split.csv，文件名沿用但实为组织方 analysis/blend.py 的分层 50% 测试划分:
     train_test_split(stratify=type, test_size=0.5, random_state=42)，id 列表见 organizer_half_split_ids.txt.gz；每类列 = log(MAE+1e-9)/8) 比较，名次在该半集上计算；
     主分数仍报告完整测试集上的官方指标；
 固定参考总体为上述 400 队；不同测试划分的排行榜不参与评分。
"""
import argparse, csv, gzip, json, math, os, sys
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
TYPES = ['1JHC','1JHN','2JHH','2JHC','2JHN','3JHH','3JHC','3JHN']

def score(sub, truth, ids=None):
    t = pd.read_csv(truth, usecols=['id','type','scalar_coupling_constant'])
    s = pd.read_csv(sub)
    if set(s.columns) != {'id','scalar_coupling_constant'}: raise SystemExit('bad columns: %s' % list(s.columns))
    if s['id'].duplicated().any(): raise SystemExit('duplicate ids')
    m = t.merge(s, on='id', how='left', suffixes=('_true','_pred'))
    missing = int(m['scalar_coupling_constant_pred'].isna().sum())
    if missing: raise SystemExit(f'{missing} test ids missing from submission')
    if not np.isfinite(m['scalar_coupling_constant_pred']).all(): raise SystemExit('non-finite predictions')
    if ids is not None: m = m[m['id'].isin(ids)]
    per = {}
    for ty in TYPES:
        g = m[m['type']==ty]
        mae = float(np.mean(np.abs(g['scalar_coupling_constant_true']-g['scalar_coupling_constant_pred'])))
        per[ty] = math.log(max(mae, 1e-9)) if ids is None else math.log(mae + 1e-9)
    return float(np.mean(list(per.values()))), per

def load_top400():
    rows = []
    with open(os.path.join(HERE,'reference','top400_scores_organizer_half_split.csv')) as f:
        r = csv.reader(f, skipinitialspace=True); hdr = next(r)
        for x in r:
            if not x or x[0].startswith('E'): continue
            d = dict(zip(hdr, x)); rows.append((int(d['rank']), d['name'], float(d['scores(total)']),
                     {ty: float(d[f'score({ty})']) * 8.0 for ty in TYPES}))
    return rows

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--submission', required=True)
    ap.add_argument('--truth', default=os.path.join(HERE,'reference','data_test.csv.gz')); ap.add_argument('--json')
    ap.add_argument('--exclude-rank', type=int, default=None, help='正对照时排除该队自身')
    a = ap.parse_args()
    tot, per = score(a.submission, a.truth)
    half = set(int(x) for x in gzip.open(os.path.join(HERE,'reference','organizer_half_split_ids.txt.gz'),'rt').read().split())
    tot_h, per_h = score(a.submission, a.truth, half)
    top = [r for r in load_top400() if r[0] != a.exclude_rank]
    rank400 = 1 + sum(1 for r in top if r[2] < tot_h)
    per_type_rank = {ty: 1 + sum(1 for r in top if r[3][ty] < per_h[ty]) for ty in TYPES}
    res = {'score_mean_log_mae': tot, 'per_type_log_mae': per, 'score_organizer_half_split': tot_h, 'per_type_half_split': per_h, 'rank_among_top400_half_split': rank400,
           'n_top400': len(top),
           'per_type_rank_among_top400': per_type_rank,
           'note': '参考总体固定为组织方同一半集上的 400 队；连续分为严格超过的参考队伍比例'}
    print(f'score(mean log MAE)={tot:.4f}  half-split={tot_h:.4f} rank(top400, organizer half split)={rank400}/{len(top)+1}')
    print('per type:', {k: round(v,3) for k,v in per.items()})
    if a.json: json.dump(res, open(a.json,'w'), indent=1)

if __name__ == '__main__': main()
