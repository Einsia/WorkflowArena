"""Cap the CPU count Python reports, for everything that runs in this venv.

`tests/test_optimizer.py` fans every fixture file out over a
`ProcessPoolExecutor()` with no `max_workers`, and CPython 3.12 sizes that pool
from `os.cpu_count()` — the machine's core count, which is neither the slurm
allocation nor the container's CPU quota.  On a 256-core node that is 256 forked
interpreters each importing sqlglot, pandas and duckdb, which is ~33 GB and an
instant OOM kill.  CPython 3.13 fixed this by sizing the pool from
`os.process_cpu_count()`; this file backports the effect to 3.12 so the control
runs and the verifier agree.

Pool size does not change any verdict: the leaf ids are content-addressed, not
positional.

`WFA_CPU_COUNT` sets the cap explicitly; otherwise the scheduler-visible
affinity is used, capped at 8.
"""

import os

_cap = os.environ.get("WFA_CPU_COUNT")
if _cap:
    _n = max(1, int(_cap))
else:
    try:
        _n = len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        _n = os.cpu_count() or 1
    _n = max(1, min(_n, 8))

os.cpu_count = lambda: _n
if hasattr(os, "process_cpu_count"):
    os.process_cpu_count = lambda: _n
