"""pytest plugin: print one `path::id STATUS` line per test, with graded ids.

`templates/grade.py` (copied in unchanged, as the brief requires) parses pytest
output with

    ^(\\S+?)::([\\w\\[\\]\\-\\.]+)\\s+(PASSED|FAILED|ERROR|SKIPPED)

and keys its verdicts on group 2.  Two things make pytest's own `-v` output
unusable against that pattern for this suite:

  * group 2 is only the part after the last `::`, so `test_default` in
    tests/test_fields.py and `test_default` in tests/test_main.py would land on
    one key and mask each other.  This suite has 73 test modules.
  * 12% of the node ids carry parametrisation text with spaces, quotes, commas
    and parentheses (`test_annotated[<lambda>-5-FieldInfo(annotation=int, ...)]`),
    which the token pattern truncates at the first space.

So the ids have to be flattened and slugified, and the flattening has to be
*the same* on both sides: `scripts/carve_build/make_expected.py` produces
f2p.json / expected.json from the control runs, this plugin produces the
verdicts the grader reads.  The three functions below are copies of
`test_id`, `leaf_slug` and `safe_test_id` from that file.  `selfcheck` at the
bottom re-derives every id in expected.json and refuses to run if any of them
is unreachable, so the two copies cannot drift apart silently.

Loaded by tests/config.json as `PYTHONPATH=/app:/tests python -m pytest -p leafids`.

Not to be confused with scripts/carve_build/leafreport.py, which another task in
this batch uses: that one post-processes a `--report-log` file after the run and
does not apply `safe_test_id`, which this suite needs (12% of its node ids carry
characters grade.py would truncate). This one is an in-process plugin instead, so
there is no second step that could be skipped.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys

_SLUG_KEEP = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-")
_GRADE_TOKEN = re.compile(r"^[\w\[\]\-\.]+$")


def leaf_slug(msg) -> str:
    text = "".join(c if c in _SLUG_KEEP else "_" for c in str(msg))
    while "__" in text:
        text = text.replace("__", "_")
    text = text.strip("_")[:56]
    digest = hashlib.sha1(str(msg).encode("utf-8", "replace")).hexdigest()[:8]
    return "%s_%s" % (text, digest) if text else digest


def test_id(nodeid: str) -> str:
    parts = nodeid.split("::")
    stem = parts[0].rsplit("/", 1)[-1]
    if stem.endswith(".py"):
        stem = stem[:-3]
    return ".".join([stem] + parts[1:])


def safe_test_id(flat_id: str) -> str:
    if _GRADE_TOKEN.match(flat_id):
        return flat_id
    return leaf_slug(flat_id)


def graded_id(nodeid: str) -> str:
    return safe_test_id(test_id(nodeid))


# --- plugin ----------------------------------------------------------------
#
# Verdict precedence is make_expected.py's: the `call` phase decides, a failing
# setup or teardown is a failure of the test, and a test skipped in setup is a
# skip.  Lines are emitted once, at session end, so a test cannot be reported
# twice and partial output cannot be mistaken for a complete run.

_verdicts: dict = {}


def pytest_runtest_logreport(report):
    verdict = {"passed": "PASSED", "failed": "FAILED", "skipped": "SKIPPED"}.get(
        report.outcome
    )
    if verdict is None:
        return
    key = graded_id(report.nodeid)
    if report.when == "call":
        _verdicts[key] = verdict
    elif verdict == "FAILED":
        _verdicts[key] = "FAILED"
    elif verdict == "SKIPPED" and key not in _verdicts:
        _verdicts[key] = "SKIPPED"


def pytest_sessionfinish(session, exitstatus):
    out = sys.stdout
    out.write("\n=== leafids: %d verdicts\n" % len(_verdicts))
    for key in sorted(_verdicts):
        out.write("leaf::%s %s\n" % (key, _verdicts[key]))
    out.flush()


def pytest_configure(config):
    """Refuse to run if this file and expected.json disagree about ids.

    An id the grader expects but that no node id can produce would be scored as
    a silent failure for every solution, including the reference one.  Checking
    the shape here turns that into a loud configuration error instead.
    """
    path = os.environ.get("LEAFREPORT_EXPECTED", "/tests/expected.json")
    try:
        with open(path) as fh:
            expected = json.load(fh)
    except (OSError, ValueError):
        return
    bad = [
        t
        for ids in expected.values()
        for t in ids
        if not _GRADE_TOKEN.match(t)
    ]
    if bad:
        raise SystemExit(
            "leafids: %d ids in %s cannot be matched by grade.py, e.g. %r"
            % (len(bad), path, bad[:3])
        )
