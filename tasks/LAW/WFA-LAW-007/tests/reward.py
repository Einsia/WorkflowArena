#!/usr/bin/env python3
"""verify.py JSON -> Harbor rewards (WorkflowArena LEGAL/contract-survey convention).
reward.txt  = full_success of the original package (0/1): branch >= branch_min and merge >= merge_min
              (thresholds from /tests/reference/grading.json, applied by the original verify.py).
reward.json = reward, full_success, branch_score, merge_score, merge_partial, consistency, thresholds,
              counts, submission_error (1 = malformed submission graded as empty), per-agreement branch scores
              and per-question exact merge scores (numbers only)."""
import json, re, sys
r = json.load(open(sys.argv[1]))
for k in ("branch", "merge", "full_success", "thresholds"):
    if k not in r:
        sys.exit("verify output lacks " + k)
full = float(bool(r["full_success"]))
out = {"reward": full, "full_success": full,
       "branch_score": float(r["branch"]), "merge_score": float(r["merge"]),
       "merge_partial": float(r.get("merge_partial", 0.0)), "consistency": float(r.get("consistency", 0.0)),
       "branch_min": float(r["thresholds"]["branch_min"]), "merge_min": float(r["thresholds"]["merge_min"]),
       "n_cells": float(r.get("n_cells", 0)), "n_merge_questions": float(r.get("n_merge_questions", 0)),
       "n_submission_warnings": float(len(r.get("submission_warnings", []))),
       "submission_error": float(r.get("submission_error", 0))}
for a, v in sorted(r.get("branch_by_agreement", {}).items()):
    out["branch_" + re.sub(r"[^A-Za-z0-9_]+", "_", a)] = float(v)
for q, v in sorted(r.get("merge_by_question", {}).items()):
    out["merge_" + re.sub(r"[^A-Za-z0-9_]+", "_", q) + "_exact"] = float(v.get("exact", 0.0))
open("/logs/verifier/reward.json", "w").write(json.dumps(out))
open("/logs/verifier/reward.txt", "w").write("%s\n" % out["reward"])
print(json.dumps({k: out[k] for k in ("reward", "branch_score", "merge_score", "merge_partial", "consistency")}))
