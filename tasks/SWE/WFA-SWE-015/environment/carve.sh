#!/bin/bash
# Materialise the starting tree: remove the SQL optimizer, keep its contract.
#
# Run during image build against a pristine source tree ($1).  Four things
# happen, in this order:
#
#   1. the 23 optimizer modules are hollowed out — every declaration stays
#      (classes, signatures, annotations, docstrings, module- and class-level
#      constants), every executable body is replaced by a return of a zero value
#      derived from the return annotation
#   2. the tests that judge the optimizer are removed (the verifier brings them
#      back after the agent has finished)
#   3. all but three of the data-driven fixture files are removed; the three that
#      stay are a format sample, and the two TPC files go with the rest because
#      they pin fully optimized SQL for 121 large queries
#   4. the tree must still import every module, end to end
#
# Zero values rather than `raise NotImplementedError`: this tree calls into the
# optimizer while it is being imported (`_COERCES_TO = _build_coerces_to()` in
# annotate_types.py, `GEN_DISPATCH = _build_gen_dispatch()` in simplify.py), and
# `sqlglot/dialects/bigquery.py` then indexes into the result from its own class
# body.  A raising stub would abort `import sqlglot` and nothing in the tree
# would run at all — the carve would read as "did not run", not as "failed".
# stubgen.py keeps the bodies of the few functions that run during import, and
# prints which ones.
set -euo pipefail
TREE=${1:?usage: carve.sh <source-tree>}
HERE=$(cd "$(dirname "$0")" && pwd)
PY=${PY:-/opt/venv/bin/python}

# Every module in sqlglot/optimizer except __init__.py, which is the PEP 562
# lazy re-export shim: hollowing its __getattr__ would break
# `from sqlglot.optimizer import ...` in retained modules (lineage.py), and it
# holds none of the behaviour under test.
CARVE_FILES="sqlglot/optimizer/annotate_types.py sqlglot/optimizer/canonicalize.py
sqlglot/optimizer/canonicalize_internal_names.py sqlglot/optimizer/eliminate_ctes.py
sqlglot/optimizer/eliminate_joins.py sqlglot/optimizer/eliminate_subqueries.py
sqlglot/optimizer/helpers.py sqlglot/optimizer/isolate_table_selects.py
sqlglot/optimizer/journal.py sqlglot/optimizer/merge_subqueries.py
sqlglot/optimizer/normalize.py sqlglot/optimizer/normalize_identifiers.py
sqlglot/optimizer/optimize_joins.py sqlglot/optimizer/optimizer.py
sqlglot/optimizer/pushdown_predicates.py sqlglot/optimizer/pushdown_projections.py
sqlglot/optimizer/qualify.py sqlglot/optimizer/qualify_columns.py
sqlglot/optimizer/qualify_tables.py sqlglot/optimizer/resolver.py
sqlglot/optimizer/scope.py sqlglot/optimizer/simplify.py
sqlglot/optimizer/unnest_subqueries.py"

# test_optimizer.py is the optimizer's own acceptance suite.  test_executor.py
# joins it because its setUpClass loads the two TPC fixture files.
HIDDEN_TESTS="tests/test_optimizer.py tests/test_executor.py"

KEEP_FIXTURES="isolate_table_selects.sql normalize.sql quote_identifiers.sql"

echo "[carve] hollowing out the optimizer"
( cd "$TREE" && "$PY" -I "$HERE/stubgen.py" $CARVE_FILES )

echo "[carve] removing the judging tests"
( cd "$TREE" && rm -f $HIDDEN_TESTS )

echo "[carve] reducing the fixture suite to a format sample"
for f in "$TREE"/tests/fixtures/optimizer/*.sql; do
    keep=no
    for k in $KEEP_FIXTURES; do [ "$(basename "$f")" = "$k" ] && keep=yes; done
    [ "$keep" = no ] && rm -f "$f"
done
rm -f "$TREE/tests/fixtures/optimizer/tpc-h/tpc-h.sql" \
      "$TREE/tests/fixtures/optimizer/tpc-ds/tpc-ds.sql"
ls "$TREE/tests/fixtures/optimizer/"

echo "[carve] no VCS history in the tree (a checkout would undo the carve)"
rm -rf "$TREE/.git"
test ! -d "$TREE/.git"

echo "[carve] the tree must still import, module by module"
( cd "$TREE" && "$PY" - <<'PY'
import importlib, pkgutil, sys
import sqlglot
bad = []
for m in pkgutil.walk_packages(sqlglot.__path__, "sqlglot."):
    # sqlglot/__main__.py is an argparse CLI: importing it parses this process's
    # argv, fails on the missing positional and calls sys.exit(2).  That is true
    # of the pristine tree as well, so it says nothing about the carve.
    if m.name.endswith("__main__"):
        continue
    try:
        importlib.import_module(m.name)
    except Exception as e:
        bad.append((m.name, type(e).__name__, str(e)[:120]))
print("[carve] import check:", "clean" if not bad else bad)
# The retained parser and generator still have to work.
assert sqlglot.transpile("SELECT a FROM t WHERE 1 = 1")[0] == "SELECT a FROM t WHERE 1 = 1"
sys.exit(1 if bad else 0)
PY
)
echo "[carve] done"
