#!/usr/bin/env python3
"""verify.py JSON -> Harbor rewards (WorkflowArena paper-repro convention).
reward.txt = fraction of targets passed (per-target pass decided by the original verify.py);
reward.json adds full_success (original rule) and per-target pass/score."""
import json, re, sys
r = json.load(open(sys.argv[1]))
t = r["targets"]
n = len(t)
if n == 0:
    sys.exit("no targets in verify output")
npass = sum(bool(x.get("passed")) for x in t)
full = r.get("full_success", r.get("task_success"))
out = {"reward": npass / n, "full_success": float(bool(full)), "targets_passed": float(npass),
       "targets_total": float(n),
       "mean_target_score": float(r.get("mean_score", r.get("mean_target_score", 0.0)))}
for x in t:
    k = re.sub(r"[^A-Za-z0-9_]+", "_", str(x["id"]))
    out[k + "_pass"] = float(bool(x.get("passed")))
    out[k + "_score"] = float(x.get("score") or 0.0)
open("/logs/verifier/reward.json", "w").write(json.dumps(out))
open("/logs/verifier/reward.txt", "w").write("%s\n" % out["reward"])
print(json.dumps(out))
