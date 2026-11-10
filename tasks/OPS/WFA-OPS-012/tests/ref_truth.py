"""Authored truth for OOO-OPS-07. Rules precede the state.

Rules that generate this truth (all discoverable in workspace/policies/):
  * DSAR-procedure-2026 s.3  identity is verified before any search of the record estate
  * identity-verification-standard-2026 s.2  one photographic document AND one document
    evidencing current address; anything less does not verify
  * DSAR-procedure-2026 s.2  an erasure request is not an access request: it is closed as
    `not_an_access_request` and referred; no disclosure pack is assembled
  * DSAR-procedure-2026 s.5  a further request from the same subject received fewer than
    eight steps after the previous response is manifestly unfounded and is refused
  * exemptions-register-handbook s.1  an exemption withholds a record only while `active`
  * exemptions-register-handbook s.4  a record marked `third_party` is released only after
    a redaction has been recorded, and the pack must cite that redaction

The exception requests (R-01..R-06) and their traps are unchanged from the first edition.
The routine requests are derived from feed_cfg, so the truth grows with the queue.
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F

NOW = F.NOW
REPEAT_WINDOW = F.REPEAT_WINDOW
PHOTO_DOCS   = set(F.PHOTO_DOCS)
ADDRESS_DOCS = set(F.ADDRESS_DOCS)

# ---------------------------------------------------------------- exceptions (unchanged)
EXPECT_EXC = {k: dict(v) for k, v in F.EXC_EXPECT.items()}
TRAP_OF = dict(F.EXC_TRAP)
EXC_NEEDS_REDACTION = {"REC-0402"}
EXC_ACTIVE_EXEMPT   = {"REC-0303"}
EXC_LAPSED_EXEMPT   = {"REC-0302"}

# ---------------------------------------------------------------- routine requests
ROUTINE = F.routine()
ROUTINE_IDS = [r["id"] for r in ROUTINE]
ROUTINE_RECORDS = F.routine_records()
ROUTINE_EXEMPTIONS = F.routine_exemptions()

def _identity_ok(evidence):
    parts = set((evidence or "").split("+"))
    return bool(parts & PHOTO_DOCS) and bool(parts & ADDRESS_DOCS)

def _estate(subject):
    return [x for x in ROUTINE_RECORDS if x["subject"] == subject]

def _exempt_of(subject):
    mine = {x["id"] for x in _estate(subject)}
    return [e for e in ROUTINE_EXEMPTIONS if e[1] in mine]

def _routine_expect(r):
    """Apply the published rules to one routine request."""
    estate = _estate(r["subject"])
    active = {e[1] for e in _exempt_of(r["subject"]) if e[3] == "active"}
    unfounded = (r["prior_response_step"] is not None
                 and r["received_step"] - r["prior_response_step"] < REPEAT_WINDOW)
    if not _identity_ok(r["id_evidence"]):
        return {"identity": "failed", "disposition": "identity_not_verified",
                "release": [], "considered": len(estate)}
    if r["request_type"] != "access":
        return {"identity": "passed", "disposition": "not_an_access_request",
                "release": [], "considered": len(estate)}
    if unfounded:
        return {"identity": "passed", "disposition": "refused_unfounded",
                "release": [], "considered": len(estate)}
    release = sorted(x["id"] for x in estate if x["id"] not in active)
    withheld = len(estate) - len(release)
    return {"identity": "passed",
            "disposition": "fulfilled_in_part" if withheld else "fulfilled",
            "release": release, "considered": len(estate)}

EXPECT_ROUTINE = {r["id"]: _routine_expect(r) for r in ROUTINE}
EXPECT = dict(EXPECT_EXC); EXPECT.update(EXPECT_ROUTINE)

NEEDS_REDACTION = set(EXC_NEEDS_REDACTION) | {x["id"] for x in ROUTINE_RECORDS
                                              if x["sensitivity"] == "third_party"}
ACTIVE_EXEMPT   = set(EXC_ACTIVE_EXEMPT) | {e[1] for e in ROUTINE_EXEMPTIONS if e[3] == "active"}
LAPSED_EXEMPT   = set(EXC_LAPSED_EXEMPT) | {e[1] for e in ROUTINE_EXEMPTIONS if e[3] == "lapsed"}

RELEASABLE = {r for e in EXPECT.values() for r in e["release"]}
TOTALS = {"considered": sum(e["considered"] for e in EXPECT.values()),
          "released":   sum(len(e["release"]) for e in EXPECT.values()),
          "withheld":   sum(e["considered"] - len(e["release"]) for e in EXPECT.values())}

# the real organisations whose personnel appear in a third-party record, so a redaction has
# something concrete to be about
COUNTERPARTY_OF_RECORD = F.all_counterparties()
