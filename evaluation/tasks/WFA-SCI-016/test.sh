#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
python3 -I /tests/verify.py --submission /workspace/submission --reference /tests/reference --json /logs/verifier/details.json
python3 -I /tests/reward.py /logs/verifier/details.json
