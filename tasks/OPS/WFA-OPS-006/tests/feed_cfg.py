"""Shared, deterministic derivation of OOO-GOV-07's disposal queue.

The routine disposals are drawn from real UK published spend returns (OGL v3.0): real buyer
names, real values, real paying bodies. The seven exception disposals, the people, the
delegated limits and every threshold are authored, so the truth stays known by
construction. build_state.py, ref_truth.py, golden.py, controls.py and check_fit.py all
import this module, so the state and the truth cannot drift apart.
"""
import os, sys

TASK_ID = "ooo-gov-07"
N_ROUTINE = 15

#       id        name               role                   limit    delegation_expires
STAFF = [
    ("u_est",  "W. Mutambo",      "estates_officer",         0,      None),
    ("u_val",  "I. Castellani",   "valuation_officer",       10000,  None),
    ("u_am",   "Q. Fitzgerald",   "asset_manager",           40000,  None),
    ("u_dir",  "Z. Oyelowo",      "director_of_estates",     250000, None),
    ("u_dir2", "B. Lindholm",     "finance_director",        250000, None),
    ("u_dir3", "Y. Haddad",       "director_of_estates",     250000, None),
]

# ---- exception block: authored, each carries one disposal-control trap. UNCHANGED. ----
EXC_BUYERS = [      # real names from published spend returns; standing is synthetic
    ("B-YORW",  "Yorwaste Ltd",                    "active", "BK-7120"),
    ("B-TARMAC", "Tarmac Ltd",                     "active", "BK-3348"),
    ("B-RINGD", "Ringdane Ltd",                    "active", "BK-9915"),
    ("B-ADECCO", "Adecco UK Ltd",                  "active", "BK-2204"),
    ("B-PERT",  "Pertemps Limited",                "barred", "BK-6671"),  # connected party
    ("B-SLAKE", "South Lakeland District Council", "active", "BK-5583"),
]
#       id       buyer        carrying     lot      retention_until  revalued_by
EXCEPTIONS = [
    ("AD-61", "B-YORW",   38000.00, "LOT-A", 1,  None),
    ("AD-62", "B-YORW",   52000.00, "LOT-A", 1,  None),   # same buyer: 90,000 combined
    ("AD-63", "B-TARMAC",  9000.00, "LOT-B", 1,  "u_val"),  # revalued by the valuer
    ("AD-64", "B-RINGD",  14000.00, "LOT-C", 1,  None),
    ("AD-65", "B-ADECCO", 22000.00, "LOT-D", 1,  None),
    ("AD-66", "B-PERT",   46000.00, "LOT-E", 1,  None),   # buyer barred
    ("AD-67", "B-SLAKE",  31000.00, "LOT-F", 12, None),   # still inside minimum retention
]
EXC_VALUE = {e[0]: e[2] for e in EXCEPTIONS}
# A direct-sale authorisation already on file against the barred buyer's lot.
PRIOR = ("AP-DIRECT-66", "AD-66", "u_dir", 46000.00, 0, "disposal", None)

# Exception disposals effected before the certified revaluation lands, and the one that must
# wait for it.
EXC_EARLY = ["AD-61", "AD-62", "AD-63", "AD-64"]
EXC_LATE  = ["AD-65"]
EXC_HELD  = ["AD-66", "AD-67"]


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'amount': 742.07,
  'buyer_id': 'B-R01',
  'buyer_name': 'Lifeways Community Care',
  'id': 'AD-R01',
  'lot': 'LOT-R01',
  'retention_until': 1,
  'source_body': 'Plymouth City Council'},
 {'amount': 1705.56,
  'buyer_id': 'B-R02',
  'buyer_name': 'Ringdane Ltd',
  'id': 'AD-R02',
  'lot': 'LOT-R02',
  'retention_until': 1,
  'source_body': 'City of York Council'},
 {'amount': 946.77,
  'buyer_id': 'B-R03',
  'buyer_name': 'ARIA COURT',
  'id': 'AD-R03',
  'lot': 'LOT-R03',
  'retention_until': 1,
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 7070.0,
  'buyer_id': 'B-R04',
  'buyer_name': 'KTD Agricultural Services',
  'id': 'AD-R04',
  'lot': 'LOT-R04',
  'retention_until': 1,
  'source_body': 'Calderdale Metropolitan Borough Council'},
 {'amount': 803.64,
  'buyer_id': 'B-R05',
  'buyer_name': 'BOXTREE COTTAGE CAMBRIDGE LIMITED T/A BOXTREE COTTAGE RESIDENTIAL HOME',
  'id': 'AD-R05',
  'lot': 'LOT-R05',
  'retention_until': 1,
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 649.74,
  'buyer_id': 'B-R06',
  'buyer_name': 'Redacted personal data',
  'id': 'AD-R06',
  'lot': 'LOT-R06',
  'retention_until': 1,
  'source_body': 'Plymouth City Council'},
 {'amount': 1169.7,
  'buyer_id': 'B-R07',
  'buyer_name': 'Housing 21',
  'id': 'AD-R07',
  'lot': 'LOT-R07',
  'retention_until': 1,
  'source_body': 'Bristol City Council'},
 {'amount': 1035.0,
  'buyer_id': 'B-R08',
  'buyer_name': 'Independence South West',
  'id': 'AD-R08',
  'lot': 'LOT-R08',
  'retention_until': 1,
  'source_body': 'Plymouth City Council'},
 {'amount': 1196.09,
  'buyer_id': 'B-R09',
  'buyer_name': 'Adt Fire And Security',
  'id': 'AD-R09',
  'lot': 'LOT-R09',
  'retention_until': 1,
  'source_body': 'City of York Council'},
 {'amount': 3911.14,
  'buyer_id': 'B-R10',
  'buyer_name': 'United Response',
  'id': 'AD-R10',
  'lot': 'LOT-R10',
  'retention_until': 1,
  'source_body': 'City of York Council'},
 {'amount': 1196.77,
  'buyer_id': 'B-R11',
  'buyer_name': 'ASKHAM SERVICES LIMITED',
  'id': 'AD-R11',
  'lot': 'LOT-R11',
  'retention_until': 1,
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 4630.0,
  'buyer_id': 'B-R12',
  'buyer_name': 'AINSLEY GOMMON ARCHITECTS',
  'id': 'AD-R12',
  'lot': 'LOT-R12',
  'retention_until': 1,
  'source_body': 'Wirral Metropolitan Borough Council'},
 {'amount': 1289.28,
  'buyer_id': 'B-R13',
  'buyer_name': 'Carlisle Staffing PLC T/A Guidant Global',
  'id': 'AD-R13',
  'lot': 'LOT-R13',
  'retention_until': 1,
  'source_body': 'Bristol City Council'},
 {'amount': 2000.0,
  'buyer_id': 'B-R14',
  'buyer_name': 'Dolphin Stairlifts South-West',
  'id': 'AD-R14',
  'lot': 'LOT-R14',
  'retention_until': 1,
  'source_body': 'Plymouth City Council'},
 {'amount': 2200.0,
  'buyer_id': 'B-R15',
  'buyer_name': 'Firmstep',
  'id': 'AD-R15',
  'lot': 'LOT-R15',
  'retention_until': 1,
  'source_body': 'Plymouth City Council'}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_total():
    return round(sum(r["amount"] for r in routine()), 2)


# ---- asset base, sized so the asset-base floor still binds exactly as it did at W=7 ----
# EC-2026-03 asset base floor 300,000 at every point. Opening is set so that the routine
# queue plus the four early exception disposals leaves a small cushion above the floor, so
# AD-65 waits for the step-5 certified revaluation, and pulling it forward still breaches.
FLOOR        = 300000.00
HEADROOM     = 500.00
EARLY_EXC    = round(sum(EXC_VALUE[p] for p in EXC_EARLY), 2)      # 113,000
LATE_EXC     = round(sum(EXC_VALUE[p] for p in EXC_LATE), 2)       # 22,000
OPENING      = round(FLOOR + routine_total() + EARLY_EXC + HEADROOM, 2)
REVAL_AMT    = 80000.00
REVAL_STEP   = 5
REVAL = ("PE-01", REVAL_STEP, "acct_assetbase", REVAL_AMT,
         "Certified revaluation uplift, retained estate")
ACCOUNT = ("acct_assetbase", "Net book value of the disposable estate", OPENING, FLOOR)
AUCTION_REQUIRED_BAND = "C"
WINDOW_END = 10
