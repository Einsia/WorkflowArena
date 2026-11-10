#!/bin/bash
# Harbor verifier for a SIMCO task: original verify.py (stdlib only) -> reward.py.
# If verify.py crashes on the submission (e.g. a non-numeric amount), the grader is re-run on the
# packaged reference answer: if that still gives full success the crash is the submission's fault
# (reward 0, submission_error = 1); otherwise it is a platform failure (exit 1, no reward written).
set -uo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
SUB=/workspace/submission
if python3 -I /tests/verify.py "$SUB" --json-out /logs/verifier/details.json \
      >/logs/verifier/verify.stdout 2>/logs/verifier/verify.stderr; then
  python3 -I /tests/reward.py /logs/verifier/details.json
  exit $?
fi
echo "verify.py failed on the submission:" >&2
tail -n 20 /logs/verifier/verify.stderr >&2
SC=$(mktemp -d)
if python3 -I /tests/verify.py /tests/reference --json-out "$SC/gold.json" >/dev/null 2>&1 \
   && python3 -I -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))["full_success"] else 1)' "$SC/gold.json"; then
  python3 -I /tests/reward.py --submission-error /logs/verifier/verify.stderr
  exit $?
fi
echo "grader self-check on the reference answer failed: platform error, no reward written" >&2
exit 1

