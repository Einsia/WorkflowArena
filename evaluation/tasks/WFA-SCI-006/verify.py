#!/usr/bin/env python3
"""Generic verifier for B1 competition tasks with per-molecule scalar targets.

Usage:
    python3 verify.py <submission_dir> [--out result.json]

Behaviour is driven by reference/config.json next to this script. Each track:
  submission_file   file name inside <submission_dir>
  format            "sampl" (Predictions: section, comma rows: ID,value,...) or "csv"
  value_index       (sampl) column index of the predicted value in each row (0 = ID)
  id_column/value_column (csv) column names in a CSV submission
  id_prefix_filter  optional: only rows whose ID starts with one of these prefixes
  truth             csv path (relative to this script) with columns id,value[,group]
  required_ids      "all_truth" | list | csv path with column id (molecules that must be predicted)
  scored_ids        optional list restricting the scored subset
  transform         optional: "none"
  field             csv with official per-entry statistics; filtered by field_track
  primary           metric name used for ranking, lower_is_better bool
  extra_metrics     list of metric names to report

Exit code 0 even on invalid submissions; the JSON reports "valid": false and errors.

Task-local extension (comp-sampl4-hydration, P2 2026-10-23):
  success_thresholds  {metric: {"le"|"ge": x}} -> "success" block; full_success = all thresholds met
  rank_is_approximate true -> ranking blocks carry "approximate": true (truth reconstructed from FreeSolv,
                      recomputed official metrics differ by <=0.04, so near-ties can swap); ranks are reference only
  rank_metrics        extra metrics also converted to an (approximate) rank against the official field
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import b1common as C  # noqa: E402


def load_truth(track):
    rows = C.read_csv_dicts(os.path.join(HERE, track["truth"]))
    truth = {}
    for r in rows:
        v = C.to_float(r["value"])
        if v is not None:
            truth[r["id"].strip()] = v
    return truth


def required_ids(track, truth):
    req = track.get("required_ids", "all_truth")
    if req == "all_truth":
        return sorted(truth)
    if isinstance(req, list):
        return req
    rows = C.read_csv_dicts(os.path.join(HERE, req))
    return [r["id"].strip() for r in rows]


def apply_transform(track, v):
    t = track.get("transform", "none")
    if t == "none" or v is None:
        return v
    if t == "sampl7_dG_to_logP":
        # official SAMPL7 conversion: logP = round(-dG[kcal/mol]*4184 / (8.314*298.15*ln10), 2)
        import math
        return round((-v * 4184.0) / (8.314 * 298.15 * math.log(10)), 2)
    raise ValueError("unknown transform %s" % t)


def parse_submission(track, sub_dir, errors):
    path = os.path.join(sub_dir, track["submission_file"])
    if not os.path.exists(path):
        errors.append("missing file %s" % track["submission_file"])
        return {}
    preds = {}
    if track.get("format", "sampl") == "sampl":
        sec = C.read_sections(path, ["Predictions", "Name", "Software", "Category", "Method", "Ranked"])
        for line in sec["Predictions"]:
            row = C.split_row(line)
            if not row or not row[0]:
                continue
            rid = row[0]
            vi = track.get("value_index", 1)
            val = C.to_float(row[vi]) if len(row) > vi else None
            if val is None:
                continue
            if rid in preds:
                errors.append("duplicate prediction for %s" % rid)
            preds[rid] = apply_transform(track, val)
        for key in track.get("required_sections", []):
            if not sec.get(key):
                errors.append("section '%s:' missing or empty" % key)
    else:
        for r in C.read_csv_dicts(path):
            if "id_columns" in track:  # composite key, e.g. solvent_system|molecule
                rid = "|".join((r.get(c) or "").strip() for c in track["id_columns"])
            else:
                rid = (r.get(track["id_column"]) or "").strip()
            val = C.to_float(r.get(track["value_column"]))
            if rid and val is not None:
                if rid in preds:
                    errors.append("duplicate prediction for %s" % rid)
                preds[rid] = apply_transform(track, val)
    return preds


METRICS = {
    "RMSE": C.rmse,
    "MAE": C.mae,
    "ME": C.me,
    "R2": C.r2,
    "slope": C.slope,
    "kendall_tau": C.kendall_tau_b,
    "RMSEc": C.rmse_centered,
    "pearson_r": C.pearson,
    "spearman_rho": C.spearman,
}


def score_track(track, sub_dir):
    errors = []
    truth = load_truth(track)
    preds = parse_submission(track, sub_dir, errors)
    req = required_ids(track, truth)
    missing = [i for i in req if i not in preds]
    if missing:
        errors.append("missing predictions for %d required IDs: %s" % (len(missing), ",".join(missing[:20])))
    scored = track.get("scored_ids") or sorted(truth)
    ids = [i for i in scored if i in truth and i in preds]
    res = {"n_required": len(req), "n_scored": len(ids), "errors": errors}
    if errors or len(ids) < 2:
        res["valid"] = False
        return res
    p = [preds[i] for i in ids]
    e = [truth[i] for i in ids]
    names = [track["primary"]] + [m for m in track.get("extra_metrics", []) if m != track["primary"]]
    res["metrics"] = {m: METRICS[m](p, e) for m in names}
    res["per_id_error"] = {i: preds[i] - truth[i] for i in ids}
    field = C.load_field(os.path.join(HERE, track["field"]), track=track.get("field_track"),
                         metric=track["primary"], only_ranked=track.get("field_only_ranked", True))
    res["primary_metric"] = track["primary"]
    rv = res["metrics"][track["primary"]]
    if track.get("rank_round") is not None:  # official field is rounded; compare at the same precision
        rv = round(rv, track["rank_round"])
    res["ranking"] = C.rank_against(rv, field,
                                    lower_is_better=track.get("lower_is_better", True))
    if track.get("rank_is_approximate"):
        res["ranking"]["approximate"] = True
        res["ranking"]["note"] = track.get("rank_note", "approximate rank (reference only)")
    extra = {}
    for m, spec in (track.get("rank_metrics") or {}).items():  # e.g. {"MAE": {"field_col": "MAE", "lower_is_better": true}}
        if m not in res["metrics"]:
            res["metrics"][m] = METRICS[m](p, e)
        fv = C.load_field(os.path.join(HERE, track["field"]), track=track.get("field_track"),
                          metric=spec.get("field_col", m), only_ranked=track.get("field_only_ranked", True))
        v = res["metrics"][m]
        if track.get("rank_round") is not None:
            v = round(v, track["rank_round"])
        r = C.rank_against(v, fv, lower_is_better=spec.get("lower_is_better", True))
        r["approximate"] = bool(track.get("rank_is_approximate"))
        extra[m] = r
    if extra:
        res["ranking_other_metrics"] = extra
    thr = track.get("success_thresholds")
    if thr:
        checks = {}
        for m, c in thr.items():
            v = res["metrics"].get(m)
            if v is None:
                v = METRICS[m](p, e)
            ok = (v <= c["le"]) if "le" in c else (v >= c["ge"])
            checks[m] = {"value": v, "threshold": c, "pass": bool(ok)}
        res["success"] = {"checks": checks, "full_success": all(x["pass"] for x in checks.values())}
    res["valid"] = True
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("submission_dir")
    ap.add_argument("--out")
    ap.add_argument("--config", default=os.path.join(HERE, "reference", "config.json"))
    a = ap.parse_args()
    import json
    cfg = json.load(open(a.config))
    out = {"task_id": cfg["task_id"], "tracks": {}}
    for t in cfg["tracks"]:
        out["tracks"][t["name"]] = score_track(t, a.submission_dir)
    out["valid"] = all(v.get("valid") for v in out["tracks"].values())
    diag = cfg.get("consistency_diagnostic")
    if diag:  # monoprotic-acid logD consistency check (diagnostic only, not scored)
        import math
        tr = {t["name"]: t for t in cfg["tracks"]}
        P = {k: parse_submission(tr[diag[k]], a.submission_dir, []) for k in ("logP", "pKa", "logD")}
        dev = {}
        for i in P["logD"]:
            if i in P["logP"] and i in P["pKa"]:
                expect = P["logP"][i] - math.log10(1 + 10 ** (diag["pH"] - P["pKa"][i]))
                dev[i] = P["logD"][i] - expect
        out["diagnostics"] = {"logD_minus_monoprotic_acid_estimate": dev,
                              "max_abs_deviation": max((abs(v) for v in dev.values()), default=None)}
    out["full_success"] = bool(out["valid"]) and all((v.get("success") or {}).get("full_success", False)
                                                     for v in out["tracks"].values() if "success" in v or not v.get("valid"))
    out["headline"] = {k: {"primary": v.get("primary_metric"),
                           "value": (v.get("metrics") or {}).get(v.get("primary_metric")),
                           "rank": (v.get("ranking") or {}).get("rank"),
                           "field_size": (v.get("ranking") or {}).get("field_size"),
                           "rank_approximate": (v.get("ranking") or {}).get("approximate", False),
                           "full_success": (v.get("success") or {}).get("full_success")}
                       for k, v in out["tracks"].items()}
    C.dump(out, a.out)


if __name__ == "__main__":
    main()
