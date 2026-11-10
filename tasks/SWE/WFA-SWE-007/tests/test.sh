#!/bin/bash
set -uo pipefail
bash /tests/run_native.sh
native_exit=$?
python3 -I -B /tests/normalize_score.py SWE-FEAT "$native_exit"
