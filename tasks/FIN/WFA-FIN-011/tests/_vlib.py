"""Shared verification helpers for SIMCO tasks (copied into each task's tests/ as _vlib.py)."""
from __future__ import annotations

import csv
import json
import os
import re
import sys
from collections import defaultdict

ABS_TOL = 5.00          # USD (or local currency unit) absolute tolerance per amount
REL_TOL = 1e-6


def tol_for(g):
    return max(ABS_TOL, REL_TOL * abs(g))


def num(x):
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    x = str(x).strip().replace(",", "")
    if x == "":
        return 0.0
    return float(x)


# Code columns are compared as strings; normalize them so that e.g. account 1000.0 (a pandas float column),
# entity " s1 " or counterparty "nan" (empty cell written by pandas) match the canonical codes 1000 / S1 / "".
CODE_COLS = {"account", "entity", "counterparty", "seller", "buyer", "responsible_entity", "counterparty_entity"}
_INT_FLOAT = re.compile(r"^[+-]?\d+\.0*$")


def norm_code(v):
    v = (v or "").strip()
    if v.lower() in ("nan", "none", "null"):
        return ""
    if _INT_FLOAT.match(v):
        v = str(int(float(v)))
    return v.upper()


def read_rows(path):
    if not os.path.exists(path):
        return None
    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = [{(k or "").strip(): (v or "").strip() for k, v in r.items()} for r in csv.DictReader(f)]
    for r in rows:
        for k in CODE_COLS & r.keys():
            r[k] = norm_code(r[k])
    return rows


def amount_of(r):
    if "amount" in r and r["amount"] != "":
        return num(r["amount"])
    return num(r.get("debit", 0)) - num(r.get("credit", 0))


def read_json(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return None


def keyed_amounts(rows, keys):
    out = defaultdict(float)
    if not rows:
        return out
    for r in rows:
        k = tuple(r.get(x, "") for x in keys)
        out[k] += amount_of(r)
    return out


def compare(gold: dict, sub: dict, tol=tol_for, count_extra=True):
    """gold/sub: key -> amount. Returns (matched, total, mismatches)."""
    keys = {k for k, v in gold.items() if abs(v) > 0.004}
    if count_extra:
        keys |= {k for k, v in sub.items() if abs(v) > 0.5}
    matched = 0
    mism = []
    for k in sorted(keys):
        g = gold.get(k, 0.0)
        s = sub.get(k, 0.0)
        if abs(g - s) <= tol(g):
            matched += 1
        else:
            mism.append({"key": list(k) if isinstance(k, tuple) else k, "gold": round(g, 2), "submitted": round(s, 2)})
    return matched, len(keys), mism


def entries_from_rows(rows, id_col="entry_id", extra_keys=()):
    ents = defaultdict(list)
    for r in rows or []:
        ents[tuple(r.get(k, "") for k in (id_col,) + tuple(extra_keys))].append(r)
    return ents


def emit(result, out=None):
    txt = json.dumps(result, indent=1, sort_keys=False)
    print(txt)
    if out:
        with open(out, "w") as f:
            f.write(txt)


def frac(a, b):
    return 1.0 if b == 0 else a / b


def main_args():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("submission", help="directory containing the deliverables")
    ap.add_argument("--json-out", default=None)
    ap.add_argument("--show", type=int, default=15, help="max mismatches to list per section")
    return ap.parse_args()
