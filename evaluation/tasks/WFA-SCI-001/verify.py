#!/usr/bin/env python3
"""comp-capri-scoring 判分器 (仅标准库)。

用法:
  python3 verify.py --submission <目录> [--json out.json]
  python3 verify.py --self-check [--json out.json]   # 正对照: 真实打分组提交 -> 本题格式 -> 重算, 与库内官方逐模型分级比对

提交目录: 每个靶标一个文件 <靶标>.txt (靶标 C01..C10)。每个非注释行为
  `<rank> <诱饵ID>`  (rank 为 1..N 的整数)   或仅 `<诱饵ID>` (按行序定 rank)。
只评 rank<=10 的条目; 重复 ID 只计首次; 不在该靶标诱饵集中的 ID 视为 incorrect。

逐靶标 (CAPRI 打分实验官方口径, 模型分级来自 CAPRI Score_set v2022 库内评估):
  best_top10 : top-10 中最好的 CAPRI 等级 high(***)/medium(**)/acceptable(*)/incorrect
  n_acc/n_med/n_high : top-10 中 >=acceptable / >=medium / high 的模型数 (CAPRI 表格写作 N/M**/K***)
  best_top5, top1 : 同上, 取前 5 / 第 1
  dockq_top1, dockq_best10 : 第 1 名模型的 DockQ, 前 10 中最大 DockQ
汇总: hits10 = best_top10>=acceptable 的靶标数; med10 = >=medium 的靶标数; high10; 同理 hits5/hits1;
      n_acc_models10 / n_med_models10 = 各靶标前 10 中 >=acceptable / >=medium 模型数之和 (CAPRI 表格中的 N 与 M**);
      mean_dockq_top1, mean_dockq_best10 (缺失靶标记 0)。
主指标 (primary): 富集度 = (n_acc_models10, n_med_models10) 字典序, 名次 = 1 + 严格更优的打分组数
  (官方 top-10 命中靶标数对随机选择区分度不足, 随机 10 个有约 6% 概率进前 3, 故不作主指标)。
官方 CAPRI 名次 (secondary, official): 按 (hits10, med10, high10) 字典序;
  参比组 = CAPRI 真实打分组 (Score_set 中 S 集, 组身份用跨轮次 uid), 只取在 10 个靶标中至少交了 8 个的组 (缺交靶标按 incorrect);
  参赛组按库内其提交模型的官方分级重算 (同一聚合代码 aggregate())。
"""
import argparse, csv, json, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, 'reference')
TARGETS = ['C%02d' % i for i in range(1, 11)]
LEVEL = {'incorrect': 0, 'acceptable': 1, 'medium': 2, 'high': 3}
NAME = {v: k for k, v in LEVEL.items()}
MIN_TARGETS_ELIGIBLE = 8
INCORRECT = {'classification': 'incorrect', 'dockq': 0.0}

def norm(c):
    return c if c in LEVEL else 'incorrect'   # 库内个别 'unclassified' 按 incorrect

def fnum(v):
    try: return float(v)
    except Exception: return 0.0

def load_truth():
    tr = {t: {} for t in TARGETS}
    for r in csv.DictReader(open(os.path.join(REF, 'decoy_quality.csv'))):
        tr[r['target']][r['decoy_id']] = {'classification': norm(r['classification']), 'dockq': fnum(r['dockq'])}
    return tr

def parse_submission(path):
    """-> list of decoy IDs ordered by rank (index 0 = rank 1); None 表示该 rank 空缺"""
    ent = []; auto = 0
    for l in open(path, errors='replace'):
        l = l.split('#', 1)[0].strip()
        if not l: continue
        p = l.split()
        if len(p) >= 2 and re.fullmatch(r'\d+', p[0]):
            ent.append((int(p[0]), p[1]))
        else:
            auto += 1; ent.append((auto, p[0]))
    ent.sort(key=lambda x: x[0])
    out = {}; seen = set()
    for rk, d in ent:
        if rk < 1 or rk in out or d in seen: continue
        out[rk] = d; seen.add(d)
    n = max(out) if out else 0
    return [out.get(i) for i in range(1, n + 1)]

def score_target(models):
    """models: rank 顺序的质量字典列表 (None = 空缺/无效 -> incorrect)。CAPRI 打分实验聚合。"""
    m = [x if x else INCORRECT for x in models[:10]]
    lv = [LEVEL[x['classification']] for x in m]
    dq = [x['dockq'] for x in m]
    best = lambda k: max(lv[:k]) if lv[:k] else 0
    return {'n_submitted': len(m), 'best_top10': NAME[best(10)], 'best_top5': NAME[best(5)], 'top1': NAME[best(1)],
            'stars_top10': '*' * best(10), 'n_acc': sum(v >= 1 for v in lv), 'n_med': sum(v >= 2 for v in lv),
            'n_high': sum(v >= 3 for v in lv), 'dockq_top1': dq[0] if dq else 0.0, 'dockq_best10': max(dq) if dq else 0.0}

def aggregate(per):
    def cnt(key, k): return sum(1 for t in TARGETS if per.get(t) and LEVEL[per[t][key]] >= k)
    agg = {'n_targets_submitted': sum(1 for t in TARGETS if per.get(t) and per[t]['n_submitted'] > 0)}
    for key, tag in (('best_top10', '10'), ('best_top5', '5'), ('top1', '1')):
        agg['hits' + tag] = cnt(key, 1); agg['med' + tag] = cnt(key, 2); agg['high' + tag] = cnt(key, 3)
    agg['mean_dockq_top1'] = sum(per[t]['dockq_top1'] for t in TARGETS if per.get(t)) / len(TARGETS)
    agg['mean_dockq_best10'] = sum(per[t]['dockq_best10'] for t in TARGETS if per.get(t)) / len(TARGETS)
    agg['n_acc_models10'] = sum(per[t]['n_acc'] for t in TARGETS if per.get(t))   # 前10中 >=acceptable 模型总数 (富集度)
    agg['n_med_models10'] = sum(per[t]['n_med'] for t in TARGETS if per.get(t))
    agg['capri_summary'] = '%d/%d**/%d***' % (agg['hits10'], agg['med10'], agg['high10'])
    return agg

def score_submission(d, truth):
    per = {}; invalid = {}
    for t in TARGETS:
        p = next((os.path.join(d, t + e) for e in ('.txt', '') if os.path.isfile(os.path.join(d, t + e))), None)
        ids = parse_submission(p) if p else []
        invalid[t] = sum(1 for x in ids[:10] if x is not None and x not in truth[t])
        per[t] = score_target([truth[t].get(x) if x else None for x in ids]) if ids else None
    return aggregate(per), per, invalid

def load_groups():
    """CAPRI 打分组按库内官方逐模型分级重算"""
    by = collections.defaultdict(lambda: collections.defaultdict(dict)); names = {}
    for r in csv.DictReader(open(os.path.join(REF, 'scorer_submissions.csv'))):
        by[r['uid']][r['target']][int(r['rank'])] = {'classification': norm(r['classification']), 'dockq': fnum(r['dockq'])}
        names[r['uid']] = r['name']
    res = {}
    for uid, tt in by.items():
        per = {}
        for t in TARGETS:
            if t in tt:
                n = max(tt[t]); per[t] = score_target([tt[t].get(i) for i in range(1, n + 1)])
            else:
                per[t] = None
        res[uid] = (names[uid], aggregate(per), per)
    return res

def key(agg): return (agg['hits10'], agg['med10'], agg['high10'])

def rank(agg, others, f=key):
    return 1 + sum(1 for o in others if f(o) > f(agg))

def self_check(truth):
    """正对照: 每个打分组的真实提交 (映射回诱饵 ID) 经 score_submission 重算, 与库内该组官方逐模型分级聚合结果比对。"""
    G = load_groups(); rep = {'groups': {}, 'n_target_entries': 0, 'n_identical': 0, 'n_identical_fully_mapped': 0, 'n_fully_mapped': 0}
    for uid, (name, agg, per) in sorted(G.items()):
        d = os.path.join(REF, 'participants', uid)
        sagg, sper, _ = score_submission(d, truth)
        g = {'name': name, 'official': agg['capri_summary'], 'rescored_from_submission': sagg['capri_summary'], 'targets': {}}
        for t in TARGETS:
            if per[t] is None: continue
            p = os.path.join(d, t + '.txt'); lines = open(p).read().splitlines()
            fully = not any(l.startswith('#') for l in lines)
            same = all(per[t][k] == sper[t][k] for k in ('best_top10', 'best_top5', 'top1', 'n_acc', 'n_med', 'n_high')) if sper[t] else False
            rep['n_target_entries'] += 1; rep['n_identical'] += same
            rep['n_fully_mapped'] += fully; rep['n_identical_fully_mapped'] += (same and fully)
            g['targets'][t] = {'official': '%s %d/%d**/%d***' % (per[t]['best_top10'], per[t]['n_acc'], per[t]['n_med'], per[t]['n_high']),
                               'rescored': ('%s %d/%d**/%d***' % (sper[t]['best_top10'], sper[t]['n_acc'], sper[t]['n_med'], sper[t]['n_high'])) if sper[t] else 'none',
                               'fully_mapped': fully, 'identical': same}
        rep['groups'][uid] = g
    return rep

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--submission'); ap.add_argument('--json'); ap.add_argument('--self-check', action='store_true')
    a = ap.parse_args()
    truth = load_truth()
    if a.self_check:
        rep = self_check(truth)
        print(json.dumps({k: v for k, v in rep.items() if k != 'groups'}, indent=1))
        if a.json: json.dump(rep, open(a.json, 'w'), indent=1, ensure_ascii=False)
        return
    if not a.submission: ap.error('--submission required')
    agg, per, invalid = score_submission(a.submission, truth)
    G = load_groups()
    sub = os.path.abspath(a.submission)
    elig = {u: v for u, v in G.items() if v[1]['n_targets_submitted'] >= MIN_TARGETS_ELIGIBLE
            and os.path.abspath(os.path.join(REF, 'participants', u)) != sub}
    others = [v[1] for v in elig.values()]
    res = {'aggregate': agg, 'per_target': per, 'invalid_ids_in_top10': invalid, 'n_reference_groups': len(elig),
           'primary': 'enrichment (n_acc_models10, n_med_models10)',
           'rank_primary_enrichment': rank(agg, others, lambda x: (x['n_acc_models10'], x['n_med_models10'])),
           'rank_capri_official': rank(agg, others), 'rank_hits5': rank(agg, others, lambda x: (x['hits5'], x['med5'], x['high5'])),
           'rank_mean_dockq_top1': rank(agg, others, lambda x: x['mean_dockq_top1']),
           'rank_hits1': rank(agg, others, lambda x: (x['hits1'], x['med1'], x['high1'])),
           'leaderboard': sorted(((v[0] + '/' + u, v[1]['capri_summary'], v[1]['n_targets_submitted'], round(v[1]['mean_dockq_top1'], 3)) for u, v in elig.items()),
                                 key=lambda x: tuple(-int(s) for s in re.findall(r'\d+', x[1])))}
    print(f"PRIMARY enrichment: acceptable+ models in top-10 summed over targets={agg['n_acc_models10']} (medium+ {agg['n_med_models10']})  rank={res['rank_primary_enrichment']}/{len(elig)+1}")
    print(f"official CAPRI top-10 (secondary): {agg['capri_summary']} (hits/medium/high targets of 10)  rank={res['rank_capri_official']}/{len(elig)+1}")
    print(f"top-5: {agg['hits5']}/{agg['med5']}**/{agg['high5']}***  rank={res['rank_hits5']}/{len(elig)+1};  top-1 hits={agg['hits1']}")
    print(f"top-1 hits rank={res['rank_hits1']}/{len(elig)+1}")
    print(f"mean DockQ top1={agg['mean_dockq_top1']:.3f} rank={res['rank_mean_dockq_top1']}/{len(elig)+1}; mean best-of-10 DockQ={agg['mean_dockq_best10']:.3f}")
    print(f"targets submitted: {agg['n_targets_submitted']}/10; invalid IDs in top10: {sum(invalid.values())}")
    if a.json: json.dump(res, open(a.json, 'w'), indent=1, ensure_ascii=False)

if __name__ == '__main__':
    main()
