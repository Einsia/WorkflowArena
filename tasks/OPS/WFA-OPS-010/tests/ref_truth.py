"""Authored truth for OOO-OPS-05. Rules precede the state.

Rules live in workspace/policies/ (CHS-2026 is the operative one):
  * a complaint from a complainant with no account in the customer master is not a
    service complaint: it is logged nowhere and nothing is provisioned for it;
  * a complaint received more than 12 steps before the current step is out of time;
  * a complaint that restates an already-OPEN case for the same account and subject is
    attached to that case; a closed case does not absorb a new complaint;
  * queue/window: tier 1 -> priority/5, tier 2 -> standard/10, tier 3 -> extended/15;
    an account carrying a vulnerability marker is handled in the priority queue;
  * an account in a regulated sector carrying a vulnerability marker must be referred to
    that sector's redress scheme;
  * goodwill is payable only for a service_failure on a `managed` contract, at the tier
    rate (1 -> 400, 2 -> 250, 3 -> 150), and only within the 300 delegated limit.

The exception complaints (C-01..C-06) and their traps are unchanged from the first edition.
The routine complaints are derived from feed_cfg, so the truth grows with the queue.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F

NOW = F.NOW
IN_TIME_WINDOW = F.IN_TIME_WINDOW
DELEGATED_LIMIT = F.DELEGATED_LIMIT
QUEUE_OF = dict(F.QUEUE_OF)
SCHEME_OF = dict(F.SCHEME_OF)

# ---------------------------------------------------------------- exceptions (unchanged)
EXPECT_EXC = {k: dict(v) for k, v in F.EXC_EXPECT.items()}
TRAP_OF = dict(F.EXC_TRAP)

EXC_INITIAL_CASES = {c[0] for c in F.EXC_CASES}
EXC_INITIAL_CLOCKS = {c[0] for c in F.EXC_CLOCKS}

# ---------------------------------------------------------------- routine complaints
ROUTINE = F.routine()
ROUTINE_IDS = [r["id"] for r in ROUTINE]

def _routine_expect(r):
    """Apply the published rules to one routine complaint."""
    late = (NOW - r["received_step"]) > IN_TIME_WINDOW
    if late:
        return {"account": r["account"], "disp": "out_of_time", "case": None,
                "new_case": False, "subject": None, "queue": "", "due": "",
                "scheme": None, "comp": 0}
    if r["attach_to"]:
        # attaching does not start a new clock: the case's existing clock governs, and it
        # was started before this episode opened
        case = r["attach_to"]
        clock = next(c for c in F.routine_open_clocks() if c[1] == case)
        return {"account": r["account"], "disp": "attached", "case": case,
                "new_case": False, "subject": r["subject"], "queue": clock[2],
                "due": str(clock[3]), "scheme": r["scheme"], "comp": r["goodwill"]}
    return {"account": r["account"], "disp": "opened", "case": None,
            "new_case": True, "subject": r["subject"], "queue": r["queue"],
            "due": str(r["due"]), "scheme": r["scheme"], "comp": r["goodwill"]}

EXPECT_ROUTINE = {r["id"]: _routine_expect(r) for r in ROUTINE}
EXPECT = dict(EXPECT_EXC); EXPECT.update(EXPECT_ROUTINE)

# cases and clocks that exist when the episode opens
INITIAL_CASES = EXC_INITIAL_CASES | {r["attach_to"] for r in ROUTINE if r["attach_to"]}
INITIAL_CLOCKS = EXC_INITIAL_CLOCKS | {"SLA-R%02d" % i
                                       for i, r in enumerate(ROUTINE, 1) if r["attach_to"]}

# the case an attached routine complaint must land on, and the clock already running on it
ATTACH_OF = {r["id"]: r["attach_to"] for r in ROUTINE if r["attach_to"]}
EXISTING_CLOCK_OF = {r["attach_to"]: "SLA-R%02d" % i
                     for i, r in enumerate(ROUTINE, 1) if r["attach_to"]}

# ---------------------------------------------------------------- the merge
def merge():
    e = list(EXPECT.values())
    return {
        "actioned":  sum(1 for x in e if x["disp"] in ("opened", "attached")),
        "cases":     sum(1 for x in e if x["new_case"]),
        "referrals": sum(1 for x in e if x["scheme"]),
        "comp":      sum(x["comp"] for x in e),
    }

_M = merge()
NEW_CASES  = _M["cases"]
ACTIONED   = _M["actioned"]
REFERRALS  = _M["referrals"]
COMP_TOTAL = _M["comp"]
