#!/usr/bin/env python3
"""Verifier for SIMCO consolidation tasks (annual / half-year).

Usage: python verify.py <submission_dir> [--json-out result.json]

Deliverables expected in <submission_dir>:
  entity_tb_usd.csv     entity,account,amount        (translated pre-elimination TB per entity)
  eliminations.csv      entry_id,account,amount|debit,credit[,description]
  consolidated_tb.csv   account,amount
  summary.json          key figures (see prompt)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _vlib as V  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, "reference")
ASSET, LIAB, EQUITY = "A", "L", "E"


def acct_types():
    t = {}
    for r in V.read_rows(os.path.join(REF, "chart_of_accounts.csv")):
        t[r["account"]] = r["type"]
    return t


def main():
    args = V.main_args()
    sub = args.submission
    types = acct_types()
    g_ent = V.keyed_amounts(V.read_rows(os.path.join(REF, "entity_tb_usd.csv")), ("entity", "account"))
    g_cons = V.keyed_amounts(V.read_rows(os.path.join(REF, "consolidated_tb.csv")), ("account",))
    g_sum = V.read_json(os.path.join(REF, "summary.json"))

    s_ent_rows = V.read_rows(os.path.join(sub, "entity_tb_usd.csv"))
    s_el_rows = V.read_rows(os.path.join(sub, "eliminations.csv"))
    s_cons_rows = V.read_rows(os.path.join(sub, "consolidated_tb.csv"))
    s_sum = V.read_json(os.path.join(sub, "summary.json")) or {}
    s_ent = V.keyed_amounts(s_ent_rows, ("entity", "account"))
    s_cons = V.keyed_amounts(s_cons_rows, ("account",))

    hard = {}
    # H1 eliminations balance
    ents = V.entries_from_rows(s_el_rows)
    unbalanced = [k[0] for k, rows in ents.items() if abs(sum(V.amount_of(r) for r in rows)) > 0.011]
    hard["eliminations_each_balanced"] = bool(s_el_rows is not None) and not unbalanced
    # H2 consolidated TB balances
    hard["consolidated_tb_balances"] = bool(s_cons_rows) and abs(sum(s_cons.values())) <= 0.05
    # H5 each entity TB balances
    by_ent = {}
    for (e, a), v in s_ent.items():
        by_ent[e] = by_ent.get(e, 0) + v
    hard["entity_tbs_balance"] = bool(s_ent_rows) and all(abs(v) <= 0.05 for v in by_ent.values())
    # H3 internal tie: entity TBs + eliminations = consolidated TB
    tie = {}
    for (e, a), v in s_ent.items():
        tie[(a,)] = tie.get((a,), 0) + v
    for rows in ents.values():
        for r in rows:
            tie[(r.get("account", ""),)] = tie.get((r.get("account", ""),), 0) + V.amount_of(r)
    m, n, mism_tie = V.compare(tie, s_cons, tol=lambda g: 0.05)
    hard["entity_plus_eliminations_ties_to_consolidated"] = bool(s_cons_rows) and m == n
    # H4 statement tie-out: summary totals agree with submitted TB and A = L + E
    A = sum(v for (a,), v in s_cons.items() if types.get(a) == "asset")
    L = -sum(v for (a,), v in s_cons.items() if types.get(a) == "liability")
    NI = -sum(v for (a,), v in s_cons.items() if types.get(a) in ("revenue", "expense"))
    E = -sum(v for (a,), v in s_cons.items() if types.get(a) == "equity") + NI
    try:
        tie_ok = (abs(V.num(s_sum.get("total_assets")) - A) <= 1.0 and abs(V.num(s_sum.get("total_liabilities")) - L) <= 1.0
                  and abs(V.num(s_sum.get("total_equity")) - E) <= 1.0
                  and abs(V.num(s_sum.get("consolidated_net_income")) - NI) <= 1.0 and abs(A - L - E) <= 1.0)
    except Exception:
        tie_ok = False
    hard["statements_tie_out"] = bool(s_cons_rows) and tie_ok

    # branch: per-entity translated TBs
    bm, bn, bmis = V.compare(g_ent, s_ent)
    # merge: consolidated TB lines + summary figures
    cm, cn, cmis = V.compare(g_cons, s_cons)
    sm, smis = 0, []
    for k, g in g_sum.items():
        s = s_sum.get(k)
        ok = s is not None and abs(V.num(s) - V.num(g)) <= V.tol_for(V.num(g))
        sm += ok
        if not ok:
            smis.append({"key": k, "gold": g, "submitted": s})
    merge_total = cn + len(g_sum)
    merge_score = V.frac(cm + sm, merge_total)
    branch_score = V.frac(bm, bn)
    full = all(hard.values()) and bm == bn and cm == cn and sm == len(g_sum)
    res = {
        "hard_checks": hard,
        "branch": {"score": round(branch_score, 4), "matched": bm, "total": bn, "mismatches": bmis[:args.show]},
        "merge": {"score": round(merge_score, 4), "consolidated_tb": [cm, cn], "summary": [sm, len(g_sum)],
                  "tb_mismatches": cmis[:args.show], "summary_mismatches": smis},
        "unbalanced_elimination_entries": unbalanced[:args.show],
        "full_success": bool(full),
    }
    V.emit(res, args.json_out)


if __name__ == "__main__":
    main()
