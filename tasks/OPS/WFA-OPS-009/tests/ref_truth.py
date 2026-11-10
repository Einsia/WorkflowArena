"""Authored truth for OOO-OPS-03. Rules precede the state.

Derived from the three applicable policies in workspace/policies/:
  LRS-2026-leaver-recovery.md   timing of access removal, payroll closure, asset recovery
  DAI-2026-delegated-authority.md  a held delegation must pass to the line manager first
  CHS-2026-case-handover.md     an open case is reassigned, never closed, at handover

The exception leavers (L-01..L-06) and their traps are unchanged from the first edition.
The routine leavers are derived from feed_cfg, so the truth grows with the queue.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F

STEP_NOW = 1

# ---------------------------------------------------------------- exceptions (unchanged)
EXPECT_EXC = dict(F.EXC_EXPECT)
HOLD_REASON = dict(F.EXC_HOLD)
TRAP_OF = dict(F.EXC_TRAP)

ACCESS_OF = {p: sorted(s for (_, q, s, _, _) in F.EXC_ACCESS if q == p) for p in
             {a[1] for a in F.EXC_ACCESS}}
# every routine leaver holds the same pair of systems at the start
for _r in F.routine():
    ACCESS_OF[_r["id"]] = sorted({a[2] for a in F.routine_access() if a[1] == _r["id"]})

SERIAL_CLASS = {"LPT-7001":"laptop","LPT-7005":"laptop","FKT-3006":"field_kit"}
HANDOVER_TO = {"D-01":"M-Hollis","C-01":"M-Okonjo"}
BLOCKER_OF = {"L-05":("delegations","D-01"), "L-06":("open_cases","C-01")}

UNTOUCHED_DELEGATIONS = {"D-02":("lapsed",None), "D-03":("active",None)}
UNTOUCHED_CASES = {"C-02":("closed",None), "C-03":("open",None), "C-04":("open",None)}

# ---------------------------------------------------------------- routine leavers
# Every routine leaver is a completed resignation: full recovery, and the open case they
# carry is handed to their line manager before their access goes.
ROUTINE = F.routine()
ROUTINE_IDS = [r["id"] for r in ROUTINE]

EXPECT_ROUTINE = {}
for r in ROUTINE:
    EXPECT_ROUTINE[r["id"]] = {
        "access": "revoked", "payroll": "closed", "returns": [r["serial"]],
        "handover": ["C-R%02d" % (int(r["id"][-2:]))],
    }
EXPECT = dict(EXPECT_EXC); EXPECT.update(EXPECT_ROUTINE)

for r in ROUTINE:
    HANDOVER_TO["C-R%02d" % int(r["id"][-2:])] = r["manager"]
    BLOCKER_OF[r["id"]] = ("open_cases", "C-R%02d" % int(r["id"][-2:]))

# the routine case subjects, which the handover must carry across unchanged
ROUTINE_CASE_SUBJECT = {"C-R%02d" % int(r["id"][-2:]): r["subject"] for r in ROUTINE}
ROUTINE_CASE_OWNER   = {"C-R%02d" % int(r["id"][-2:]): r["id"] for r in ROUTINE}
ROUTINE_SERIAL_CLASS = {r["serial"]: "laptop" for r in ROUTINE}

for r in ROUTINE:
    HOLD_REASON.setdefault(r["id"], "")

# ---------------------------------------------------------------- the merge
# Only obtainable after every unit has been settled.
def merge():
    return {
        "access_revoked":   sum(1 for e in EXPECT.values() if e["access"] == "revoked"),
        "payroll_closed":   sum(1 for e in EXPECT.values() if e["payroll"] == "closed"),
        "assets_returned":  sum(len(e["returns"]) for e in EXPECT.values()),
        "handovers":        sum(len(e["handover"]) for e in EXPECT.values()),
    }

MERGE = merge()
