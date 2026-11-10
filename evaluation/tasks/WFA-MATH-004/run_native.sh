#!/bin/bash
# Verifier entry: grade only the collected files inside this image's own clean, prebuilt checkout.
set -uo pipefail
mkdir -p /logs/verifier
rm -f /logs/verifier/reward.txt /logs/verifier/reward.json
cd /workspace
python3 /tests/grade_lean.py grade --spec /tests/spec.json --workspace /workspace --out-dir /logs/verifier

