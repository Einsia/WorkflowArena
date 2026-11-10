#!/bin/bash
# WorkflowArena sci-pr verifier (separate image). The agent's repository directory arrives as the artifact.
# Flow (same commands as the original sci-pr controls / private/verify.sh):
#   clean agent build products -> protected-file hashes + forbidden new files/symlinks (tampered => reward 0, no build)
#   -> offline build/install (do_install) -> import check -> overlay hidden tests -> hidden tests (do_test) -> reward
# reward.txt: 1 iff build+import ok, tests exit 0, 0 failed / 0 errors, >0 passed, not tampered. reward.json adds pass_fraction.
set -uo pipefail
L=/logs/verifier
mkdir -p "$L"; rm -f "$L/reward.txt" "$L/reward.json"
for f in wfs.conf wfs-test.sh wfs_sci_pr.py protected-files.json hidden-test-files.txt; do
  [ -f "/tests/$f" ] || { echo "verifier file missing: $f" >&2; exit 2; }
done
[ -f /opt/wfs/build.sh ] && [ -f /opt/wfs/start-files.txt ] || { echo "verifier image incomplete" >&2; exit 2; }
. /tests/wfs.conf
R=$REPO_DIR
S=$L/status.txt; : > "$S"
python3 /tests/wfs_sci_pr.py pre "$R" /tests "$L" || { echo "pre-check crashed" >&2; exit 2; }
if python3 -c "import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))['tampered'] else 1)" "$L/tamper.json"; then
  echo "tampering detected -> reward 0 without building"
else
  export OPENBLAS_CORETYPE=Haswell OMP_NUM_THREADS=$OMP MKL_NUM_THREADS=$OMP OPENBLAS_NUM_THREADS=$OMP MPLBACKEND=Agg
  . /opt/wfs/build.sh
  . /tests/wfs-test.sh
  cd "$R"; ( do_install ) > "$L/install.log" 2>&1; echo "BUILD_EXIT=$?" >> "$S"; tail -n 20 "$L/install.log"
  cd "$R"; ( do_import ) > "$L/import.log" 2>&1; echo "IMPORT_EXIT=$?" >> "$S"; tail -n 3 "$L/import.log"
  python3 /tests/wfs_sci_pr.py overlay "$R" /tests || { echo "overlay failed" >&2; exit 2; }
  cd "$R"; ( export PYTEST_ADDOPTS="--junitxml=$L/junit.xml"; timeout "$TEST_TIMEOUT" bash -c '. /opt/wfs/build.sh; . /tests/wfs-test.sh; do_test' ) > "$L/test.log" 2>&1
  echo "TEST_EXIT=$?" >> "$S"; tail -n 40 "$L/test.log"
fi
python3 /tests/wfs_sci_pr.py result /tests "$L"

