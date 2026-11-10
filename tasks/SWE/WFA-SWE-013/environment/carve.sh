#!/bin/bash
# Materialise the starting tree: remove the query evaluator, keep its contract.
#
# Run during image build against a pristine source tree ($1).  Three things
# happen, in this order:
#
#   1. the eight evaluator files are hollowed out — every declaration stays,
#      every function body is replaced by a return of zero values
#   2. the tests that judge the evaluator are removed (the verifier brings them
#      back after the agent has finished), as are the tests that reach into the
#      removed implementation's internals
#   3. all but three of the data-driven acceptance files are removed; the three
#      that stay are a smoke subset, and the directory cannot be emptied because
#      a retained package embeds it
#
# Zero values rather than panics: this tree initialises package-level variables
# by calling into the evaluator, so a panicking stub would die during package
# init and nothing in the tree would run at all.
set -euo pipefail
TREE=${1:?usage: carve.sh <source-tree>}
HERE=$(cd "$(dirname "$0")" && pwd)

CARVE_FILES="promql/engine.go promql/functions.go promql/value.go promql/quantile.go
promql/info.go promql/query_logger.go promql/durations.go promql/histogram_stats_iterator.go"

WHITEBOX_TESTS="promql/engine_internal_test.go promql/functions_internal_test.go
promql/durations_test.go promql/quantile_test.go
promql/histogram_stats_iterator_test.go promql/query_logger_test.go"

HIDDEN_TESTS="promql/engine_test.go promql/functions_test.go promql/value_test.go
promql/promql_test.go promql/bench_test.go"

KEEP_FIXTURES="literals.test selectors.test staleness.test"

echo "[carve] hollowing out the evaluator"
mkdir -p /tmp/stubtool && cp "$HERE/stubgen.go" /tmp/stubtool/main.go
printf 'module stubtool\n\ngo 1.21\n' > /tmp/stubtool/go.mod
( cd /tmp/stubtool && go build -o /tmp/stubgen . )
( cd "$TREE" && /tmp/stubgen $CARVE_FILES )

echo "[carve] dropping imports that only the removed bodies used"
for round in $(seq 1 10); do
    errs=$(cd "$TREE" && go build ./promql/ 2>&1 | grep "imported and not used" || true)
    [ -z "$errs" ] && { echo "[carve] imports clean after $((round-1)) rounds"; break; }
    while IFS= read -r line; do
        file=${line%%:*}
        lineno=$(echo "$line" | cut -d: -f2)
        [ -f "$TREE/$file" ] && sed -i "${lineno}s|^|// carved: |" "$TREE/$file"
    done <<< "$errs"
done

echo "[carve] removing the judging tests and the internals-pinning tests"
( cd "$TREE" && rm -f $WHITEBOX_TESTS $HIDDEN_TESTS )

echo "[carve] reducing the data-driven suite to a smoke subset"
for f in "$TREE"/promql/promqltest/testdata/*.test; do
    keep=no
    for k in $KEEP_FIXTURES; do [ "$(basename "$f")" = "$k" ] && keep=yes; done
    [ "$keep" = no ] && rm -f "$f"
done
ls "$TREE/promql/promqltest/testdata/"

echo "[carve] no VCS history in the tree (a checkout would undo the carve)"
rm -rf "$TREE/.git"
test ! -d "$TREE/.git"

echo "[carve] the tree must still compile"
( cd "$TREE" && go build ./... )
echo "[carve] done"
