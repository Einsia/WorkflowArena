#!/bin/bash
# Run the storage engine's own suite so that one crash cannot erase the rest.
#
# An unrecovered panic fails the test it happens in and terminates the whole Go
# test binary, so every test after it reports nothing at all.  That matters here:
# with the engine removed, Open() returns (nil, nil) and the first dereference
# panics.  The control run measured 376 panic lines across the suite with an
# empty implementation.  A single `go test` invocation would therefore grade a
# half-finished solution as if almost nothing had been attempted.
#
# Phase 1 is one ordinary verbose run - this is the path the positive control
# measured (433 top-level tests, 2242 subtests, 0 panics, ~2 min on 16 cpus).
# Phase 2 only does something when phase 1 ended early: each top-level test
# that produced no verdict is re-run in its own process, so a crash costs one
# test instead of the tail of the suite.
#
# Output goes to stdout in `go test -v` form, which is what the grader parses.
set -u
cd /app || exit 1
export GOFLAGS=-buildvcs=false
# Do not inherit PATH from a login shell: Debian's /etc/profile overwrites PATH
# for root, which drops the golang image's /usr/local/go/bin and makes every `go`
# invocation here fail with "command not found". The group commands use `bash -c`
# rather than `bash -lc` for the same reason; this is belt and braces.
case ":$PATH:" in *:/usr/local/go/bin:*) ;; *) export PATH="/usr/local/go/bin:/go/bin:$PATH" ;; esac
command -v go >/dev/null || { echo "[run_f1] no go toolchain on PATH=$PATH"; exit 1; }
WORK=$(mktemp -d /tmp/f1.XXXXXX)
PHASE1=$WORK/phase1.txt

timeout 2400 go test -count=1 -v -timeout 35m ./tsdb/ > "$PHASE1" 2>&1
cat "$PHASE1"

# Top-level tests the suite declares, and the ones that reached a verdict.
grep -hoE '^func Test[A-Za-z0-9_]*' /app/tsdb/*_test.go | sed 's/^func //' | sort -u > "$WORK/all.txt"
grep -oE '^(=== RUN|--- (PASS|FAIL|SKIP): )[A-Za-z0-9_]*' "$PHASE1" \
    | grep -oE 'Test[A-Za-z0-9_]*$' > "$WORK/seen-run.txt"
grep -oE '^--- (PASS|FAIL|SKIP): [A-Za-z0-9_]*' "$PHASE1" \
    | grep -oE 'Test[A-Za-z0-9_]*$' | sort -u > "$WORK/verdict.txt"
comm -23 "$WORK/all.txt" "$WORK/verdict.txt" > "$WORK/missing.txt"

n=$(wc -l < "$WORK/missing.txt")
echo "[run_f1] $n of $(wc -l < "$WORK/all.txt") top-level tests reached no verdict in phase 1"
[ "$n" -eq 0 ] && exit 0

# Keep the compiler's output: when this failed during package validation the
# reason was swallowed and the log said only "does not build", which cost a
# whole validation round to diagnose.
if ! go test -count=1 -c -o "$WORK/tsdb.test" ./tsdb/ > "$WORK/build.txt" 2>&1; then
    echo "[run_f1] the test binary does not build; no per-test rerun possible"
    sed 's/^/[run_f1 build] /' "$WORK/build.txt"
    exit 1
fi

mkdir -p "$WORK/out"
# One process per test, output to its own file so parallel writers cannot
# interleave inside a verdict line, then concatenated.
( cd /app/tsdb && xargs -a "$WORK/missing.txt" -P 4 -I{} \
    bash -c 'timeout 420 "$0" -test.v -test.run "^$1\$" -test.timeout 6m > "$2/$1.txt" 2>&1' \
    "$WORK/tsdb.test" {} "$WORK/out" )
cat "$WORK/out"/*.txt 2>/dev/null
echo "[run_f1] per-test rerun complete"
exit 0
