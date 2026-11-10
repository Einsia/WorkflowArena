#!/usr/bin/env python3
"""SIMCO verify.py JSON -> Harbor rewards (WorkflowArena finance/simco convention).
reward.txt  = full_success (0/1) exactly as decided by the original verify.py;
reward.json = full_success, branch_score, merge_score, hard checks and the other raw counters (numbers only).
  reward.py DETAILS.json
  reward.py --submission-error STDERR_FILE     (verify.py crashed on the submission -> 0)"""
import json
import re
import sys

OUT = "/logs/verifier/"


def key(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def flatten(prefix, x, out):
    if isinstance(x, bool):
        out[key(prefix)] = float(x)
    elif isinstance(x, (int, float)):
        out[key(prefix)] = float(x)
    elif isinstance(x, dict):
        for k, v in x.items():
            flatten(prefix + "_" + k, v, out)
    elif isinstance(x, list) and len(x) == 2 and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                                    for v in x):
        out[key(prefix + "_matched")] = float(x[0])
        out[key(prefix + "_total")] = float(x[1])
    # other lists (mismatch listings) are diagnostics only and stay in details.json


def write(out):
    open(OUT + "reward.json", "w").write(json.dumps(out))
    open(OUT + "reward.txt", "w").write("%s\n" % out["reward"])
    print(json.dumps(out))


def main():
    if sys.argv[1] == "--submission-error":
        write({"reward": 0.0, "full_success": 0.0, "branch_score": 0.0, "merge_score": 0.0,
               "submission_error": 1.0})
        return
    r = json.load(open(sys.argv[1]))
    full = bool(r["full_success"])
    hard = r.get("hard_checks", {})
    out = {"reward": float(full), "full_success": float(full),
           "branch_score": float(r["branch"]["score"]), "merge_score": float(r["merge"]["score"]),
           "hard_checks_passed": float(sum(bool(v) for v in hard.values())),
           "hard_checks_total": float(len(hard)), "submission_error": 0.0}
    for k, v in hard.items():
        out[key("hard_" + k)] = float(bool(v))
    for sec in ("branch", "merge"):
        extra = {}
        flatten(sec, {k: v for k, v in r[sec].items() if k != "score"}, extra)
        out.update({k: v for k, v in extra.items() if k not in out})
    write(out)


if __name__ == "__main__":
    main()
