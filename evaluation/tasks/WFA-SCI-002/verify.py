#!/usr/bin/env python3
"""comp-casp15-ema 判分器。

用法:
  python3 verify.py --submission <目录> [--json out.json]
  python3 verify.py --self-check          # 正对照: 用同一代码重算参赛者分数并与官方表比对

提交目录: 每个靶标一个 CASP QA 格式文件 <靶标>.txt (QMODE 1)，每行 `<模型ID> <全局分> <界面分>`，
分数在 [0,1]；界面分可写 X。模型ID 为题面给出的匿名 ID。

指标 (逐靶标，然后对 12 个靶标取平均；与 CASP15 EMA 官方表同定义):
  pearson_TM / spearman_TM : 全局分 vs 模型 TM-score（官方 oligo 表 TMscore 列）
  loss_TM                  : 最高 TM-score − 预测排第一的模型的 TM-score（越低越好）
  pearson_QS / pearson_DockQ: 界面分 vs QS-score(QSbest) / DockQ_Avg（次要指标，官方复现仅近似）
主指标: mean_pearson_TM（有符号 Pearson；官方表取了绝对值，--official-abs 可切换以复现官方表）。
缺失靶标或覆盖 < 80% 模型: 该靶标相关系数记 0，loss 记 max(TM) − mean(TM)。
名次: 在同一靶标子集、同一规则下重算全部 CASP15 EMA 参赛组，名次 = 1 + 严格优于本提交的组数。
"""
import argparse, csv, glob, json, math, os, re, sys
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'reference')
TARGETS = ['H1106','H1129','H1134','H1140','H1144','H1151','H1157','T1109o','T1123o','T1132o','T1153o','T1187o']
MIN_COVER = 0.8

def fnum(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else float('nan')
    except Exception:
        return float('nan')

def load_truth():
    tr = {t: {} for t in TARGETS}
    for r in csv.DictReader(open(os.path.join(REF, 'model_scores.csv'))):
        tr[r['target']][r['anon_id']] = {k: fnum(r[k]) for k in ('TMscore','QSglob','QSbest','DockQ_Avg','lDDToligo')}
    return tr

def parse_qa(path):
    g, i = {}, {}
    for l in open(path, errors='replace'):
        p = l.split()
        if len(p) >= 2 and re.match(r'^[HT]\d{4}o?_M\d{4}$', p[0]):
            g[p[0]] = fnum(p[1]); i[p[0]] = fnum(p[2]) if len(p) > 2 else float('nan')
    return g, i

def corr(fn, x, y, use_abs):
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    r = fn(x, y)[0]
    if not np.isfinite(r): return 0.0
    return abs(r) if use_abs else r

def score_target(truth_t, g, i, use_abs):
    out = {}
    allm = list(truth_t)
    for name, pred, col in (('TM', g, 'TMscore'), ('QS', i, 'QSbest'), ('DockQ', i, 'DockQ_Avg')):
        ms = [m for m in allm if m in pred and np.isfinite(pred[m]) and np.isfinite(truth_t[m][col])]
        avail = [m for m in allm if np.isfinite(truth_t[m][col])]
        yall = np.array([truth_t[m][col] for m in avail])
        cover = len(ms) / max(1, len(avail))
        out[f'coverage_{name}'] = round(cover, 4)
        if cover < MIN_COVER:
            out[f'pearson_{name}'] = 0.0; out[f'spearman_{name}'] = 0.0
            out[f'loss_{name}'] = float(yall.max() - yall.mean()) if len(yall) else float('nan')
            continue
        x = np.array([pred[m] for m in ms]); y = np.array([truth_t[m][col] for m in ms])
        out[f'pearson_{name}'] = corr(stats.pearsonr, x, y, use_abs)
        out[f'spearman_{name}'] = corr(stats.spearmanr, x, y, use_abs)
        out[f'loss_{name}'] = float(y.max() - y[int(np.argmax(x))])
    return out

def score_dir(d, truth, use_abs=False):
    per = {}
    for t in TARGETS:
        f = None
        for ext in ('.txt', '.qa', ''):
            p = os.path.join(d, t + ext)
            if os.path.isfile(p): f = p; break
        g, i = parse_qa(f) if f else ({}, {})
        per[t] = score_target(truth[t], g, i, use_abs)
    keys = [k for k in per[TARGETS[0]] if not k.startswith('coverage')]
    agg = {f'mean_{k}': float(np.mean([per[t][k] for t in TARGETS])) for k in keys}
    agg['n_targets_covered'] = sum(per[t]['coverage_TM'] >= MIN_COVER for t in TARGETS)
    return agg, per

def participants(truth, use_abs=False):
    res = {}
    for d in sorted(glob.glob(os.path.join(REF, 'participants', '*'))):
        res[os.path.basename(d)] = score_dir(d, truth, use_abs)
    return res

def rank(value, others, higher_better=True):
    better = sum(1 for v in others if (v > value + 1e-12 if higher_better else v < value - 1e-12))
    return better + 1

def self_check(truth):
    off = {(r['target'], r['group_id']): r for r in csv.DictReader(open(os.path.join(REF, 'official', 'QA_predictioncenter_oligo-global_fold.csv')))}
    P = participants(truth, use_abs=True)
    diffs = {'pearson_TM': [], 'spearman_TM': [], 'loss_TM': []}
    for gname, (agg, per) in P.items():
        for t in TARGETS:
            o = off.get((t, gname))
            if not o or per[t]['coverage_TM'] < MIN_COVER: continue
            for k in diffs:
                ov = fnum(o[k])
                if np.isfinite(ov): diffs[k].append(abs(per[t][k] - ov))
    rep = {}
    for k, v in diffs.items():
        v = np.array(v)
        rep[k] = {'n': int(len(v)), 'max_abs_diff': float(v.max()), 'median_abs_diff': float(np.median(v)),
                  'frac_within_0.005': float(np.mean(v <= 0.005)), 'frac_within_0.02': float(np.mean(v <= 0.02))}
    return rep

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--submission'); ap.add_argument('--json'); ap.add_argument('--official-abs', action='store_true')
    ap.add_argument('--self-check', action='store_true')
    a = ap.parse_args()
    truth = load_truth()
    if a.self_check:
        rep = self_check(truth); print(json.dumps(rep, indent=1))
        if a.json: json.dump(rep, open(a.json, 'w'), indent=1)
        return
    agg, per = score_dir(a.submission, truth, a.official_abs)
    P = participants(truth, a.official_abs)
    sub_dir = os.path.abspath(a.submission)
    # 若提交本身就是某参赛组(正对照)，名次比较时排除自身
    others = {g: v for g, v in P.items() if os.path.abspath(os.path.join(REF, 'participants', g)) != sub_dir}
    res = {'aggregate': agg, 'per_target': per, 'n_participants': len(others)}
    res['rank_pearson_TM'] = rank(agg['mean_pearson_TM'], [v[0]['mean_pearson_TM'] for v in others.values()])
    res['rank_loss_TM'] = rank(agg['mean_loss_TM'], [v[0]['mean_loss_TM'] for v in others.values()], higher_better=False)
    res['rank_pearson_QS'] = rank(agg['mean_pearson_QS'], [v[0]['mean_pearson_QS'] for v in others.values()])
    res['leaderboard_pearson_TM'] = sorted(((g, round(v[0]['mean_pearson_TM'], 4)) for g, v in others.items()), key=lambda x: -x[1])
    print(f"mean_pearson_TM={agg['mean_pearson_TM']:.4f}  rank={res['rank_pearson_TM']}/{len(others)+1}")
    print(f"mean_loss_TM={agg['mean_loss_TM']:.4f}  rank={res['rank_loss_TM']}/{len(others)+1}")
    print(f"mean_pearson_QS={agg['mean_pearson_QS']:.4f}  rank={res['rank_pearson_QS']}/{len(others)+1}")
    print(f"targets covered: {agg['n_targets_covered']}/{len(TARGETS)}")
    if a.json: json.dump(res, open(a.json, 'w'), indent=1)

if __name__ == '__main__':
    main()
