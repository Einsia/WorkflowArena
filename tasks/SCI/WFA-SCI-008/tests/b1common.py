"""Shared scoring helpers for B1 competition tasks (stdlib only).

Copied verbatim into each task's tests/ directory so every bundle is self-contained.
Metric definitions mirror the official SAMPL analysis scripts
(x = predicted, y = experimental; ME = mean(pred - exp); R2 = Pearson r^2 from
linregress(pred, exp); slope = linregress(pred, exp).slope; Kendall tau = tau-b).
"""
import csv
import json
import math
import os
import random


# ---------------------------------------------------------------- parsing

def read_sections(path, section_names):
    """Parse a SAMPL-style submission file into {section: [lines]}.

    Lines starting with '#' are comments. A section starts at a line equal to
    '<Name>:' (case-insensitive, trailing text after ':' kept as first line).
    """
    names = {s.lower(): s for s in section_names}
    out = {s: [] for s in section_names}
    cur = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw in fh:
            line = raw.rstrip("\n").rstrip("\r")
            if line.lstrip().startswith("#"):
                continue
            stripped = line.strip()
            head = stripped.split(":", 1)[0].strip().lower() if ":" in stripped else None
            if head is not None and head in names and stripped.lower().startswith(head):
                cur = names[head]
                rest = stripped.split(":", 1)[1].strip()
                if rest:
                    out[cur].append(rest)
                continue
            if cur is not None and stripped:
                out[cur].append(stripped)
    return out


def split_row(line):
    return [c.strip() for c in line.split(",")]


def to_float(s):
    if s is None:
        return None
    s = str(s).strip()
    if s == "" or s.lower() in ("nan", "none", "na"):
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    if math.isnan(v) or math.isinf(v):
        return None
    return v


def read_csv_dicts(path, delimiter=","):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter=delimiter))


# ---------------------------------------------------------------- metrics

def _mean(v):
    return sum(v) / len(v)


def rmse(pred, exp):
    return math.sqrt(_mean([(p - e) ** 2 for p, e in zip(pred, exp)]))


def mae(pred, exp):
    return _mean([abs(p - e) for p, e in zip(pred, exp)])


def me(pred, exp):
    return _mean([p - e for p, e in zip(pred, exp)])


def rmse_centered(pred, exp):
    """RMSE after removing the mean signed error (D3R/SAMPL 'RMSEc')."""
    d = [p - e for p, e in zip(pred, exp)]
    m = _mean(d)
    return math.sqrt(_mean([(x - m) ** 2 for x in d]))


def pearson(x, y):
    mx, my = _mean(x), _mean(y)
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    if sxx == 0 or syy == 0:
        return float("nan")
    return sxy / math.sqrt(sxx * syy)


def r2(pred, exp):
    r = pearson(pred, exp)
    return r * r if r == r else float("nan")


def slope(pred, exp):
    mx, my = _mean(pred), _mean(exp)
    sxx = sum((a - mx) ** 2 for a in pred)
    if sxx == 0:
        return float("nan")
    return sum((a - mx) * (b - my) for a, b in zip(pred, exp)) / sxx


def kendall_tau_b(x, y):
    n = len(x)
    conc = disc = tx = ty = 0
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[i] - x[j]
            dy = y[i] - y[j]
            if dx == 0 and dy == 0:
                continue
            if dx == 0:
                tx += 1
            elif dy == 0:
                ty += 1
            elif (dx > 0) == (dy > 0):
                conc += 1
            else:
                disc += 1
    denom = math.sqrt((conc + disc + tx) * (conc + disc + ty))
    if denom == 0:
        return float("nan")
    return (conc - disc) / denom


def _rankdata(v):
    order = sorted(range(len(v)), key=lambda i: v[i])
    ranks = [0.0] * len(v)
    i = 0
    while i < len(v):
        j = i
        while j + 1 < len(v) and v[order[j + 1]] == v[order[i]]:
            j += 1
        r = (i + j) / 2.0 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = r
        i = j + 1
    return ranks


def spearman(x, y):
    return pearson(_rankdata(x), _rankdata(y))


def r2_score(y_true, y_pred):
    """Coefficient of determination (sklearn convention)."""
    m = _mean(y_true)
    ss_res = sum((t - p) ** 2 for t, p in zip(y_true, y_pred))
    ss_tot = sum((t - m) ** 2 for t in y_true)
    return 1 - ss_res / ss_tot if ss_tot else float("nan")


def standard_stats(pred, exp):
    return {
        "RMSE": rmse(pred, exp),
        "MAE": mae(pred, exp),
        "ME": me(pred, exp),
        "R2": r2(pred, exp),
        "slope": slope(pred, exp),
        "kendall_tau": kendall_tau_b(pred, exp),
    }


# ---------------------------------------------------------------- ranking

def rank_against(value, field_values, lower_is_better=True, eps=1e-9):
    """Rank of `value` if inserted into the official field.

    rank = 1 + number of official entries strictly better; field_size = len(field)+1.
    Ties count in the candidate's favour (same convention as competition ranking).
    """
    vals = [v for v in field_values if v is not None and v == v]
    if value is None or value != value:
        return {"rank": None, "field_size": len(vals) + 1, "percentile_beaten": None}
    tol = eps * max(1.0, abs(value))
    better = sum(1 for v in vals if (v < value - tol if lower_is_better else v > value + tol))
    worse = sum(1 for v in vals if (v > value + tol if lower_is_better else v < value - tol))
    return {
        "rank": better + 1,
        "field_size": len(vals) + 1,
        "official_entries": len(vals),
        "fraction_of_official_beaten": (worse / len(vals)) if vals else None,
    }


def load_field(path, track=None, metric=None, track_col="track", only_ranked=True):
    rows = read_csv_dicts(path)
    out = []
    for r in rows:
        if track is not None and r.get(track_col) != track:
            continue
        if only_ranked and str(r.get("ranked", "True")).strip().lower() in ("false", "0", "no"):
            continue
        out.append(to_float(r[metric]))
    return out


# ---------------------------------------------------------------- negative controls

def write_sampl_file(path, rows, name="control", category="Other", extra_sections=None):
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("Predictions:\n")
        for r in rows:
            fh.write(",".join("" if c is None else str(c) for c in r) + "\n")
        fh.write("\nName:\n%s\n\nSoftware:\nnone\n\nCategory:\n%s\n\nMethod:\ncontrol submission\n" % (name, category))
        if extra_sections:
            for k, v in extra_sections.items():
                fh.write("\n%s:\n%s\n" % (k, v))


def seeded_rng(seed=12345):
    return random.Random(seed)


def dump(result, out_path=None):
    s = json.dumps(result, indent=2, ensure_ascii=False, default=lambda o: None)
    if out_path:
        os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(s + "\n")
    print(s)
