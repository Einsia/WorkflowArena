"""Authored truth for OOO-OPS-02. Rules precede the state.

Rules (as published in workspace/policies/):
  * every applicant is screened against the sanctions register before anything else is
    recorded; an exact match on the registered legal name stops the accreditation
  * financial standing is checked for every applicant; employers liability insurance is
    checked for every applicant that is a body corporate (a sole trader is exempt)
  * a master record may be set `active` only when due diligence is complete and the bank
    account has been verified; otherwise it is held at `pending`
  * bank details are recorded only when the account holder is the applicant itself
  * a spend ceiling is set only for an active supplier, at the cap of its value band
      under 25,000 -> 25,000 ; 25,000 to 100,000 inclusive -> 100,000 ; over 100,000 -> board
  * a lapsed master record is reactivated, never duplicated

The exception applicants (A-01..A-06) and their traps are unchanged from the first edition.
The routine applicants are derived from feed_cfg, so the truth grows with the queue.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F

NOW = 12

# ---------------------------------------------------------------- exceptions (unchanged)
EXPECT_EXC = dict(F.EXC_EXPECT)
REUSE_MASTER = dict(F.EXC_REUSE)
NOTE = dict(F.EXC_NOTE)
TRAP_OF = dict(F.EXC_TRAP)

# ---------------------------------------------------------------- routine applicants
# A clean company/sole trader: sanctions pass, financial standing pass, insurance pass for a
# body corporate only, own-name account, active master, ceiling at its band cap -- or no
# ceiling at all where the value is over 100,000 and the board must set it.
def _routine_expect(r):
    dd = {"sanctions": "pass", "financial_standing": "pass"}
    if r["legal_form"] != "sole_trader":
        dd["insurance"] = "pass"
    ceiling = r["ceiling"]
    approved = ceiling is not None
    return {"dd": dd,
            "master": "active" if approved else "pending",
            "bank": approved,
            "ceiling": ceiling,
            "disposition": "approved" if approved else "held"}

EXPECT_ROUTINE = {r["id"]: _routine_expect(r) for r in F.routine()}
EXPECT = dict(EXPECT_EXC); EXPECT.update(EXPECT_ROUTINE)

ROUTINE = F.routine()
ROUTINE_IDS = [r["id"] for r in ROUTINE]
BOARD_IDS = [r["id"] for r in ROUTINE if r["board"]]

def _hold_note(rid):
    if rid in BOARD_IDS:
        return "ceiling above the local band is set by the commercial board"
    return ""

ROUTINE_NOTE = {rid: _hold_note(rid) for rid in ROUTINE_IDS}

# ---------------------------------------------------------------- programme merge
def merge():
    """Counts and ceiling total the register's TOTAL row must carry."""
    c = {"approved": 0, "held": 0, "rejected": 0}
    total = 0.0
    for a, e in EXPECT.items():
        c[e["disposition"]] += 1
        if e["ceiling"]: total += e["ceiling"]
    return {"approved": c["approved"], "held": c["held"], "rejected": c["rejected"],
            "ceiling_total": round(total, 2)}

MERGE = merge()
