#!/bin/bash
# Materialise the starting tree: remove the storage engine, keep its contract.
#
# Run during image build against a pristine source tree ($1).  Four things
# happen, in this order:
#
#   1. seventeen files of the flat `tsdb` package are hollowed out - every
#      declaration stays, every function body is replaced by a return of zero
#      values.  564 bodies in total.
#   2. the imports that only the deleted bodies used are commented out, driven
#      by the compiler's own error messages
#   3. the package's tests are removed; the verifier brings them back after the
#      agent has finished, together with the binary fixtures they read
#   4. the VCS history is removed, because a checkout would undo the carve
#
# Three of the package's twenty non-test files are deliberately NOT carved:
#
#   tsdb/testutil.go           contains nothing but test fixtures
#                              (sampleTypeScenarios, requireEqualSamples,
#                              testValue, counterResetAsString ...) and is
#                              referenced by no non-test file in the repository.
#                              Carving it would leave the judging suite without
#                              its fixtures.
#   tsdb/head_other.go         //go:build !dedupelabels
#   tsdb/head_dedupelabels.go  //go:build dedupelabels
#                              stubgen clears every comment in a file, which
#                              deletes the //go:build line; both files would
#                              then join the default build and collide on
#                              (*memSeries).labels().  76 lines of two trivial
#                              helpers, kept whole.
#
# Zero values rather than panics: a panicking stub dies during package init or
# on the first dereference and takes the whole test binary with it, so the
# starting tree would report "nothing ran" instead of "assertions failed".
set -euo pipefail
TREE=${1:?usage: carve.sh <source-tree>}
HERE=$(cd "$(dirname "$0")" && pwd)

CARVE_FILES="tsdb/head.go tsdb/db.go tsdb/head_append.go tsdb/head_wal.go
tsdb/querier.go tsdb/compact.go tsdb/head_read.go tsdb/ooo_head_read.go
tsdb/block.go tsdb/exemplar.go tsdb/head_append_v2.go tsdb/isolation.go
tsdb/ooo_head.go tsdb/repair.go tsdb/tsdbblockutil.go tsdb/blockwriter.go
tsdb/ooo_isolation.go"

# Every one of these is `package tsdb`.  The package has no external test
# package at all, so there is no second, contract-level suite to leave behind:
# the whole suite is removed here and restored by the verifier.
HIDDEN_TESTS="tsdb/block_test.go tsdb/blockwriter_test.go tsdb/compact_test.go
tsdb/db_append_v2_test.go tsdb/db_test.go tsdb/example_test.go
tsdb/exemplar_test.go tsdb/head_append_v2_test.go tsdb/head_bench_test.go
tsdb/head_read_test.go tsdb/head_test.go tsdb/isolation_test.go
tsdb/label_values_bench_test.go tsdb/mocks_test.go tsdb/ooo_head_read_test.go
tsdb/ooo_head_test.go tsdb/ooo_isolation_test.go tsdb/querier_bench_test.go
tsdb/querier_test.go tsdb/repair_test.go"

export GOFLAGS=-buildvcs=false

echo "[carve] hollowing out the storage engine"
mkdir -p /tmp/stubtool && cp "$HERE/stubgen.go" /tmp/stubtool/main.go
printf 'module stubtool\n\ngo 1.21\n' > /tmp/stubtool/go.mod
( cd /tmp/stubtool && go build -o /tmp/stubgen . )
( cd "$TREE" && /tmp/stubgen $CARVE_FILES )

echo "[carve] dropping imports that only the removed bodies used"
# Both wordings: a plain import reports `"p" imported and not used`, an aliased
# one reports `"p" imported as x and not used`.  tsdb/db.go has one of the
# latter (prom_runtime); a grep for only the first wording silently leaves it.
for round in $(seq 1 30); do
    errs=$(cd "$TREE" && go build ./tsdb/ 2>&1 | grep -E 'imported .*not used' || true)
    [ -z "$errs" ] && { echo "[carve] imports clean after $((round-1)) rounds"; break; }
    while IFS= read -r line; do
        file=${line%%:*}
        lineno=$(echo "$line" | cut -d: -f2)
        [ -f "$TREE/$file" ] && sed -i "${lineno}s|^|// carved: |" "$TREE/$file"
    done <<< "$errs"
done

echo "[carve] removing the judging tests and the fixtures they read"
( cd "$TREE" && rm -f $HIDDEN_TESTS )
# Nothing under tsdb/ embeds testdata and no non-test file reads it: the four
# readers are block_test.go, db_test.go, querier_test.go and repair_test.go,
# all of which go into the hidden set.  The directory can leave entirely.
rm -rf "$TREE/tsdb/testdata"
test ! -d "$TREE/tsdb/testdata"

echo "[carve] no VCS history in the tree (a checkout would undo the carve)"
rm -rf "$TREE/.git"
test ! -d "$TREE/.git"

echo "[carve] the tree must still compile, in both label builds"
( cd "$TREE" && go build ./... )
( cd "$TREE" && go build -tags dedupelabels ./tsdb/ )
echo "[carve] done"
