#!/usr/bin/env python3
"""comp-casp16-ema 判分器。

用法:
  python3 verify.py --submission <目录> [--json out.json]
  python3 verify.py --self-check [--json out.json]   # 正对照: 用同一代码重算全部参赛者，与官方逐靶标表比对

提交目录: 每个靶标一个 CASP QA 格式文件 <靶标>.txt (QMODE 1)，模型行 `<模型ID> <全局分> <界面分>`，
分数在 [0,1]；界面分可写 X。模型ID 为题面给出的匿名 ID（如 H1215_M0001）。

指标 (逐靶标，再对 12 个靶标取平均；与 CASP16 EMA 官方 qa_global_fold / qa_global_iface 表同定义):
  pearson_TM / spearman_TM : 全局分 vs 模型 TM-score（官方 CASP16_prot_oligo.scores.csv 的 TMscore 列）
  loss_TM                  : max(TM) − 预测排第一的模型的 TM（越低越好）
  pearson_DockQ / loss_DockQ: 界面分 vs DockQ_Avg
  pearson_QS               : 界面分 vs QSbest
CASP16 官方表使用有符号 Pearson/Spearman（与 CASP15 不同，未取绝对值），本判分器同样用有符号值。
官方 AUC 列的定义未能复现，不纳入判分。
缺失靶标或覆盖 < 80% 模型: 该靶标相关记 0，loss 记 max − mean。
名次: 在同一靶标子集、同一代码下重算参赛组。默认比较集 = 官方全局表（qa_global_fold avg）中排名的 23 个参赛组
(全局指标) / 官方界面表中排名的组 (界面指标)；另报告对全部 33 份参赛文件的名次。
名次 = 1 + 严格优于本提交的组数。
"""
import argparse, csv, glob, json, math, os, re
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'reference')
TARGETS = ['H1215','H1223','H1230','H1232','H1236','H1244','H1245','T1201o','T1234o','T1235o','T1259o','T1298o']
MIN_COVER = 0.8
METRICS = (('TM', 'g', 'TMscore'), ('DockQ', 'i', 'DockQ_Avg'), ('QS', 'i', 'QSbest'))

def fnum(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else float('nan')
    except Exception:
        return float('nan')

def load_truth():
    tr = {t: {} for t in TARGETS}
    for r in csv.DictReader(open(os.path.join(REF, 'model_scores.csv'))):
        tr[r['target']][r['anon_id']] = {k: fnum(r[k]) for k in ('TMscore', 'QSbest', 'DockQ_Avg')}
    return tr

def parse_qa(path):
    g, i = {}, {}
    for l in open(path, errors='replace'):
        p = l.split()
        if len(p) >= 2 and re.match(r'^[HT]\d{4}o?_M\d{4}$', p[0]):
            g[p[0]] = fnum(p[1]); i[p[0]] = fnum(p[2]) if len(p) > 2 else float('nan')
    return g, i

def corr(fn, x, y):
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    r = fn(x, y)[0]
    return float(r) if np.isfinite(r) else 0.0

def score_target(truth_t, g, i):
    out = {}
    for name, which, col in METRICS:
        pred = g if which == 'g' else i
        avail = [m for m in truth_t if np.isfinite(truth_t[m][col])]
        ms = [m for m in avail if m in pred and np.isfinite(pred[m])]
        yall = np.array([truth_t[m][col] for m in avail])
        cover = len(ms) / max(1, len(avail))
        out[f'coverage_{name}'] = round(cover, 4)
        if cover < MIN_COVER:
            out[f'pearson_{name}'] = 0.0; out[f'spearman_{name}'] = 0.0
            out[f'loss_{name}'] = float(yall.max() - yall.mean()) if len(yall) else float('nan')
            continue
        x = np.array([pred[m] for m in ms]); y = np.array([truth_t[m][col] for m in ms])
        out[f'pearson_{name}'] = corr(stats.pearsonr, x, y)
        out[f'spearman_{name}'] = corr(stats.spearmanr, x, y)
        out[f'loss_{name}'] = float(y.max() - y[int(np.argmax(x))])
    return out

def find_file(d, t):
    for ext in ('.txt', '.qa', ''):
        p = os.path.join(d, t + ext)
        if os.path.isfile(p):
            return p
    return None

def score_dir(d, truth):
    per = {}
    for t in TARGETS:
        f = find_file(d, t)
        g, i = parse_qa(f) if f else ({}, {})
        per[t] = score_target(truth[t], g, i)
    keys = [k for k in per[TARGETS[0]] if not k.startswith('coverage')]
    agg = {f'mean_{k}': float(np.mean([per[t][k] for t in TARGETS])) for k in keys}
    agg['n_targets_covered'] = int(sum(per[t]['coverage_TM'] >= MIN_COVER for t in TARGETS))
    return agg, per

def participants(truth):
    return {os.path.basename(d): score_dir(d, truth) for d in sorted(glob.glob(os.path.join(REF, 'participants', '*')))}

def official_ranked(kind):
    s = set()
    for r in csv.DictReader(open(os.path.join(REF, 'official', f'casp16_qa_global_{kind}.csv'))):
        if r['target'] == 'avg' and r['group_id'] != '0':
            s.add(r['group_id'])
    return s

def rank(value, others, higher_better=True):
    return 1 + sum(1 for v in others if (v > value + 1e-12 if higher_better else v < value - 1e-12))

def self_check(truth):
    P = participants(truth)
    rep = {}
    for kind, pairs in (('fold', [('pearson_TM', 'Pears_TM'), ('spearman_TM', 'Spear_TM'), ('loss_TM', 'Loss_TM')]),
                        ('iface', [('pearson_DockQ', 'Pears_DockQ'), ('spearman_DockQ', 'Spear_DockQ'), ('loss_DockQ', 'Loss_DOckQ'),
                                   ('pearson_QS', 'Pears_QS'), ('spearman_QS', 'Spear_QS')])):
        off = {(r['target'], r['group_id']): r for r in csv.DictReader(open(os.path.join(REF, 'official', f'casp16_qa_global_{kind}.csv')))}
        for ours, theirs in pairs:
            cov = 'coverage_' + ours.split('_')[1]
            diffs = []
            for gid, (agg, per) in P.items():
                for t in TARGETS:
                    o = off.get((t, gid))
                    if not o or per[t][cov] < MIN_COVER: continue
                    ov = fnum(o[theirs])
                    if np.isfinite(ov): diffs.append(abs(per[t][ours] - ov))
            v = np.array(diffs)
            rep[ours] = {'official_column': theirs, 'n': int(len(v)), 'max_abs_diff': float(v.max()), 'median_abs_diff': float(np.median(v)),
                         'frac_within_0.005': float(np.mean(v <= 0.005)), 'frac_within_0.02': float(np.mean(v <= 0.02))}
    # 子集平均的官方值 vs 本代码：对官方逐靶标值在 12 个靶标上取平均（仅比较 12 个靶标均有官方值的组）
    off = {(r['target'], r['group_id']): r for r in csv.DictReader(open(os.path.join(REF, 'official', 'casp16_qa_global_fold.csv')))}
    sub = {}
    for gid, (agg, per) in P.items():
        vals = [fnum(off[(t, gid)]['Pears_TM']) if (t, gid) in off else float('nan') for t in TARGETS]
        if all(np.isfinite(vals)):
            sub[gid] = {'official_subset_mean_pearson_TM': round(float(np.mean(vals)), 4), 'verify_mean_pearson_TM': round(agg['mean_pearson_TM'], 4)}
    rep['subset_means'] = sub
    return rep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--submission'); ap.add_argument('--json'); ap.add_argument('--self-check', action='store_true')
    a = ap.parse_args()
    truth = load_truth()
    if a.self_check:
        rep = self_check(truth); print(json.dumps(rep, indent=1))
        if a.json: json.dump(rep, open(a.json, 'w'), indent=1)
        return
    if not a.submission:
        ap.error('--submission required')
    agg, per = score_dir(a.submission, truth)
    P = participants(truth)
    sub_dir = os.path.realpath(a.submission)
    # 若提交本身就是某参赛组目录(正对照)，名次比较时排除自身
    P = {g: v for g, v in P.items() if os.path.realpath(os.path.join(REF, 'participants', g)) != sub_dir}
    fold_set = {g: v for g, v in P.items() if g in official_ranked('fold')}
    iface_set = {g: v for g, v in P.items() if g in official_ranked('iface')}
    res = {'aggregate': agg, 'per_target': per, 'n_official_fold_groups': len(fold_set), 'n_official_iface_groups': len(iface_set), 'n_all_participant_files': len(P)}
    for key, hb, pool, label in (('mean_pearson_TM', True, fold_set, 'fold'), ('mean_spearman_TM', True, fold_set, 'fold'),
                                 ('mean_loss_TM', False, fold_set, 'fold'), ('mean_pearson_DockQ', True, iface_set, 'iface'),
                                 ('mean_loss_DockQ', False, iface_set, 'iface'), ('mean_pearson_QS', True, iface_set, 'iface')):
        res[f'rank_{key}'] = rank(agg[key], [v[0][key] for v in pool.values()], hb)
        res[f'rank_{key}_of'] = len(pool) + 1
        res[f'rank_{key}_all_files'] = rank(agg[key], [v[0][key] for v in P.values()], hb)
    res['leaderboard_pearson_TM'] = sorted(((g, round(v[0]['mean_pearson_TM'], 4)) for g, v in fold_set.items()), key=lambda x: -x[1])
    for key in ('mean_pearson_TM', 'mean_spearman_TM', 'mean_loss_TM', 'mean_pearson_DockQ', 'mean_loss_DockQ', 'mean_pearson_QS'):
        print(f"{key}={agg[key]:.4f}  rank={res['rank_' + key]}/{res['rank_' + key + '_of']}  (all files: {res['rank_' + key + '_all_files']}/{len(P) + 1})")
    print(f"targets covered: {agg['n_targets_covered']}/{len(TARGETS)}")
    if a.json: json.dump(res, open(a.json, 'w'), indent=1)

if __name__ == '__main__':
    main()
