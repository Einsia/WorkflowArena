#!/usr/bin/env python3
"""Harbor entry point: replay-integrity check, then the task grader, then rewards."""
import json, os, sqlite3, sys
sys.path.insert(0, "/tests")
import verify

def log_consistent(db):
    """The action log must account for the final state: every mutating row's `after`
    snapshot must match what the database now holds for that row, for the last write to
    it. A hand-edited database that bypassed the sanctioned interface fails this."""
    c = sqlite3.connect(db); c.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in c.execute(
            "SELECT seq, action, COALESCE(table_name,'') AS tn, target, after"
            " FROM action_log ORDER BY seq")]
    except sqlite3.OperationalError:
        try:
            rows = [dict(r) for r in c.execute(
                "SELECT seq, action, '' AS tn, target, after FROM action_log ORDER BY seq")]
        except sqlite3.OperationalError:
            c.close(); return True, "no action log in this task"
    last = {}
    for r in rows:
        after = json.loads(r["after"] or "null")
        recs = after if isinstance(after, list) else (
            [x for v in after.values() if isinstance(v, list) for x in v] if isinstance(after, dict) else [])
        for rec in recs:
            if isinstance(rec, dict) and "id" in rec:
                last[(r["tn"], rec["id"])] = rec
    bad = []
    for (tn, rid), rec in last.items():
        if not tn:
            continue
        try:
            cur = c.execute("SELECT * FROM %s WHERE id=?" % tn, (rid,)).fetchone()
        except sqlite3.OperationalError:
            continue
        if cur is None:
            continue
        cur = dict(cur)
        for k, v in rec.items():
            if k not in cur:
                continue
            a, b = cur[k], v
            if isinstance(a, float) or isinstance(b, float):
                try:
                    if abs(float(a) - float(b)) > 0.01: bad.append((tn, rid, k, b, a))
                except (TypeError, ValueError): pass
            elif a != b:
                bad.append((tn, rid, k, b, a))
    c.close()
    return (not bad), ("final state diverges from the action log: %s" % bad[:5] if bad else "")

db, sub = sys.argv[1], sys.argv[2]
ok, why = log_consistent(db)
res = verify.grade(db, sub)
if not ok:
    res["strict"] = 0
    res["F"] = dict(res.get("F", {}), ok=False, total=res["F"]["total"] + 1)
    res.setdefault("checks", []).append(
        {"id": "f_action_log_consistent", "dim": "F", "passed": False, "error": why,
         "catches": "state_tampering"})
reward = float(res["strict"])
out = {"reward": reward, "strict": reward,
       "G_passed": res["G"]["passed"], "G_total": res["G"]["total"],
       "P_passed": res["P"]["passed"], "P_total": res["P"]["total"],
       "F_passed": res["F"]["passed"], "F_total": res["F"]["total"],
       "intermediate_failure": float(bool(res.get("intermediate_failure"))),
       "completion_score": res.get("completion_score", 0.0)}
if "outcome_class" in res:
    out["outcome_" + res["outcome_class"]] = 1.0
open("/logs/verifier/reward.json", "w").write(json.dumps(out))
open("/logs/verifier/reward.txt", "w").write("%s\n" % reward)
if "--json" in sys.argv:
    json.dump(res, open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1)
print(json.dumps(out, indent=1))
