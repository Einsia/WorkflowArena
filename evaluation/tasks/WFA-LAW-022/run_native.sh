#!/bin/bash
# Harbor verifier for a multi-defendant task: original verify.py (stdlib only, unchanged) -> reward.py.
# A missing / unreadable judgment.json is graded by verify.py itself as an empty submission (reward 0).
# If verify.py crashes on the submission (e.g. final_term given as a string), the grader is re-run on the
# packaged gold submission: if that still gives full success the crash is the submission's fault
# (reward 0, submission_error = 1); otherwise it is a platform failure (exit 1, no reward written).
# A judgment.json that is a symbolic link, or that resolves into /tests (e.g. the packaged gold control),
# is an invalid submission: reward 0, submission_error = 1.
set -uo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
SUB=/workspace/submission/judgment.json
if python3 -I -c 'import os, sys; p = sys.argv[1]; t = os.path.realpath("/tests")
sys.exit(0 if os.path.islink(p) or os.path.realpath(p).startswith(t + os.sep) else 1)' "$SUB"; then
    echo "judgment.json is a symbolic link or resolves into the verifier directory -> invalid submission, reward 0" >&2
    python3 -I /tests/reward.py --submission-error || exit 1
    exit 0
fi
if python3 -I /tests/verify.py --submission "$SUB" --out /logs/verifier/details.json \
        > /logs/verifier/verify.stdout 2> /logs/verifier/verify.stderr; then
    cat /logs/verifier/verify.stdout
    python3 -I /tests/reward.py /logs/verifier/details.json || exit 1
else
    cat /logs/verifier/verify.stderr >&2
    if python3 -I /tests/verify.py --submission /tests/controls/positive_gold.submission.json \
            --out /tmp/gold_check.json > /dev/null \
        && python3 -I -c "import json,sys; sys.exit(0 if json.load(open('/tmp/gold_check.json'))['full_success'] else 1)"; then
        echo "verify.py crashed on the submission; grader OK on the gold submission -> reward 0" >&2
        python3 -I /tests/reward.py --submission-error || exit 1
    else
        echo "grader failed on the packaged gold submission: platform failure, no reward written" >&2
        exit 1
    fi
fi

