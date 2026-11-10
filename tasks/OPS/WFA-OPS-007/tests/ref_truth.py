"""Authored truth for OOO-OPS-01. Rules precede the state.

The exception joiners (J-01..J-06) and their traps are unchanged from the first edition.
The routine joiners are derived from feed_cfg, so the truth grows with the queue without
anyone hand-writing it.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F

# ---------------------------------------------------------------- exceptions (unchanged)
EXPECT_EXC = dict(F.EXC_EXPECT)
HOLD_REASON = dict(F.EXC_HOLD)
TRAP_OF = dict(F.EXC_TRAP)
REUSE_RECORD = dict(F.EXC_REUSE)

# ---------------------------------------------------------------- routine placements
# Every routine joiner is an ordinary case: active, on payroll, corefin + intranet, laptop.
EXPECT_ROUTINE = {
    r["id"]: {"hr": "active", "payroll": True,
              "access": ["corefin", "intranet"], "asset": "laptop"}
    for r in F.routine()
}
EXPECT = dict(EXPECT_EXC); EXPECT.update(EXPECT_ROUTINE)

# joiner id -> the client body its HR record must name (real bodies for routine placements)
SITE = F.site_of()

# The returner is the only record that must be reused.
ROUTINE = F.routine()
ROUTINE_IDS = [r["id"] for r in ROUTINE]

STOCK_AFTER = F.stock_after()
LAPTOP_ISSUES = F.laptop_demand()
