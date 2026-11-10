#!/bin/bash
set -uo pipefail
bash /tests/run_native.sh
native_exit=$?
python3 -I -B /tests/normalize_score.py OPS-XSYS "$native_exit"
