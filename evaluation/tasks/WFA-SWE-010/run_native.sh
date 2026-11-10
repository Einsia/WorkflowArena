#!/bin/bash
# sci-pr verifier: tamper check -> clean rebuild of the collected /work -> hidden tests.
# Writes /logs/verifier/reward.txt (0/1) and reward.json (pass_fraction etc.).
set -uo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
python3 /tests/verify.py

