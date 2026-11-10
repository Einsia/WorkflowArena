#!/usr/bin/env python3
"""Generic SIMCO verifier driven by reference/spec.json (tables + summary + hard checks).

Usage: python verify.py <submission_dir> [--json-out result.json]
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _vlib as V  # noqa: E402

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference")
PAIRS = (("1200", "2100"), ("1250", "2150"), ("1260", "2160"), ("1270", "2250"))


def table_score(tspec, sub):
    g_rows = V.read_rows(os.path.join(REF, tspec["file"])) or []
    s_rows = V.read_rows(os.path.join(sub, tspec["file"])) or []
    keys, vals = tspec["keys"], tspec["values"]
    tol = tspec.get("tol", 5.0)
    gi = {tuple(r[k] for k in keys): r for r in g_rows}
    si = {}
    for r in s_rows:
        si[tuple(r.get(k, "") for k in keys)] = r
    m = n = 0
    mis = []
    for k, g in gi.items():
        s = si.get(k)
        for v in vals:
            n += 1
            gv = g[v]
            if s is None:
                ok = False
            elif tspec.get("text", False) or v in tspec.get("text_cols", []):
                sv = (s.get(v, "") or "").strip()
                if gv == "":
                    ok = True                      # free-text field: not graded
                else:
                    try:
                        ok = abs(float(sv) - float(gv)) <= max(tol, 1e-6 * abs(float(gv)))
                    except ValueError:
                        ok = sv.lower() == gv.strip().lower()
            else:
                try:
                    ok = abs(V.num(s.get(v)) - V.num(gv)) <= max(tol, 1e-6 * abs(V.num(gv)))
                except ValueError:
                    ok = False
            m += ok
            if not ok:
                mis.append({"key": list(k), "col": v, "gold": gv, "submitted": None if s is None else s.get(v)})
    if tspec.get("extra_penalty", True):
        for k, s in si.items():
            if k in gi:
                continue
            nonzero = any((s.get(v, "") not in ("", "0", "0.00", "0.0")) for v in vals)
            if nonzero:
                n += len(vals)
                mis.append({"key": list(k), "col": "*", "gold": None, "submitted": "extra row"})
    return m, n, mis, s_rows


def summary_score(keys_role, sub, role, g_sum):
    s_sum = V.read_json(os.path.join(sub, "summary.json")) or {}
    m = n = 0
    mis = []
    for k, g in g_sum.items():
        if keys_role.get(k, "merge") != role:
            continue
        n += 1
        s = s_sum.get(k)
        if isinstance(g, str):
            ok = isinstance(s, str) and s.strip() == g
        elif isinstance(g, list):
            ok = isinstance(s, list) and sorted(map(str, s)) == sorted(map(str, g))
        else:
            ok = s is not None and not isinstance(s, (str, list, dict)) and abs(V.num(s) - V.num(g)) <= V.tol_for(V.num(g))
        m += ok
        if not ok:
            mis.append({"key": k, "gold": g, "submitted": s})
    return m, n, mis, s_sum


def main():
    args = V.main_args()
    sub = args.submission
    spec = V.read_json(os.path.join(REF, "spec.json"))
    g_sum = V.read_json(os.path.join(REF, "summary.json")) or {}
    res = {"branch": {}, "merge": {}, "hard_checks": {}}
    tot = {"branch": [0, 0], "merge": [0, 0]}
    sub_tables = {}
    for t in spec["tables"]:
        m, n, mis, rows = table_score(t, sub)
        sub_tables[t["file"]] = rows
        tot[t["role"]][0] += m
        tot[t["role"]][1] += n
        res[t["role"]][t["file"]] = {"matched": m, "total": n, "mismatches": mis[:args.show]}
    roles = spec.get("summary_roles", {})
    s_sum = {}
    for role in ("branch", "merge"):
        m, n, mis, s_sum = summary_score(roles, sub, role, g_sum)
        if n:
            tot[role][0] += m
            tot[role][1] += n
            res[role]["summary.json"] = {"matched": m, "total": n, "mismatches": mis}
    for h in spec.get("hard", []):
        name = h["name"]
        if h["type"] == "present":
            res["hard_checks"][name] = all(os.path.exists(os.path.join(sub, f)) for f in h["files"])
        elif h["type"] == "pairwise_ic":
            rows = sub_tables.get(h["file"]) or V.read_rows(os.path.join(sub, h["file"])) or []
            bal = defaultdict(float)
            for r in rows:
                bal[(r.get("entity"), r.get("counterparty"), r.get("account"))] += V.num(r.get(h["value"]))
            ok = bool(rows)
            for (e, cp, a), v in bal.items():
                for ra, pa in PAIRS:
                    if a == ra and abs(v + bal.get((cp, e, pa), 0.0)) > h.get("tol", 1.0):
                        ok = False
            res["hard_checks"][name] = ok
        elif h["type"] == "summary_identity":
            # sum of terms (with signs) must equal target
            try:
                lhs = sum(sg * V.num(s_sum.get(k)) for k, sg in h["terms"])
                ok = abs(lhs - V.num(s_sum.get(h["target"]))) <= h.get("tol", 1.0)
            except Exception:
                ok = False
            res["hard_checks"][name] = ok
        elif h["type"] == "table_sum_equals_summary":
            rows = sub_tables.get(h["file"]) or []
            try:
                tsum = defaultdict(float)
                for r in rows:
                    tsum[r.get(h["group"])] += V.num(r.get(h["value"]))
                ok = bool(rows)
                for grp, key in h["map"].items():
                    if abs(tsum.get(grp, 0.0) - V.num(s_sum.get(key))) > h.get("tol", 1.0):
                        ok = False
            except Exception:
                ok = False
            res["hard_checks"][name] = ok
    b = V.frac(*tot["branch"]) if tot["branch"][1] else 1.0
    mg = V.frac(*tot["merge"])
    res["branch"]["score"] = round(b, 4)
    res["merge"]["score"] = round(mg, 4)
    res["full_success"] = bool(all(res["hard_checks"].values()) and tot["branch"][0] == tot["branch"][1]
                               and tot["merge"][0] == tot["merge"][1])
    V.emit(res, args.json_out)


if __name__ == "__main__":
    main()
