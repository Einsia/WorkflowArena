#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json /logs/verifier/details.json /logs/verifier/acceptance.json /logs/verifier/grading_error.json
python3 /tests/verify.py /workspace/submission --out /logs/verifier/details.json
python3 /tests/reward.py /logs/verifier/details.json
python3 -I -B /tests/acceptance.py
