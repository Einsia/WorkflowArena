#!/usr/bin/env python3
"""Turn verify.py output into Harbor rewards (WorkflowArena competition convention)."""
import json, sys
r = json.load(open(sys.argv[1]))
fr = []
for name, t in r["tracks"].items():
    rk = t.get("ranking") or {}
    fr.append(rk.get("fraction_of_official_beaten") if t.get("valid") else 0.0)
reward = 0.0 if not r.get("valid") or any(f is None for f in fr) else sum(fr) / len(fr)
out = {"reward": reward, "valid": float(bool(r.get("valid")))}
for name, h in r.get("headline", {}).items():
    if h.get("value") is not None:
        out[f"{name}_{h['primary']}"] = h["value"]
    if h.get("rank") is not None:
        out[f"{name}_rank"] = h["rank"]
        out[f"{name}_field_size"] = h["field_size"]
open("/logs/verifier/reward.json", "w").write(json.dumps(out))
open("/logs/verifier/reward.txt", "w").write(f"{reward}\n")
print(json.dumps(out))
