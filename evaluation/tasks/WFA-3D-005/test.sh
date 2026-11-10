#!/bin/bash
# WorkflowArena CDC verifier entry (v0.2). Grading logic is the original rubric_score.py
# (tests/checks.py deterministic items + Gemini-3.8-Flash judge for the rest; configure WORKFLOWARENA_JUDGE_CONFIG or GEMINI_API_KEY).
# Wrapper rules: inputs and the statement come from /tests (not from the agent environment);
# if any rubric item could not be graded (judge unreachable, grader crash) no reward is written and the
# script exits non-zero; reward.json keeps numbers only, the full report goes to details.json.
set -uo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json /logs/verifier/details.json
export WS_INPUT="${WS_INPUT:-/tests/public_input}" WS_INSTR="${WS_INSTR:-/tests/instruction.md}"
cd /tests
python3 /tests/rubric_score.py
rc=$?
python3 - "$rc" <<'EOF'
import json, sys
from pathlib import Path
log = Path("/logs/verifier")
rj, rt = log / "reward.json", log / "reward.txt"
if not rj.exists():
    rt.unlink(missing_ok=True)
    sys.exit("rubric_score.py wrote no reward.json")
rep = json.loads(rj.read_text())
(log / "details.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2))
if int(sys.argv[1]) != 0 or rep.get("grader_error") or rep.get("n_ungraded"):
    rj.unlink(); rt.unlink(missing_ok=True)
    sys.exit(f"grading incomplete (rc={sys.argv[1]}, n_ungraded={rep.get('n_ungraded')}, "
             f"grader_error={rep.get('grader_error')}); no reward written")
num = {k: (float(v) if isinstance(v, bool) else v) for k, v in rep.items()
       if isinstance(v, (int, float)) and k != "items"}
rj.write_text(json.dumps(num, indent=1))
print(json.dumps(num))
EOF
