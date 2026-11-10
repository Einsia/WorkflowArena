#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Programmatic grader for the multi-defendant criminal-judgment tasks (no LLM judge).

usage: verify.py [--gold tests/reference/gold.json] --submission output/judgment.json [--out report.json]

Branch score (per-defendant, can be produced defendant by defendant):
    charges set-F1, articles set-F1, statutory-circumstance set-F1, final-term score (CAIL-style
    log-distance bands), probation accuracy (only where the gold is determinable).
Merge score (needs the whole case):
    role accuracy per (defendant, charge) where the court designated 主犯/从犯/胁从犯 (0.6),
    首要分子 set-F1 (0.2), consistency checks (0.2): 刑法第69条 range of the decided term vs the
    per-charge terms, 第72/74条 probation preconditions, and principal-vs-accessory term ordering on
    the pairs where the court's own terms respect that ordering.
Case-level all-correct (CMDL-style): every defendant's charge set and article set exact and every
graded role exact.  Full success: see FULL_SUCCESS below.
"""
import argparse, json, math, os, sys, unicodedata

CIRC_ENUM = ["未成年", "未遂", "自首", "坦白", "立功", "累犯"]
ROLE_GRADED = {"主犯", "从犯", "胁从犯"}
SEVERE = {"死刑": 10000, "死刑缓期二年执行": 9000, "无期徒刑": 8000}
DEATH_ALIASES = {"死刑", "死刑立即执行", "死刑缓期二年执行", "死缓", "死刑缓期执行"}
FULL_SUCCESS = dict(term_band=0.8, term_frac=0.8, circ_f1=0.8, prob_acc=0.8, order=0.9)

def nfkc(s):
    return unicodedata.normalize("NFKC", str(s)).replace(" ", "").replace("　", "").strip()

def norm_charge(c):
    c = nfkc(c).replace(",", "、")
    if c and not c.endswith("罪"):
        c += "罪"
    return c

def norm_type(t):
    t = nfkc(t or "")
    if t in ("死缓", "死刑缓期执行", "死刑缓期二年执行"):
        return "死刑缓期二年执行"
    if t in ("死刑立即执行",):
        return "死刑"
    return t

def f1(pred, gold):
    pred, gold = set(pred), set(gold)
    if not pred and not gold:
        return 1.0
    if not pred or not gold:
        return 0.0
    tp = len(pred & gold)
    if tp == 0:
        return 0.0
    p, r = tp / len(pred), tp / len(gold)
    return 2 * p * r / (p + r)

def months_of(term):
    """severity scale used for ordering; None if unparseable"""
    if not isinstance(term, dict):
        return None
    t = norm_type(term.get("type"))
    if t in SEVERE:
        return SEVERE[t]
    if t in ("有期徒刑", "拘役", "管制"):
        try:
            m = float(term.get("months"))
        except (TypeError, ValueError):
            return None
        return m if m >= 0 else None
    if t in ("免予刑事处罚", "免予刑事处分", "单处罚金"):
        return 0.0
    return None

def term_score(pred, gold):
    """CAIL-style: v = |ln(p+1) - ln(g+1)|; bands 0.2/0.4/0.6/0.8/1.0 -> 1/.8/.6/.4/.2, else 0."""
    gt = norm_type(gold["type"])
    if not isinstance(pred, dict):
        return 0.0, None
    pt = norm_type(pred.get("type"))
    if gt in ("死刑", "死刑缓期二年执行"):
        ok = pt in ("死刑", "死刑缓期二年执行") if gold.get("death_any") else pt == gt
        return (1.0 if ok else 0.0), None
    if gt == "无期徒刑":
        return (1.0 if pt == "无期徒刑" else 0.0), None
    if pt in SEVERE:
        return 0.0, None
    p, g = months_of(pred), float(gold["months"])
    if p is None:
        return 0.0, None
    v = abs(math.log(p + 1) - math.log(g + 1))
    s = 0.0
    for thr, sc in ((0.2, 1.0), (0.4, 0.8), (0.6, 0.6), (0.8, 0.4), (1.0, 0.2)):
        if v <= thr:
            s = sc
            break
    if pt != gt and s > 0:          # 有期徒刑 vs 拘役 vs 管制 mismatch
        s *= 0.8
    return s, v

def check_69(entry, charges):
    """刑法第69条: decided term within [max per-charge term, min(sum, cap)]; returns (applicable, ok, why)"""
    if len(charges) < 2:
        return False, True, ""
    ct = entry.get("charge_terms") or {}
    ct = {norm_charge(k): v for k, v in ct.items()} if isinstance(ct, dict) else {}
    terms = [ct.get(c) for c in charges]
    final = entry.get("final_term")
    if any(not isinstance(t, dict) for t in terms) or not isinstance(final, dict):
        return True, False, "missing charge_terms/final_term"
    types = [norm_type(t.get("type")) for t in terms]
    ft = norm_type(final.get("type"))
    sev = [SEVERE[t] for t in types if t in SEVERE]
    if sev:
        top = max(sev)
        return True, (ft in SEVERE and SEVERE[ft] >= top), "life/death absorbs"
    fixed = [months_of(t) for t, ty in zip(terms, types) if ty == "有期徒刑"]
    jy = [months_of(t) for t, ty in zip(terms, types) if ty == "拘役"]
    gz = [months_of(t) for t, ty in zip(terms, types) if ty == "管制"]
    if None in fixed + jy + gz:
        return True, False, "unparseable"
    fm = months_of(final)
    if fm is None:
        return True, False, "unparseable final"
    if fixed:            # 有期徒刑 absorbs 拘役 (69(2), 修正案九); 管制 executed separately
        lo, total = max(fixed), sum(fixed)
        cap = 240 if total < 420 else 300
        hi = min(total, cap)
        return True, (ft == "有期徒刑" and lo - 1e-9 <= fm <= hi + 1e-9), "fixed-term range [%s,%s]" % (lo, hi)
    if jy:
        lo, hi = max(jy), min(sum(jy), 12)
        return True, (ft == "拘役" and lo <= fm <= hi), "detention range"
    lo, hi = max(gz), min(sum(gz), 36)
    return True, (ft == "管制" and lo <= fm <= hi), "control range"

def check_74(entry, circs, leader):
    if entry.get("probation") is not True:
        return False, True
    fm, ft = months_of(entry.get("final_term")), norm_type((entry.get("final_term") or {}).get("type"))
    ok = ft in ("有期徒刑", "拘役") and fm is not None and fm <= 36 and "累犯" not in circs and not leader
    return True, ok

def grade(gold, sub):
    gdefs = gold["defendants"]
    sdefs = sub.get("defendants", {}) if isinstance(sub, dict) else {}
    if not isinstance(sdefs, dict):
        sdefs = {}
    ungraded_circ = set(gold.get("ungraded_circumstances", []))
    circ_enum = [c for c in CIRC_ENUM if c not in ungraded_circ]
    per, comp = {}, {"charges": [], "articles": [], "circumstances": [], "term": [], "probation": []}
    circ_tp = circ_fp = circ_fn = 0
    role_items, role_ok = [], 0
    all_correct = True
    band_hits = 0
    for name, g in gdefs.items():
        s = sdefs.get(name) or {}
        if not isinstance(s, dict):
            s = {}
        sc = [norm_charge(c) for c in (s.get("charges") or []) if isinstance(c, str)]
        sa = []
        for a in s.get("articles") or []:
            try:
                sa.append(int(str(a).strip().lstrip("第").rstrip("条")))
            except ValueError:
                pass
        scirc = [nfkc(c) for c in (s.get("circumstances") or []) if isinstance(c, str)]
        scirc_g = set(c for c in scirc if c in circ_enum)
        gcirc_g = set(c for c in g["circumstances"] if c in circ_enum)
        cf, af, crf = f1(sc, g["charges"]), f1(sa, g["articles"]), f1(scirc_g, gcirc_g)
        circ_tp += len(scirc_g & gcirc_g); circ_fp += len(scirc_g - gcirc_g); circ_fn += len(gcirc_g - scirc_g)
        ts, v = term_score(s.get("final_term"), g["term"])
        band_hits += ts >= FULL_SUCCESS["term_band"]
        comp["charges"].append(cf); comp["articles"].append(af); comp["circumstances"].append(crf); comp["term"].append(ts)
        pr = None
        if g.get("probation") is not None:
            pr = 1.0 if (s.get("probation") is True) == bool(g["probation"]) else 0.0
            comp["probation"].append(pr)
        sroles = s.get("roles") or {}
        sroles = {norm_charge(k): nfkc(v) for k, v in sroles.items()} if isinstance(sroles, dict) else {}
        r_ok = []
        for ch, gr in g["roles"].items():
            if gr not in ROLE_GRADED:
                continue
            pr_role = sroles.get(norm_charge(ch), "")
            if pr_role == "首要分子":
                pr_role = "主犯"
            ok = pr_role == gr
            role_items.append((name, ch, gr, pr_role, ok)); role_ok += ok; r_ok.append(ok)
        exact = set(sc) == set(g["charges"]) and set(sa) == set(g["articles"]) and all(r_ok)
        all_correct &= exact
        per[name] = dict(charges_f1=cf, articles_f1=af, circumstances_f1=crf, term_score=ts, log_dist=v,
                         probation=pr, roles_correct=sum(r_ok), roles_graded=len(r_ok), exact=exact)
    n = len(gdefs)
    branch_parts = {k: (sum(v) / len(v) if v else None) for k, v in comp.items()}
    branch = sum(x for x in branch_parts.values() if x is not None) / len([x for x in branch_parts.values() if x is not None])
    circ_micro = 1.0 if circ_tp + circ_fp + circ_fn == 0 else 2 * circ_tp / (2 * circ_tp + circ_fp + circ_fn)
    role_acc = role_ok / len(role_items) if role_items else 1.0
    gold_leaders = {k for k, g in gdefs.items() if g.get("leader")}
    sub_leaders = {k for k in gdefs if isinstance(sdefs.get(k), dict) and sdefs[k].get("leader") is True}
    leader_f1 = f1(sub_leaders, gold_leaders)
    # consistency (submission-internal + gold-anchored ordering)
    c69 = []; c74 = []
    for name, g in gdefs.items():
        s = sdefs.get(name) if isinstance(sdefs.get(name), dict) else {}
        sc = sorted(set(norm_charge(c) for c in (s.get("charges") or []) if isinstance(c, str)))
        if not g.get("prior_sentence_merged"):
            app, ok, why = check_69(s, sc)
            if app:
                c69.append((name, ok, why))
        app, ok = check_74(s, set(nfkc(c) for c in (s.get("circumstances") or []) if isinstance(c, str)), s.get("leader") is True)
        if app:
            c74.append((name, ok))
    pairs = []
    for ch in sorted({c for g in gdefs.values() for c in g["roles"]}):
        P = [k for k, g in gdefs.items() if g["roles"].get(ch) == "主犯"]
        A = [k for k, g in gdefs.items() if g["roles"].get(ch) == "从犯"]
        for p in P:
            for a in A:
                gp, ga = months_of(gdefs[p]["term"]), months_of(gdefs[a]["term"])
                if gp is not None and ga is not None and gp >= ga:
                    sp = months_of((sdefs.get(p) or {}).get("final_term")) if isinstance(sdefs.get(p), dict) else None
                    sa_ = months_of((sdefs.get(a) or {}).get("final_term")) if isinstance(sdefs.get(a), dict) else None
                    pairs.append((p, a, ch, sp is not None and sa_ is not None and sp >= sa_))
    c69_rate = sum(ok for _, ok, _ in c69) / len(c69) if c69 else 1.0
    c74_rate = sum(ok for _, ok in c74) / len(c74) if c74 else 1.0
    order_rate = sum(ok for *_, ok in pairs) / len(pairs) if pairs else 1.0
    consistency = (c69_rate + c74_rate + order_rate) / 3
    if not sdefs:
        consistency = c69_rate = c74_rate = order_rate = 0.0
    merge = 0.6 * role_acc + 0.2 * leader_f1 + 0.2 * consistency
    prob_acc = branch_parts["probation"] if branch_parts["probation"] is not None else 1.0
    full = (all_correct and leader_f1 == 1.0 and circ_micro >= FULL_SUCCESS["circ_f1"]
            and band_hits / n >= FULL_SUCCESS["term_frac"] and prob_acc >= FULL_SUCCESS["prob_acc"]
            and c69_rate == 1.0 and c74_rate == 1.0 and order_rate >= FULL_SUCCESS["order"])
    return dict(
        n_defendants=n,
        branch=dict(score=round(branch, 4), **{k: (round(v, 4) if v is not None else None) for k, v in branch_parts.items()},
                    circumstances_micro_f1=round(circ_micro, 4), term_within_band_frac=round(band_hits / n, 4)),
        merge=dict(score=round(merge, 4), role_accuracy=round(role_acc, 4), n_role_items=len(role_items),
                   leader_f1=round(leader_f1, 4), n_gold_leaders=len(gold_leaders),
                   consistency=dict(score=round(consistency, 4), art69_rate=round(c69_rate, 4), n_art69=len(c69),
                                    art74_rate=round(c74_rate, 4), n_art74=len(c74), order_rate=round(order_rate, 4), n_order_pairs=len(pairs))),
        case_all_correct=all_correct,
        full_success=bool(full),
        per_defendant=per,
        role_errors=[dict(defendant=a, charge=b, gold=c, pred=d) for a, b, c, d, ok in role_items if not ok],
        art69_failures=[dict(defendant=a, why=w) for a, ok, w in c69 if not ok],
        unknown_defendants_in_submission=sorted(set(sdefs) - set(gdefs)),
    )

def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--gold", default=os.path.join(here, "reference", "gold.json"))
    ap.add_argument("--submission", required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    gold = json.load(open(a.gold, encoding="utf-8"))
    try:
        sub = json.load(open(a.submission, encoding="utf-8"))
    except Exception as e:  # unreadable submission scores zero
        sub = {}
        print("WARN: unreadable submission: %s" % e, file=sys.stderr)
    rep = grade(gold, sub)
    txt = json.dumps(rep, ensure_ascii=False, indent=1)
    if a.out:
        open(a.out, "w", encoding="utf-8").write(txt)
    summary = dict(branch=rep["branch"]["score"], merge=rep["merge"]["score"], role_accuracy=rep["merge"]["role_accuracy"],
                   case_all_correct=rep["case_all_correct"], full_success=rep["full_success"])
    print(json.dumps(summary, ensure_ascii=False))

if __name__ == "__main__":
    main()
