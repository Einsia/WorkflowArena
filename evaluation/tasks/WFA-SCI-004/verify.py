#!/usr/bin/env python3
"""comp-dream5-network-inference 判分器（DREAM5 Network Inference 官方 MATLAB 评分的 Python 移植）。

用法:
  python3 verify.py --submission <目录> [--json out.json] [--name 名字]
  python3 verify.py --self-check <Supp3 Network_predictions 目录> [--json out.json]
      正对照: 用本代码重算全部 35 个方法 + community 的提交，与官方 Supp Data 2 表逐项比对

提交目录: 每个网络一个文件 Network{1,2,3,4}.txt（也接受 DREAM5_NetworkInference_<x>_Network{k}.txt），
每行 `TF<TAB>target<TAB>confidence`，基因用题面给出的匿名 ID（G1, G2, ...）。行序即排名（与官方脚本一致，
置信度列不参与计算，但必须非增）。每个文件最多 100000 行，超出部分截断。

逐网络指标（与官方 DREAM5_Challenge4_Evaluation.m 完全同算法）:
  - 评分全集 = 金标中出现的调控因子 × 金标中出现的全部基因（去掉自环）；正例 = 金标边，其余为负例；
  - 预测中不在全集内的边被丢弃（官方 remove_edges_not_in_gs）；列表未覆盖的部分按随机补全；
  - AUROC = trapz(FPR,TPR)；AUPR = trapz(REC,PREC)/(1-1/P)；
  - p 值 = P(null >= 观测值)，null 为官方提供的概率密度（Network{1,3,4}_{AUPR,AUROC}.mat）。
总分（主指标） overall = mean( -mean_k log10 p_AUPR(k), -mean_k log10 p_AUROC(k) ), k ∈ {Net1,Net3,Net4}。
Net2 有金标但当届不计分（无 null 分布），这里只报告 AUPR/AUROC 作为次要指标。
名次: 与官方 Supp Data 2 中 35 个方法 + community 的 Overall 比较，名次 = 1 + 严格优于本提交的条目数。
p 值为 0（超出 null 支撑）时按 P_FLOOR 截断，并在输出中标注。
本移植的重复边处理与官方一致（不去重，按出现位置计入）。
"""
import argparse, csv, glob, json, math, os, re, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'reference')
SCORED = [1, 3, 4]
ALL = [1, 2, 3, 4]
MAX_EDGES = 100000
P_FLOOR = 1e-300


def load_gold(n):
    pos = []
    for l in open(os.path.join(REF, 'gold', f'Network{n}.tsv')):
        p = l.split()
        if len(p) >= 3 and float(p[2]) != 0:
            pos.append((int(p[0][1:]), int(p[1][1:])))
    return pos


class Gold:
    def __init__(self, n):
        pos = load_gold(n)
        self.pos = set(pos)
        self.regs = set(i for i, _ in pos)
        self.genes = set(i for e in pos for i in e)
        self.P = len(self.pos)
        ng = len(self.genes)
        # 全集 = regs × genes 去自环（reg 必在 genes 中）
        self.T = len(self.regs) * ng - len(self.regs)
        self.N = self.T - self.P

    def label(self, i, j):
        """1 正例, 0 负例, None 不在全集"""
        if i not in self.regs or j not in self.genes or i == j:
            return None
        return 1 if (i, j) in self.pos else 0


def load_pdf(n, metric):
    from scipy.io import loadmat
    m = loadmat(os.path.join(REF, 'null_pdfs', f'Network{n}_{metric}.mat'))
    return m['X'].ravel().astype(float), m['Y'].ravel().astype(float)


def probability(X, Y, x):
    dx = X[1] - X[0]
    return float(np.sum((X >= x) * Y * dx))


def parse_pred(path, max_edges=MAX_EDGES):
    edges, conf, warn = [], [], []
    bad = 0
    for l in open(path, errors='replace'):
        p = l.split()
        if len(p) < 2:
            continue
        m1, m2 = re.match(r'^G(\d+)$', p[0]), re.match(r'^G(\d+)$', p[1])
        if not (m1 and m2):
            bad += 1
            continue
        edges.append((int(m1.group(1)), int(m2.group(1))))
        try:
            conf.append(float(p[2]) if len(p) > 2 else float('nan'))
        except ValueError:
            conf.append(float('nan'))
    if bad:
        warn.append(f'{bad} 行无法解析已跳过')
    if len(edges) > max_edges:
        warn.append(f'{len(edges)} 行 > {max_edges}，截断')
        edges, conf = edges[:max_edges], conf[:max_edges]
    c = np.array(conf)
    if len(c) > 1 and np.all(np.isfinite(c)) and np.any(np.diff(c) > 1e-12):
        warn.append('置信度不是非增序列；按行序计分（与官方脚本一致）')
    return edges, warn


def evaluate(gold, edges):
    disc = [gold.label(i, j) for i, j in edges]
    disc = np.array([d for d in disc if d is not None], dtype=float)
    L, P, N, T = len(disc), gold.P, gold.N, gold.T
    TPL = disc.sum()
    p = (P - TPL) / (T - L) if L < T else 0.0
    pos = np.concatenate([disc, np.full(T - L, p)])
    neg = np.concatenate([1 - disc, np.full(T - L, 1 - p)])
    TPk, FPk = np.cumsum(pos), np.cumsum(neg)
    K = np.arange(1, T + 1, dtype=float)
    TPR, FPR, PREC = TPk / P, FPk / N, TPk / K
    auroc = float(np.trapezoid(TPR, FPR) if hasattr(np, 'trapezoid') else np.trapz(TPR, FPR))
    aupr = float((np.trapezoid(PREC, TPR) if hasattr(np, 'trapezoid') else np.trapz(PREC, TPR)) / (1 - 1 / P))
    return {'L_in_gs': int(L), 'TP_in_list': int(TPL), 'P': P, 'N': N, 'AUROC': auroc, 'AUPR': aupr}


def find_file(d, n):
    for pat in (f'Network{n}.txt', f'Network{n}.tsv', f'*_Network{n}.txt', f'*_Network{n}.tsv', f'*Network{n}*'):
        fs = sorted(glob.glob(os.path.join(d, pat)))
        if fs:
            return fs[0]
    return None


_CACHE = {}


def gold_of(n):
    if n not in _CACHE:
        _CACHE[n] = Gold(n)
    return _CACHE[n]


def score_dir(d):
    per, warns, missing = {}, {}, []
    for n in ALL:
        f = find_file(d, n)
        if f is None:
            missing.append(f'Network{n}')
        if f is None:
            edges, w = [], ['文件缺失，按空列表（完全随机补全）计分']
        else:
            edges, w = parse_pred(f)
        r = evaluate(gold_of(n), edges)
        if n in SCORED:
            for metric in ('AUPR', 'AUROC'):
                X, Y = load_pdf(n, metric)
                pv = probability(X, Y, r[metric])
                if pv <= 0:
                    w.append(f'p_{metric}=0（超出 null 支撑），截断为 {P_FLOOR}')
                    pv = P_FLOOR
                r['p_' + metric] = pv
        per[f'Net{n}'] = r
        if w:
            warns[f'Net{n}'] = w
    aupr_score = -float(np.mean([math.log10(per[f'Net{n}']['p_AUPR']) for n in SCORED]))
    auroc_score = -float(np.mean([math.log10(per[f'Net{n}']['p_AUROC']) for n in SCORED]))
    overall = (aupr_score + auroc_score) / 2
    return {'overall': overall, 'aupr_score': aupr_score, 'auroc_score': auroc_score,
            'complete': not missing, 'missing_networks': missing,
            'per_network': per, 'warnings': warns}


def load_board():
    return list(csv.DictReader(open(os.path.join(REF, 'leaderboard_official.csv'))))


def rank(overall, board, exclude=None):
    rows = [r for r in board if r['method'] != exclude]
    better = sum(1 for r in rows if float(r['overall']) > overall + 1e-9)
    better35 = sum(1 for r in rows if r['kind'] != 'community' and float(r['overall']) > overall + 1e-9)
    n35 = sum(1 for r in rows if r['kind'] != 'community')
    return {'rank_among_36_incl_community': f'{better + 1}/{len(rows) + 1}',
            'rank_among_35_methods': f'{better35 + 1}/{n35 + 1}'}


def self_check(pred_root):
    board = load_board()
    dirs = {}
    for sub in ('Challenge participants', 'Off-the-shelf methods'):
        for d in glob.glob(os.path.join(pred_root, sub, '*')):
            if os.path.isdir(d):
                dirs[os.path.basename(d)] = d
    dirs['Community'] = os.path.join(pred_root, 'Community integration')
    rows, diffs = [], {k: [] for k in ('overall', 'aupr_score', 'auroc_score', 'aupr', 'auroc', 'aupr_net2', 'auroc_net2')}
    for b in board:
        m = b['method']
        if m not in dirs:
            rows.append({'method': m, 'missing': True}); continue
        s = score_dir(dirs[m])
        row = {'method': m, 'official_overall': float(b['overall']), 'ours_overall': round(s['overall'], 4),
               'official_aupr_score': float(b['aupr_score']), 'ours_aupr_score': round(s['aupr_score'], 4),
               'official_auroc_score': float(b['auroc_score']), 'ours_auroc_score': round(s['auroc_score'], 4)}
        diffs['overall'].append(abs(s['overall'] - float(b['overall'])))
        diffs['aupr_score'].append(abs(s['aupr_score'] - float(b['aupr_score'])))
        diffs['auroc_score'].append(abs(s['auroc_score'] - float(b['auroc_score'])))
        for n in ALL:
            for met in ('AUPR', 'AUROC'):
                off = float(b[f'{met.lower()}_net{n}'])
                ours = s['per_network'][f'Net{n}'][met]
                row[f'{met}_Net{n}'] = [off, round(ours, 4)]
                key = met.lower() + ('_net2' if n == 2 else '')
                diffs[key].append(abs(ours - off))
        rows.append(row)
    summ = {k: {'n': len(v), 'max_abs_diff': round(max(v), 5) if v else None,
                'n_gt_0.0015' if k in ('aupr', 'auroc', 'aupr_net2', 'auroc_net2') else 'n_gt_0.01':
                    int(sum(1 for x in v if x > (0.0015 if k in ('aupr', 'auroc', 'aupr_net2', 'auroc_net2') else 0.01)))}
            for k, v in diffs.items()}
    return {'summary': summ, 'rows': rows}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--submission')
    ap.add_argument('--self-check')
    ap.add_argument('--json')
    ap.add_argument('--name', default=None, help='若提交即为官方表中某方法，名次计算时排除它自身')
    a = ap.parse_args()
    if a.self_check:
        out = self_check(a.self_check)
        print(json.dumps(out['summary'], ensure_ascii=False, indent=1))
    elif a.submission:
        out = score_dir(a.submission)
        out.update(rank(out['overall'], load_board(), exclude=a.name))
        for n in ALL:
            r = out['per_network'][f'Net{n}']
            extra = f"  p_AUPR={r['p_AUPR']:.3e} p_AUROC={r['p_AUROC']:.3e}" if 'p_AUPR' in r else '  (不计分)'
            print(f"Net{n}: AUPR={r['AUPR']:.4f} AUROC={r['AUROC']:.4f}{extra}")
        print(f"overall={out['overall']:.3f} (AUPR score {out['aupr_score']:.3f}, AUROC score {out['auroc_score']:.3f})")
        print(f"rank: {out['rank_among_36_incl_community']} (含 community); {out['rank_among_35_methods']} (35 个方法)")
        if out['warnings']:
            print('warnings:', json.dumps(out['warnings'], ensure_ascii=False))
    else:
        ap.error('需要 --submission 或 --self-check')
    if a.json:
        json.dump(out, open(a.json, 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
