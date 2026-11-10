#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
python3 -I /tests/grade_entry.py /workspace/state.db /workspace/submission \
        --json /logs/verifier/details.json

