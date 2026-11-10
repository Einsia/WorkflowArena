"""Truth for OOO-GOV-02, read off the policy library before the state was built.

SO-2026-procurement 4.1 bands (value of the release):
    A  3,000 and under            one approver holding at least 3,000
    B  over 3,000 up to 20,000    one approver holding at least 20,000
    C  over 20,000                two distinct approvers each holding at least 150,000
4.2 aggregation: orders released to the same vendor inside one window are banded on
    their combined value -> V-XMA is 2,400 + 19,000 = 21,400, so PO-11 and PO-15 are both C.
4.4 vendor must be `active`      -> PO-13 (V-PHS suspended) is held
PRW-2026 window closes at step 8 -> PO-17 enters at step 9 and is carried forward
CB-2026-02 budget floor 30,000 held at every point -> the routine queue plus the four
    early exception orders land the budget exactly on the floor, so PO-15 waits for the
    step-6 virement.

The routine orders are real records, but their correct treatment follows from the same
authored rules (each is a distinct vendor under 3,000 in band A), so the truth is still
derived, never observed.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feed_cfg as F

_ROUTINE = F.routine()
_ROUTINE_IDS = [r["id"] for r in _ROUTINE]

DISPOSITION = {
    "PO-11": "released", "PO-12": "released", "PO-13": "held", "PO-14": "released",
    "PO-15": "released", "PO-16": "released", "PO-17": "held",
}
BAND = {  # released orders banded on the aggregated vendor value, held orders on their own
    "PO-11": "C", "PO-12": "B", "PO-13": "C", "PO-14": "B",
    "PO-15": "C", "PO-16": "B", "PO-17": "C",
}
TRAP_OF = {
    "PO-11": "split_to_evade_threshold",
    "PO-12": None,
    "PO-13": "inactive_counterparty",
    "PO-14": None,
    "PO-15": "split_to_evade_threshold+expired_authority+budget_floor",
    "PO-16": None,
    "PO-17": "cross_period",
}
for _r in _ROUTINE:
    DISPOSITION[_r["id"]] = "released"
    BAND[_r["id"]] = "A"          # distinct vendor, own value under 3,000
    TRAP_OF[_r["id"]] = None

ROUTINE_IDS = _ROUTINE_IDS
ROUTINE_TOTAL = F.routine_total()
EXC_EXECUTED = round(sum(F.EXC_VALUE[p] for p in F.EXC_EARLY + F.EXC_LATE), 2)
TOTAL_EXECUTED = round(ROUTINE_TOTAL + EXC_EXECUTED, 2)          # 56,800 + routine
FINAL_BALANCE = round(F.OPENING - TOTAL_EXECUTED + F.VIREMENT_AMT, 2)

STAFF_LIMITS = {s[0]: s[3] for s in F.STAFF}
CP_STATUS = {v[0]: v[2] for v in F.EXC_VENDORS}
CP_STATUS.update({r["vendor_id"]: "active" for r in _ROUTINE})
