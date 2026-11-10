#!/usr/bin/env python3
"""Turn a pytest `--report-log` file into the text report templates/grade.py reads.

grade.py is copied verbatim into every task in this batch, and its pytest parser
matches one line per test:

    ^(\\S+?)::([\\w\\[\\]\\-\\.]+)\\s+(PASSED|FAILED|ERROR|SKIPPED)

keying the verdict on the second group alone.  Two things follow for a task
whose judging surface is `unittest` subtests over data-driven fixtures:

  * `pytest -v` output is not usable directly — the bare function name is the
    key, and `test_ddl` exists in a dozen dialect test files, so verdicts would
    overwrite each other
  * passing subtests never appear in `-v` output at all, so a 599-case fixture
    file would be worth a single scoring unit

So the verifier runs pytest with `--report-log` and this script rewrites the log
into one line per leaf (one subtest, or one test function that has none), using
exactly the ids that `make_expected.py` recorded from the control runs.

    python3 -I leafreport.py <report-log> [more-report-logs...]
"""

import hashlib
import json
import sys
from collections import Counter

# Generated from scripts/carve_build/pytest_block.py -- keep in sync.
# --- pytest-reportlog output (additive: the paths above are untouched) -------
#
# `pytest --report-log=F` writes one JSON object per line, like `go test -json`,
# so the file still starts with "{" and has to be told apart by content.  With
# pytest-subtests installed, every `unittest.TestCase.subTest` block emits its
# own record ("_report_type": "SubTestReport") carrying the subTest message in
# "_subtest.context".  That is the leaf granularity this carve-out needs: one
# fixture case is one scoring unit, so a single wrong rewrite costs one unit
# instead of a whole 599-case test function.
#
# A leaf id has to survive two constraints:
#   * templates/grade.py matches test names against `[\w\[\]\-\.]+`, so a
#     subTest message (arbitrary SQL) cannot be used verbatim
#   * check_file submits its cases to a ProcessPoolExecutor and consumes them
#     with as_completed, so ids must not depend on execution order
# Hence: slugify the message and append a short digest of the full message.
# Same code is used by the control runs and by the verifier's leaf reporter, so
# the ids match on both sides.

_PYTEST_SUB = "_subtest.context"
_SLUG_KEEP = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")


def leaf_slug(msg: str) -> str:
    """A grade.py-safe, order-independent token for one subTest message."""
    text = "".join(c if c in _SLUG_KEEP else "_" for c in str(msg))
    while "__" in text:
        text = text.replace("__", "_")
    text = text.strip("_")[:56]
    digest = hashlib.sha1(str(msg).encode("utf-8", "replace")).hexdigest()[:8]
    return "%s_%s" % (text, digest) if text else digest


def test_id(nodeid: str) -> str:
    """Flat, collision-free id for a test function.

    templates/grade.py keys its verdicts on a single `[\\w\\[\\]\\-\\.]+` token,
    so the id cannot contain `/` or `::` and cannot be the bare function name
    either: `test_ddl` exists in a dozen dialect test files.  Module stem and
    class are folded in with dots, which the token pattern allows.

        tests/dialects/test_snowflake.py::TestSnowflake::test_ddl
            -> test_snowflake.TestSnowflake.test_ddl
    """
    parts = nodeid.split("::")
    stem = parts[0].rsplit("/", 1)[-1]
    if stem.endswith(".py"):
        stem = stem[:-3]
    return ".".join([stem] + parts[1:])


def leaf_id(nodeid: str, msg, repeat: int = 1) -> str:
    """Id for one subtest: the test id plus a bracketed slug of its message."""
    suffix = "" if repeat <= 1 else ".r%d" % repeat
    return "%s[%s%s]" % (test_id(nodeid), leaf_slug(msg), suffix)


def looks_like_pytest(path: str) -> bool:
    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                return False
            return "$report_type" in ev or "_report_type" in ev
    return False


def pytest_verdicts(path):
    """Return (leaves, parents, collect_errors) for a pytest report-log file.

    leaves          {leaf id: "pass"|"fail"|"skip"}, subtests resolved
    parents         node ids that only exist because they have subtests
    collect_errors  node ids pytest could not even collect
    """
    leaves = {}
    parents = set()
    collect_errors = []
    repeats = Counter()

    with open(path, errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            kind = ev.get("$report_type") or ev.get("_report_type")
            nodeid = ev.get("nodeid")
            outcome = {"passed": "pass", "failed": "fail", "skipped": "skip"}.get(
                ev.get("outcome"))
            if not nodeid or outcome is None:
                continue

            if kind == "CollectReport":
                if outcome == "fail":
                    collect_errors.append(nodeid)
                continue

            if kind == "SubTestReport":
                context = ev.get(_PYTEST_SUB) or {}
                msg = context.get("msg")
                if msg is None:
                    msg = context.get("kwargs") or ""
                # One subTest message can be reused inside a single test
                # function (test_annotate_funcs loops over dialects with one
                # title); number the repeats.  That loop is sequential, so the
                # numbering is stable across runs.
                key = (nodeid, str(msg))
                repeats[key] += 1
                leaves[leaf_id(nodeid, msg, repeats[key])] = outcome
                parents.add(test_id(nodeid))
                continue

            if kind == "TestReport":
                ident = test_id(nodeid)
                when = ev.get("when")
                if when == "call":
                    leaves[ident] = outcome
                elif outcome == "fail":
                    # a setup/teardown error is a failure of the test
                    leaves[ident] = "fail"
                elif outcome == "skip" and ident not in leaves:
                    leaves[ident] = "skip"

    for parent in parents:
        leaves.pop(parent, None)
    return leaves, parents, collect_errors


def main(argv):
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    text = {"pass": "PASSED", "fail": "FAILED", "skip": "SKIPPED"}
    total = Counter()
    for path in argv:
        leaves, _parents, collect_errors = pytest_verdicts(path)
        for nodeid in collect_errors:
            print("%s::%s ERROR" % (nodeid.split("::")[0], test_id(nodeid)))
        for ident in sorted(leaves):
            total[leaves[ident]] += 1
            print("leaf::%s %s" % (ident, text[leaves[ident]]))
    print("# leaves: pass=%d fail=%d skip=%d"
          % (total["pass"], total["fail"], total["skip"]), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
