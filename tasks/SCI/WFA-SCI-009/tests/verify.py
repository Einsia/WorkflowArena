#!/usr/bin/env python3
"""Generic numeric verifier for paper-repro tasks (A1).

Usage:
  python3 -I verify.py --submission <dir-with-outputs> [--spec <spec.json>] [--json out.json]

spec.json (next to this file under reference/) lists targets. Each target:
  id, file (CSV the solver must write inside <submission>/outputs/), keys (key columns),
  value (value column in the submission), gold (gold CSV path relative to spec),
  pass_fraction (fraction of gold rows that must be within tolerance for the target to pass).
Gold CSV columns: key columns..., value, tol_abs, tol_rel  (optional: weight)
A gold row passes if |pred - gold| <= max(tol_abs, tol_rel*|gold|).
Optional per-target "mode": "points" (default) or "abs_le"/"abs_ge" handled via tol columns only.
Missing rows / unparsable values count as failures. Extra rows are ignored.
Exit code 0 always; overall result is in the printed JSON ("task_success").
"""
import argparse, csv, json, math, os, sys


def norm_key(v):
    v = (v or "").strip()
    try:
        f = float(v) + 0.0  # normalise -0.0
        return ("%.10g" % f)
    except ValueError:
        return v.lower()


def load_csv(path):
    with open(path, newline="") as fh:
        rows = list(csv.DictReader(fh))
    return rows


def to_float(x):
    try:
        f = float(str(x).strip())
        if math.isnan(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def score_target(t, spec_dir, sub_dir):
    gold = load_csv(os.path.join(spec_dir, t["gold"]))
    keys = t["keys"]
    vcol = t.get("value", "value")
    out_path = os.path.join(sub_dir, "outputs", t["file"])
    res = {"id": t["id"], "file": t["file"], "n_gold": len(gold), "n_pass": 0,
           "missing": 0, "failures": []}
    pred = {}
    if os.path.exists(out_path):
        try:
            for r in load_csv(out_path):
                k = tuple(norm_key(r.get(c)) for c in keys)
                pred[k] = r.get(vcol)
        except Exception as e:  # malformed CSV
            res["error"] = "unreadable submission csv: %s" % e
    else:
        res["error"] = "missing file"
    wsum = 0.0
    wpass = 0.0
    for g in gold:
        k = tuple(norm_key(g.get(c)) for c in keys)
        w = to_float(g.get("weight")) or 1.0
        wsum += w
        gv = float(g["value"])
        ta = to_float(g.get("tol_abs")) or 0.0
        tr = to_float(g.get("tol_rel")) or 0.0
        tol = max(ta, tr * abs(gv))
        pv = to_float(pred.get(k)) if k in pred else None
        if pv is None:
            res["missing"] += 1
            res["failures"].append({"key": list(k), "gold": gv, "pred": None})
            continue
        if abs(pv - gv) <= tol:
            res["n_pass"] += 1
            wpass += w
        else:
            res["failures"].append({"key": list(k), "gold": gv, "pred": pv, "tol": tol})
    res["score"] = (wpass / wsum) if wsum else 0.0
    res["pass_fraction_required"] = t.get("pass_fraction", 1.0)
    res["passed"] = res["score"] + 1e-12 >= res["pass_fraction_required"]
    res["failures"] = res["failures"][:20]
    return res


def main():
    ap = argparse.ArgumentParser()
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument("--submission", required=True)
    ap.add_argument("--spec", default=os.path.join(here, "reference", "spec.json"))
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    spec = json.load(open(a.spec))
    spec_dir = os.path.dirname(os.path.abspath(a.spec))
    results = [score_target(t, spec_dir, a.submission) for t in spec["targets"]]
    n_pass = sum(r["passed"] for r in results)
    summary = {
        "task_id": spec.get("task_id"),
        "targets_passed": n_pass,
        "targets_total": len(results),
        "mean_target_score": sum(r["score"] for r in results) / max(1, len(results)),
        "task_success": n_pass == len(results),
        "targets": results,
    }
    txt = json.dumps(summary, indent=1)
    if a.json:
        open(a.json, "w").write(txt)
    print(txt)


if __name__ == "__main__":
    main()
