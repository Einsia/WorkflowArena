#!/usr/bin/env python3
"""Generic CSV-target verifier for A2 paper-repro tasks.

Usage: python3 -I verify.py --submission <dir with model CSVs> [--reference <dir>] [--json out.json]

Reads <reference>/targets.json:
{
  "task_id": "...",
  "full_success": {"min_targets_passed": N}  # default: all targets
  "targets": [
    {"id": "T1", "file": "T1_name.csv",          # file expected in submission dir AND gold file in reference dir
     "mode": "cells",                             # cells | series
     "keys": ["col", ...],                        # join keys (string-normalized; numeric keys rounded)
     "values": {"col": {"rtol": 0.1, "atol": 0.0, "log10_atol": null}},   # or {"interval": ["lo_col","hi_col"]}
     "pass_frac": 0.9},                           # fraction of gold cells within tolerance needed to pass
    {"id": "T2", "file": "T2.csv", "mode": "series",
     "keys": ["year"], "value": "gmst", "group": null,   # optional group column -> metric computed per group, averaged
     "corr_min": 0.9, "rmse_max": 0.1}
  ]
}
Score per target in [0,1]; pass per target bool; overall success bool. Gold values are never printed.
"""
import argparse, csv, json, math, os, sys

def norm_key(v):
    s = str(v).strip()
    try:
        f = float(s)
        if math.isfinite(f):
            return repr(round(f, 6))
    except ValueError:
        pass
    return s.lower()

def read_csv(path):
    with open(path, newline='', encoding='utf-8-sig') as fh:
        rows = list(csv.DictReader(fh))
    return [{(k or '').strip(): (v.strip() if isinstance(v, str) else v) for k, v in r.items()} for r in rows]

def fnum(x):
    try:
        f = float(x)
        return f if math.isfinite(f) else None
    except (TypeError, ValueError):
        return None

def index(rows, keys):
    out = {}
    for r in rows:
        if any(k not in r for k in keys):
            raise KeyError('missing key column(s) %s' % [k for k in keys if k not in r])
        out[tuple(norm_key(r[k]) for k in keys)] = r
    return out

def within(g, s, tol, grow=None):
    if s is None:
        return False
    if tol.get('interval') is not None:   # gold row supplies [lo, hi] columns; pass if lo <= sub <= hi
        lo, hi = fnum(grow.get(tol['interval'][0])), fnum(grow.get(tol['interval'][1]))
        return lo is not None and hi is not None and lo <= s <= hi
    if tol.get('log10_atol') is not None:
        if g <= 0 or s <= 0:
            return False
        return abs(math.log10(s) - math.log10(g)) <= tol['log10_atol']
    return abs(s - g) <= tol.get('atol', 0.0) + tol.get('rtol', 0.0) * abs(g)

def score_cells(t, gold, sub):
    gi, si = index(gold, t['keys']), index(sub, t['keys'])
    n = ok = 0
    for k, gr in gi.items():
        for col, tol in t['values'].items():
            g = fnum(gr.get(col))
            if g is None:
                continue
            n += 1
            sr = si.get(k)
            if sr is not None and within(g, fnum(sr.get(col)), tol, gr):
                ok += 1
    frac = ok / n if n else 0.0
    return frac, frac >= t.get('pass_frac', 1.0), {'cells': n, 'cells_ok': ok}

def pearson(a, b):
    n = len(a)
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a); vb = sum((y - mb) ** 2 for y in b)
    if va == 0 or vb == 0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / math.sqrt(va * vb)

def score_series(t, gold, sub):
    grp = t.get('group')
    keys = t['keys'] + ([grp] if grp else [])
    gi, si = index(gold, keys), index(sub, keys)
    groups = {}
    for k, gr in gi.items():
        g = fnum(gr.get(t['value']))
        if g is None:
            continue
        gname = k[-1] if grp else '_'
        s = fnum(si[k].get(t['value'])) if k in si else None
        groups.setdefault(gname, []).append((g, s))
    per, passes = {}, []
    for gname, pairs in groups.items():
        cov = sum(1 for _, s in pairs if s is not None) / len(pairs)
        pp = [(g, s) for g, s in pairs if s is not None]
        if len(pp) < 3 or cov < t.get('min_coverage', 0.95):
            per[gname] = {'coverage': cov, 'pass': False}; passes.append(False); continue
        gs, ss = [p[0] for p in pp], [p[1] for p in pp]
        r = pearson(gs, ss); rmse = math.sqrt(sum((x - y) ** 2 for x, y in pp) / len(pp))
        ok = (r >= t.get('corr_min', -1)) and (rmse <= t.get('rmse_max', float('inf')))
        per[gname] = {'coverage': round(cov, 3), 'corr': round(r, 4), 'rmse': round(rmse, 5), 'pass': ok}
        passes.append(ok)
    frac = sum(passes) / len(passes) if passes else 0.0
    return frac, frac >= t.get('pass_frac', 1.0), {'groups': per}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--submission', required=True)
    ap.add_argument('--reference', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reference'))
    ap.add_argument('--json')
    a = ap.parse_args()
    spec = json.load(open(os.path.join(a.reference, 'targets.json')))
    results = []
    for t in spec['targets']:
        sp = os.path.join(a.submission, t['file'])
        res = {'id': t['id'], 'file': t['file']}
        if not os.path.exists(sp):
            res.update(score=0.0, passed=False, error='missing submission file')
        else:
            try:
                gold = read_csv(os.path.join(a.reference, t['file']))
                sub = read_csv(sp)
                fn = score_series if t.get('mode') == 'series' else score_cells
                sc, ok, det = fn(t, gold, sub)
                res.update(score=round(sc, 4), passed=bool(ok), detail=det)
            except Exception as e:  # malformed submission
                res.update(score=0.0, passed=False, error='%s: %s' % (type(e).__name__, e))
        results.append(res)
    need = spec.get('full_success', {}).get('min_targets_passed', len(results))
    npass = sum(r['passed'] for r in results)
    out = {'task_id': spec.get('task_id'), 'targets': results, 'targets_passed': npass,
           'targets_total': len(results), 'mean_score': round(sum(r['score'] for r in results) / max(1, len(results)), 4),
           'full_success': npass >= need}
    for r in results:
        print('%-6s %-40s score=%.3f pass=%s %s' % (r['id'], r['file'], r['score'], r['passed'], r.get('error', '')))
    print('TOTAL passed %d/%d  mean_score=%.3f  full_success=%s' % (npass, len(results), out['mean_score'], out['full_success']))
    if a.json:
        json.dump(out, open(a.json, 'w'), indent=1)
    return 0

if __name__ == '__main__':
    sys.exit(main())
