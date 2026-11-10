"""Authored truth for OOO-OPS-06. Rules precede the state.

Rules live in workspace/policies/ (CRP-2026 is the operative one):
  * the renewal period is 2028; the renewal value is the current value indexed by the
    factor for the contract's series **in that period**;
  * a renewal value above the 500,000 re-tender threshold may not be renewed at all -- it
    goes back to the market, and the threshold is tested on the indexed value;
  * a renewal is executed only where the legal review **for the renewal period** reads
    `cleared` or `cleared_with_conditions`; `unresolved` holds the renewal;
  * a contract already renewed through the renewal period is not renewed again;
  * a contract on which the counterparty has served notice lapses;
  * the billing schedule is signed by the active signatory of lowest authority whose limit
    covers the annual value; schedules start at step 60.

The exception contracts (K-01..K-06) and their traps are unchanged from the first edition.
The routine contracts are derived from feed_cfg, so the truth grows with the queue.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F

NOW = F.NOW
PERIOD = F.PERIOD
RETENDER_THRESHOLD = F.RETENDER_THRESHOLD
START_STEP = F.START_STEP
EXECUTABLE = F.EXECUTABLE

# ---------------------------------------------------------------- exceptions (unchanged)
EXPECT_EXC = {k: dict(v) for k, v in F.EXC_EXPECT.items()}
TRAP_OF = dict(F.EXC_TRAP)
INITIAL_OPPS = set(F.EXC_INITIAL_OPPS)
INITIAL_SCHEDULES = set(F.EXC_INITIAL_SCHEDULES)

# ---------------------------------------------------------------- routine contracts
# Every routine contract is an ordinary renewal: cleared review for the renewal period, no
# notice, not already renewed, indexed value under the threshold.
ROUTINE = F.routine()
ROUTINE_IDS = [r["id"] for r in ROUTINE]

EXPECT_ROUTINE = {
    r["id"]: {"disp": "renewed", "value": r["value"], "stage": "closed_won",
              "schedule": True, "signatory": r["signatory"]}
    for r in ROUTINE
}
EXPECT = dict(EXPECT_EXC); EXPECT.update(EXPECT_ROUTINE)

COUNTERPARTY = {r["id"]: r["counterparty"] for r in ROUTINE}

# ---------------------------------------------------------------- the merge
def merge():
    renewed = [e for e in EXPECT.values() if e["disp"] == "renewed"]
    return {
        "renewed":     len(renewed),
        "renewed_value": round(sum(e["value"] for e in renewed), 2),
        "not_renewed": len(EXPECT) - len(renewed),
    }

_M = merge()
RENEWED = _M["renewed"]
RENEWED_VALUE = _M["renewed_value"]
NOT_RENEWED = _M["not_renewed"]
