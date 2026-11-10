"""Truth for OOO-GOV-03, read off the policy library before the state was built.

ER-2026 3.1 bands (value of the reimbursement):
    A  1,200 and under          one approver holding at least 1,200
    B  over 1,200 up to 6,000   one approver holding at least 6,000
    C  over 6,000               two distinct approvers each holding at least 40,000
ER-2026 3.2 aggregation is by **cost centre** within one run:
    CC-4120 = 980 + 4,350 + 5,200 = 10,530 -> EX-21, EX-22 and EX-25 are all band C
    CC-4210 = 1,150                        -> EX-26 is band A
    CC-4330 = 7,400                        -> EX-24 is band C
ER-2026 3.3 only a claim-level authorisation reimburses a claim
ER-2026 3.5 a person who amended a claim may not approve it -> EX-24 not u_dir2
ER-2026 3.6 claimant must be `active`  -> EX-23 (leaver) is held
IMP-2026 run closes at step 7          -> EX-27 enters at step 9 and is carried forward
IMP-2026 float floor 10,000 at every point; the routine queue plus the four early exception
    claims leaves only a small cushion, so EX-24 waits for the step-5 top-up.

The routine claims are real amounts, but their correct treatment follows from the same
authored rules: each sits on its own cost centre and is under 1,200, so it is band A and
the line manager clears it. The truth is still derived, never observed.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import feed_cfg as F

_ROUTINE = F.routine()

DISPOSITION = {
    "EX-21": "reimbursed", "EX-22": "reimbursed", "EX-23": "held", "EX-24": "reimbursed",
    "EX-25": "reimbursed", "EX-26": "reimbursed", "EX-27": "held",
}
BAND = {  # reimbursed claims banded on the aggregated cost-centre value, held on their own
    "EX-21": "C", "EX-22": "C", "EX-23": "B", "EX-24": "C",
    "EX-25": "C", "EX-26": "A", "EX-27": "B",
}
TRAP_OF = {
    "EX-21": "split_to_evade_threshold",
    "EX-22": "split_to_evade_threshold",
    "EX-23": "inactive_counterparty",
    "EX-24": "separation_of_duties+out_of_scope_approval",
    "EX-25": "split_to_evade_threshold+float_floor",
    "EX-26": None,
    "EX-27": "cross_period",
}
for _r in _ROUTINE:
    DISPOSITION[_r["id"]] = "reimbursed"
    BAND[_r["id"]] = "A"          # own cost centre, own value under 1,200
    TRAP_OF[_r["id"]] = None

ROUTINE_IDS = [r["id"] for r in _ROUTINE]
ROUTINE_TOTAL = F.routine_total()
TOTAL_EXECUTED = round(ROUTINE_TOTAL + F.TOTAL_EXC, 2)
FINAL_BALANCE = round(F.OPENING - TOTAL_EXECUTED + F.TOPUP_AMT, 2)
RUN_CAP = F.RUN_CAP
STAFF_LIMITS = {s[0]: s[3] for s in F.STAFF}
CP_STATUS = {v[0]: v[2] for v in F.EXC_CLAIMANTS}
CP_STATUS.update({r["claimant_id"]: "active" for r in _ROUTINE})
