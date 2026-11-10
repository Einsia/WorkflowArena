#!/usr/bin/env python3
"""Verifier for SIMCO multi-month close tasks (simco-07, simco-08).

Usage: python verify.py <submission_dir> [--json-out result.json]
Deliverables: adjustments.csv, closing_tb.csv, findings.csv, summary.json
"""
import math
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _vlib as V  # noqa: E402

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference")
IC = ("1200", "1250", "1260", "1270", "2100", "2150", "2160", "2250")
PAIRS = (("1200", "2100"), ("1250", "2150"), ("1260", "2160"), ("1270", "2250"))


def month_end(m):
    import calendar
    y, mm = int(m[:4]), int(m[5:7])
    return f"{m}-{calendar.monthrange(y, mm)[1]:02d}"


def load(path):
    out = defaultdict(float)
    for r in V.read_rows(path) or []:
        out[(r["entity"], r["month"], r["account"], r.get("counterparty", ""))] += V.num(r["amount"])
    return out


def main():
    args = V.main_args()
    sub = args.submission
    meta = V.read_json(os.path.join(REF, "meta.json"))
    ents, months = meta["entities"], meta["months"]
    ab = load(os.path.join(REF, "asbooked_tb.csv"))
    cl = load(os.path.join(REF, "clean_tb.csv"))
    adj = V.read_rows(os.path.join(sub, "adjustments.csv"))
    hard = {}
    groups = V.entries_from_rows(adj)
    unbal = [k[0] for k, rows in groups.items() if abs(sum(V.amount_of(r) for r in rows)) > 0.011]
    hard["adjustments_balanced"] = adj is not None and not unbal
    touched = {r.get("account") for r in adj or [] if abs(V.amount_of(r)) > 0.004}
    hard["protected_accounts_untouched"] = not (touched & set(meta["protected_accounts"]))
    # timing traps: no entry may move cash of an entity by exactly a deposit-in-transit / outstanding amount
    traps = meta["timing_traps"]
    viol = []
    for (eid,), rows in groups.items():
        cash = defaultdict(float)
        for r in rows:
            if r.get("account") == "1000":
                cash[r.get("entity")] += V.amount_of(r)
        for e, c in cash.items():
            if any(abs(abs(c) - abs(t)) < 0.005 for t in traps.get(e, [])):
                viol.append(eid)
    hard["timing_differences_not_adjusted"] = not viol
    # replay
    rep = defaultdict(float, ab)
    start = meta["period_start"]
    for r in adj or []:
        e, a, cp, d = r.get("entity", ""), r.get("account", ""), r.get("counterparty", ""), r.get("date", "")
        v = V.amount_of(r)
        if d < start:
            continue
        for m in months:
            if d <= month_end(m):
                rep[(e, m, a, "")] += v
                if a in IC and cp:
                    rep[(e, m, a, cp)] += v
    keys = {k for k in set(cl) | set(ab) if abs(cl.get(k, 0) - ab.get(k, 0)) > 0.004}
    keys |= {k for k in rep if abs(rep.get(k, 0) - ab.get(k, 0)) > 0.004}
    ok = [k for k in keys if abs(rep.get(k, 0) - cl.get(k, 0)) <= 5.0]
    bmis = [{"key": list(k), "gold": round(cl.get(k, 0), 2), "replayed": round(rep.get(k, 0), 2)}
            for k in sorted(keys) if abs(rep.get(k, 0) - cl.get(k, 0)) > 5.0]
    # IC agreement after correction (USD; foreign at month closing rate)
    ccy = meta["currencies"]
    rates = meta["close_rates"]
    agree = True
    for m in months:
        for e in ents:
            for cp in ents:
                for ra, pa in PAIRS:
                    def usd(ent, acct, c):
                        v = rep.get((ent, m, acct, c), 0.0)
                        return v if ccy[ent] == "USD" else v * rates[m][ccy[ent]]
                    if abs(usd(e, ra, cp) + usd(cp, pa, e)) > 1.0:
                        agree = False
    hard["ic_balances_agree_after_correction"] = agree
    # self-reported closing TB must equal the replay for every reported cell and cover every changed cell
    rep_tb = load(os.path.join(sub, "closing_tb.csv")) if os.path.exists(os.path.join(sub, "closing_tb.csv")) else {}
    # Extra counterparty detail is allowed only outside every canonical key domain.
    detail = {tuple(r["key"]): r["amount"] for r in V.read_json(os.path.join(REF, "counterparty_details.json"))}
    for r in V.read_rows(os.path.join(sub, "adjustments.csv")) or []:
        e, a, cp, d = [r.get(k, "") for k in ["entity", "account", "counterparty", "date"]]
        if d < meta["period_start"] or not cp:
            continue
        for month in meta["months"]:
            if d <= month_end(month):
                key = (e, month, a, cp)
                detail[key] = detail.get(key, 0) + V.amount_of(r)
    def expected_detail(k):
        optional = bool(k[3]) and k not in rep and k not in cl and k not in ab and k not in keys
        return detail.get(k, 0) if optional else rep.get(k, 0)
    exact = bool(rep_tb) and all(math.isfinite(value) and math.isfinite(expected_detail(k)) and abs(value - expected_detail(k)) <= 5.0 for k, value in rep_tb.items()) and all(math.isfinite(rep_tb.get(k, 0)) and abs(rep_tb.get(k, 0) - rep.get(k, 0)) <= 5.0 for k in keys)
    hard["closing_tb_equals_replay"] = exact
    # findings multiset F1
    g = Counter((r["entity"], r["month"], r["error_type"]) for r in V.read_rows(os.path.join(REF, "findings.csv")))
    s = Counter((r.get("entity"), r.get("month"), r.get("error_type")) for r in V.read_rows(os.path.join(sub, "findings.csv")) or [])
    tp = sum(min(g[k], s[k]) for k in g)
    prec = V.frac(tp, sum(s.values())) if s else 0.0
    rec = V.frac(tp, sum(g.values()))
    f1 = 0.0 if tp == 0 else 2 * prec * rec / (prec + rec)
    # summary
    gs = V.read_json(os.path.join(REF, "summary.json"))
    ss = V.read_json(os.path.join(sub, "summary.json")) or {}
    sm, smis = 0, []
    for k, gv in gs.items():
        sv = ss.get(k)
        if isinstance(gv, str):
            good = isinstance(sv, str) and sv.strip() == gv
        else:
            good = sv is not None and not isinstance(sv, str) and abs(V.num(sv) - gv) <= V.tol_for(gv)
        sm += good
        if not good:
            smis.append({"key": k, "gold": gv, "submitted": sv})
    branch = V.frac(len(ok), len(keys))
    merge = (V.frac(sm, len(gs)) + f1) / 2
    full = all(hard.values()) and len(ok) == len(keys) and sm == len(gs) and abs(f1 - 1) < 1e-9
    V.emit({"hard_checks": hard,
            "branch": {"score": round(branch, 4), "cells": [len(ok), len(keys)], "mismatches": bmis[:args.show]},
            "merge": {"score": round(merge, 4), "summary": [sm, len(gs)], "summary_mismatches": smis,
                      "findings_precision": round(prec, 4), "findings_recall": round(rec, 4), "findings_f1": round(f1, 4),
                      "missed_findings": [list(k) for k in (g - s)][:args.show]},
            "timing_trap_violations": viol[:args.show], "unbalanced_entries": unbal[:args.show],
            "full_success": bool(full)}, args.json_out)


if __name__ == "__main__":
    main()
