#!/usr/bin/env python3
"""verify.py report -> Harbor rewards (WorkflowArena LEGAL/multi-defendant convention).
reward.txt  = full_success of the original package (0/1), computed by the unchanged verify.py.
reward.json = reward, full_success, branch_score, merge_score, role_accuracy, leader_f1, consistency
              (+ art69/art74/order rates), case_all_correct, branch components and counts (numbers only).
--submission-error: verify.py crashed on the submission (grader verified on gold) -> all zeros."""
import json, sys
if sys.argv[1:] == ["--submission-error"]:
    out = {"reward": 0.0, "full_success": 0.0, "branch_score": 0.0, "merge_score": 0.0, "submission_error": 1.0}
else:
    r = json.load(open(sys.argv[1], encoding="utf-8"))
    for k in ("branch", "merge", "full_success", "case_all_correct", "n_defendants"):
        if k not in r:
            sys.exit("verify output lacks " + k)
    if not r["n_defendants"]:
        sys.exit("verify output has no graded defendants")
    b, m = r["branch"], r["merge"]
    c = m["consistency"]
    full = float(bool(r["full_success"]))
    out = {"reward": full, "full_success": full,
           "branch_score": float(b["score"]), "merge_score": float(m["score"]),
           "role_accuracy": float(m["role_accuracy"]), "leader_f1": float(m["leader_f1"]),
           "consistency": float(c["score"]), "art69_rate": float(c["art69_rate"]),
           "art74_rate": float(c["art74_rate"]), "order_rate": float(c["order_rate"]),
           "case_all_correct": float(bool(r["case_all_correct"])),
           "circumstances_micro_f1": float(b["circumstances_micro_f1"]),
           "term_within_band_frac": float(b["term_within_band_frac"]),
           "n_defendants": float(r["n_defendants"]), "n_role_items": float(m["n_role_items"]),
           "n_gold_leaders": float(m["n_gold_leaders"]), "n_art69": float(c["n_art69"]),
           "n_art74": float(c["n_art74"]), "n_order_pairs": float(c["n_order_pairs"]),
           "n_role_errors": float(len(r.get("role_errors", []))),
           "n_unknown_defendants_in_submission": float(len(r.get("unknown_defendants_in_submission", []))),
           "submission_error": 0.0}
    for k in ("charges", "articles", "circumstances", "term", "probation"):
        if b.get(k) is not None:
            out["branch_" + k] = float(b[k])
open("/logs/verifier/reward.json", "w").write(json.dumps(out))
open("/logs/verifier/reward.txt", "w").write("%s\n" % out["reward"])
print(json.dumps({k: out[k] for k in ("reward", "branch_score", "merge_score")}))
