#!/usr/bin/env python3
"""WorkflowArena CONTRACT-SURVEY verifier (self-contained, stdlib only).

Usage:
  python3 verify.py SUBMISSION_DIR [--json OUT.json]

SUBMISSION_DIR must contain:
  deal_points.csv  columns: agreement,deal_point,answer
                   (multi-select answers: options joined with " | ")
  answers.json     {"M01": <answer>, ...}

Scores (all in [0,1]):
  branch        mean per-cell score over all agreement x deal-point cells of the
                reference table; single-select = exact match, multi-select = set F1.
  merge         fraction of merge questions answered exactly right.
  merge_partial mean partial credit (lists: set F1; option counts: fraction of
                options with the exact count; groups: co-membership pair F1;
                integers: exact).
  consistency   fraction of merge questions whose submitted answer equals the
                answer recomputed mechanically from the submitter's OWN table
                (diagnostic; not part of full_success).
  full_success  branch >= BRANCH_MIN and merge >= MERGE_MIN (see reference/grading.json).

A malformed submission (deal_points.csv / answers.json that cannot be decoded as UTF-8 or parsed,
or a submission file that is a symbolic link or resolves into the verifier's directory) is invalid: it is graded as an empty
submission (all scores 0, full_success false) and reported with submission_error = 1.
"""
import csv, json, os, sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
SEP = " | "


# ---------------------------------------------------------------- tables
def load_meta(ref_dir):
    meta = json.load(open(os.path.join(ref_dir, "task_meta.json")))
    return meta  # {"agreements": [...], "deal_points": {id: {"options": [...], "multi": bool}}}


def parse_answer(raw, dpm):
    """Return (value, ok). value: str for single, frozenset for multi."""
    raw = (raw or "").strip()
    if dpm["multi"]:
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        ok = len(parts) > 0 and all(p in dpm["options"] for p in parts)
        return frozenset(p for p in parts if p in dpm["options"]), ok
    return raw, raw in dpm["options"]


def load_table(path, meta):
    table, invalid, dup = {}, [], 0
    if not os.path.exists(path):
        return table, ["missing file"]
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            row = {(k or "").strip().lower(): v for k, v in row.items()}
            a = (row.get("agreement") or "").strip().upper()
            d = (row.get("deal_point") or "").strip()
            if a not in meta["agreements"] or d not in meta["deal_points"]:
                invalid.append(f"unknown cell {a}/{d}")
                continue
            v, ok = parse_answer(row.get("answer"), meta["deal_points"][d])
            if not ok:
                invalid.append(f"non-standard answer {a}/{d}: {row.get('answer')!r}")
                if not v:
                    continue
            if (a, d) in table:
                dup += 1
            table[(a, d)] = v
    if dup:
        invalid.append(f"{dup} duplicate cells (last one kept)")
    return table, invalid


class SubmissionError(Exception):
    pass


def sub_path(sub_dir, name):
    """Path of a submission file. A file that is a symbolic link, or that resolves into the verifier's own
    directory (e.g. via a symlinked submission dir pointing at reference/), makes the submission invalid."""
    p = os.path.join(sub_dir, name)
    here = os.path.realpath(HERE)
    if os.path.islink(p) or os.path.realpath(p).startswith(here + os.sep):
        raise SubmissionError(f"{name} is a symbolic link or resolves into the verifier directory")
    return p


def cell_score(g, s, multi):
    if s is None:
        return 0.0
    if not multi:
        return 1.0 if g == s else 0.0
    if not g and not s:
        return 1.0
    tp = len(g & s)
    if tp == 0:
        return 0.0
    p, r = tp / len(s), tp / len(g)
    return 2 * p * r / (p + r)


# ---------------------------------------------------------------- merge engine
def _val(table, a, d):
    return table.get((a, d))


def eval_cond(c, table, a):
    if "all" in c:
        return all(eval_cond(x, table, a) for x in c["all"])
    if "any" in c:
        return any(eval_cond(x, table, a) for x in c["any"])
    if "not" in c:
        return not eval_cond(c["not"], table, a)
    v = _val(table, a, c["dp"])
    if v is None:
        return False
    if "eq" in c:
        return v == c["eq"]
    if "in" in c:
        return v in c["in"]
    if "has" in c:
        return c["has"] in v
    if "same_as" in c:
        w = _val(table, a, c["same_as"])
        return w is not None and v == w
    raise ValueError(f"bad condition {c}")


def _key(v):
    return tuple(sorted(v)) if isinstance(v, frozenset) else v


def _profile(table, a, dps):
    return tuple(_key(_val(table, a, d)) for d in dps)


def _modes(table, agrs, d):
    cnt = Counter(_key(_val(table, a, d)) for a in agrs)
    top = max(cnt.values())
    return {k for k, n in cnt.items() if n == top}


def _score(spec, table, a):
    t = spec["type"]
    if t == "count_true":
        return sum(1 for c in spec["conds"] if eval_cond(c, table, a))
    if t == "set_size":
        v = _val(table, a, spec["dp"]) or frozenset()
        return len([x for x in v if x not in spec.get("exclude", [])])
    raise ValueError(t)


def compute(q, table, agrs, meta):
    """Mechanically compute the answer to merge question q over agreements agrs."""
    op = q["op"]
    agrs = sorted(agrs)
    if op == "count":
        return sum(1 for a in agrs if eval_cond(q["cond"], table, a))
    if op == "list":
        return [a for a in agrs if eval_cond(q["cond"], table, a)]
    if op == "distribution":
        dpm = meta["deal_points"][q["dp"]]
        out = {o: 0 for o in dpm["options"]}
        for a in agrs:
            v = _val(table, a, q["dp"])
            if v is None:
                continue
            for o in (v if dpm["multi"] else [v]):
                out[o] += 1
        return out
    if op == "extremum":
        sc = {a: _score(q["score"], table, a) for a in agrs}
        best = (max if q["mode"] == "max" else min)(sc.values())
        return [a for a in agrs if sc[a] == best]
    if op == "minority":
        cnt = Counter(_key(_val(table, a, q["dp"])) for a in agrs)
        return [a for a in agrs if cnt[_key(_val(table, a, q["dp"]))] <= q["max_holders"]]
    if op == "outlier":
        modes = {d: _modes(table, agrs, d) for d in q["dps"]}
        dev = {a: sum(1 for d in q["dps"] if _key(_val(table, a, d)) not in modes[d]) for a in agrs}
        return [a for a in agrs if dev[a] >= q["min_dev"]]
    if op == "groups":
        g = {}
        for a in agrs:
            g.setdefault(_profile(table, a, q["dps"]), []).append(a)
        return sorted(sorted(v) for v in g.values() if len(v) >= 2)
    if op == "n_profiles":
        return len({_profile(table, a, q["dps"]) for a in agrs})
    if op == "most_similar":
        t = q["target"]
        if t not in agrs:
            return None
        sim = {a: sum(1 for d in q["dps"] if _val(table, a, d) is not None and _val(table, a, d) == _val(table, t, d))
               for a in agrs if a != t}
        best = max(sim.values())
        return [a for a in sorted(sim) if sim[a] == best]
    raise ValueError(op)


# ---------------------------------------------------------------- answer scoring
def _norm_list(x):
    if not isinstance(x, list):
        return None
    return sorted({str(i).strip().upper() for i in x})


def score_answer(q, gold, sub):
    """Return (exact, partial)."""
    op = q["op"]
    if sub is None:
        return 0.0, 0.0
    if op in ("count", "n_profiles"):
        try:
            ok = int(sub) == gold and float(sub) == int(sub)
        except Exception:
            ok = False
        return float(ok), float(ok)
    if op in ("list", "extremum", "minority", "outlier", "most_similar"):
        s = _norm_list(sub)
        if s is None:
            return 0.0, 0.0
        g = set(gold); s = set(s)
        if g == s:
            return 1.0, 1.0
        if not g or not s:
            return 0.0, 0.0
        tp = len(g & s)
        return 0.0, (0.0 if tp == 0 else 2 * tp / (len(g) + len(s)))
    if op == "distribution":
        if not isinstance(sub, dict):
            return 0.0, 0.0
        try:
            sub = {str(k).strip(): int(v) for k, v in sub.items()}
        except Exception:
            return 0.0, 0.0
        extra = [k for k, v in sub.items() if k not in gold and v != 0]
        right = sum(1 for k in gold if sub.get(k, 0) == gold[k])
        exact = float(right == len(gold) and not extra)
        return exact, right / (len(gold) + len(extra))
    if op == "groups":
        if not isinstance(sub, list) or not all(isinstance(x, list) for x in sub):
            return 0.0, 0.0
        sg = {frozenset(_norm_list(x)) for x in sub if len(set(_norm_list(x))) >= 2}
        gg = {frozenset(x) for x in gold}
        if sg == gg:
            return 1.0, 1.0
        pairs = lambda G: {frozenset((a, b)) for grp in G for a in grp for b in grp if a < b}
        gp, sp = pairs(gg), pairs(sg)
        if not gp or not sp:
            return 0.0, 0.0
        tp = len(gp & sp)
        return 0.0, (0.0 if tp == 0 else 2 * tp / (len(gp) + len(sp)))
    raise ValueError(op)


def same_answer(q, a, b):
    try:
        return score_answer(q, a, b)[0] == 1.0
    except Exception:
        return False


# ---------------------------------------------------------------- main
def evaluate(sub_dir, ref_dir=None):
    ref_dir = ref_dir or os.path.join(HERE, "reference")
    meta = load_meta(ref_dir)
    grading = json.load(open(os.path.join(ref_dir, "grading.json")))
    spec = json.load(open(os.path.join(ref_dir, "merge_spec.json")))
    gold_table, _ = load_table(os.path.join(ref_dir, "deal_points.csv"), meta)
    gold_ans = json.load(open(os.path.join(ref_dir, "answers.json")))
    sub_error = None
    try:
        sub_table, invalid = load_table(sub_path(sub_dir, "deal_points.csv"), meta)
        ans_path = sub_path(sub_dir, "answers.json")
    except (SubmissionError, UnicodeError, csv.Error, OSError, ValueError) as e:
        sub_error = f"invalid submission: {type(e).__name__}: {str(e)[:200]}"
    sub_ans = {}
    if sub_error is None:
        try:
            sub_ans = json.load(open(ans_path, encoding="utf-8"))
            if not isinstance(sub_ans, dict):
                sub_ans = {}
        except UnicodeError as e:
            sub_error = f"invalid submission: answers.json is not UTF-8: {str(e)[:200]}"
        except Exception:
            sub_ans = {}
            invalid.append("answers.json missing or not valid JSON")
    if sub_error is not None:   # graded as an empty submission
        sub_table, sub_ans, invalid = {}, {}, [sub_error]

    # branch
    per_dp = {}
    for (a, d), g in gold_table.items():
        s = sub_table.get((a, d))
        per_dp.setdefault(d, []).append(cell_score(g, s, meta["deal_points"][d]["multi"]))
    cells = [x for v in per_dp.values() for x in v]
    branch = sum(cells) / len(cells)
    per_agr = {}
    for (a, d), g in gold_table.items():
        per_agr.setdefault(a, []).append(cell_score(g, sub_table.get((a, d)), meta["deal_points"][d]["multi"]))

    # merge + consistency
    agrs = meta["agreements"]
    per_q, ex, pa, cons = {}, [], [], []
    for q in spec["questions"]:
        qid = q["id"]
        e, p = score_answer(q, gold_ans[qid], sub_ans.get(qid))
        own = compute(q, sub_table, agrs, meta)
        c = qid in sub_ans and same_answer(q, own, sub_ans.get(qid))
        per_q[qid] = {"exact": e, "partial": round(p, 4), "consistent_with_own_table": c}
        ex.append(e); pa.append(p); cons.append(float(c))
    merge = sum(ex) / len(ex)
    merge_partial = sum(pa) / len(pa)
    consistency = sum(cons) / len(cons)
    full = sub_error is None and branch >= grading["branch_min"] and merge >= grading["merge_min"]
    return {
        "branch": round(branch, 4),
        "merge": round(merge, 4),
        "merge_partial": round(merge_partial, 4),
        "consistency": round(consistency, 4),
        "full_success": bool(full),
        "thresholds": grading,
        "n_cells": len(cells),
        "n_merge_questions": len(ex),
        "branch_by_deal_point": {d: round(sum(v) / len(v), 4) for d, v in sorted(per_dp.items())},
        "branch_by_agreement": {a: round(sum(v) / len(v), 4) for a, v in sorted(per_agr.items())},
        "merge_by_question": per_q,
        "submission_error": int(sub_error is not None),
        "submission_warnings": invalid[:50] + ([f"... {len(invalid) - 50} more"] if len(invalid) > 50 else []),
    }


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    out = None
    if "--json" in args:
        i = args.index("--json"); out = args[i + 1]; del args[i:i + 2]
    res = evaluate(args[0])
    txt = json.dumps(res, indent=1, ensure_ascii=False)
    if out:
        open(out, "w").write(txt)
    print(json.dumps({k: res[k] for k in ("branch", "merge", "merge_partial", "consistency", "full_success", "n_cells", "n_merge_questions")}))
