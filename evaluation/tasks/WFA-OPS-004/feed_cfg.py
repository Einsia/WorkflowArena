"""Shared, deterministic derivation of OOO-GOV-04's variation queue.

The routine variations are drawn from real UK published spend returns (OGL v3.0): real
contractor names, real values, real paying bodies. The seven exception variations, the
people, the delegated limits and every threshold are authored, so the truth stays known by
construction. build_state.py, ref_truth.py, golden.py, controls.py and check_fit.py all
import this module, so the state and the truth cannot drift apart.
"""
import os, sys

TASK_ID = "ooo-gov-04"
N_ROUTINE = 16

#       id        name               role                   limit    delegation_expires
STAFF = [
    ("u_qs",   "F. Oyelaran",     "quantity_surveyor",       0,      None),
    ("u_pm",   "S. Baptiste",     "project_manager",         5000,   None),
    ("u_cm",   "H. Lindgren",     "contracts_manager",       25000,  None),
    ("u_dir",  "R. Mwangi",       "director_of_estates",     150000, None),
    ("u_dir2", "T. Castellanos",  "finance_director",        150000, None),
    ("u_dir3", "O. Bergstrom",    "director_of_estates",     150000, None),
]

# ---- exception block: authored, each carries one procurement-control trap. UNCHANGED. ----
EXC_CONTRACTORS = [     # real names from published spend returns; standing is synthetic
    ("C-KIER", "KIER CONSTRUCTION LIMITED", "active", "BK-2210"),
    ("C-BALF", "BALFOUR BEATTY",            "active", "BK-8814"),
    ("C-WILL", "WILLMOTT DIXON",            "active", "BK-4455"),
    ("C-MORG", "MORGAN SINDALL",            "active", "BK-6673"),
    ("C-GALL", "GALLIFORD TRY",             "active", "BK-9902"),
    ("C-INTE", "INTERSERVE",                "active", "BK-1137"),
]
#       id       contractor   value       contract        raised_at  raised_by
EXCEPTIONS = [
    ("VO-31", "C-KIER",  18000.00, "CTR-2024-07", 1, None),
    ("VO-32", "C-KIER",  14000.00, "CTR-2024-07", 1, None),  # same contract: 32,000 combined
    ("VO-33", "C-BALF",  26000.00, "CTR-2025-02", 1, None),
    ("VO-34", "C-WILL",   9500.00, "CTR-2025-11", 1, None),
    ("VO-35", "C-MORG", 175000.00, "CTR-2024-19", 1, None),  # above the scheme: board reserved
    ("VO-36", "C-GALL",  95000.00, "CTR-2025-04", 1, None),  # provision cannot reach it
    ("VO-37", "C-INTE",   4200.00, "CTR-2026-01", 1, None),
]
EXC_VALUE = {e[0]: e[2] for e in EXCEPTIONS}
# Two director authorisations for VO-33 that lapsed with the previous certification period,
# and a provisional-sum authorisation against VO-31 that is short of its value.
LAPSED = [
    ("AP-OLD-33A", "VO-33", "u_dir",  26000.00, 0, "variation", 0),
    ("AP-OLD-33B", "VO-33", "u_dir2", 26000.00, 0, "variation", 0),
]
PROVISIONAL = ("AP-PROV-31", "VO-31", "u_cm", 15000.00, 0, "variation", None)

# Exception variations authorised before the quarterly release lands, and the two that must
# wait for it: both would take the provision under its floor.
EXC_EARLY = ["VO-31", "VO-33", "VO-37"]
EXC_LATE  = ["VO-32", "VO-34"]
EXC_HELD  = ["VO-35", "VO-36"]


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'amount': 3226.25,
  'contract': 'CTR-2026-R01',
  'contractor_id': 'C-R01',
  'contractor_name': 'CARING CONNECTIONS LIMITED',
  'id': 'VO-R01',
  'raised_at': 1,
  'source_body': 'Wirral Metropolitan Borough Council'},
 {'amount': 3279.44,
  'contract': 'CTR-2026-R02',
  'contractor_id': 'C-R02',
  'contractor_name': 'LouiesA Ltd',
  'id': 'VO-R02',
  'raised_at': 1,
  'source_body': 'Calderdale Metropolitan Borough Council'},
 {'amount': 1050.0,
  'contract': 'CTR-2026-R03',
  'contractor_id': 'C-R03',
  'contractor_name': 'ARIA COURT',
  'id': 'VO-R03',
  'raised_at': 1,
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 1918.44,
  'contract': 'CTR-2026-R04',
  'contractor_id': 'C-R04',
  'contractor_name': 'Manor House Nursing Home',
  'id': 'VO-R04',
  'raised_at': 1,
  'source_body': 'City of York Council'},
 {'amount': 2943.79,
  'contract': 'CTR-2026-R05',
  'contractor_id': 'C-R05',
  'contractor_name': 'RED2GREEN',
  'id': 'VO-R05',
  'raised_at': 1,
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 866.66,
  'contract': 'CTR-2026-R06',
  'contractor_id': 'C-R06',
  'contractor_name': 'Redacted personal data',
  'id': 'VO-R06',
  'raised_at': 1,
  'source_body': 'Plymouth City Council'},
 {'amount': 1980.0,
  'contract': 'CTR-2026-R07',
  'contractor_id': 'C-R07',
  'contractor_name': 'Peter Jones',
  'id': 'VO-R07',
  'raised_at': 1,
  'source_body': 'Plymouth City Council'},
 {'amount': 3542.99,
  'contract': 'CTR-2026-R08',
  'contractor_id': 'C-R08',
  'contractor_name': 'Family Foster Care Ltd',
  'id': 'VO-R08',
  'raised_at': 1,
  'source_body': 'Bristol City Council'},
 {'amount': 828.52,
  'contract': 'CTR-2026-R09',
  'contractor_id': 'C-R09',
  'contractor_name': 'Npower',
  'id': 'VO-R09',
  'raised_at': 1,
  'source_body': 'City of York Council'},
 {'amount': 4524.8,
  'contract': 'CTR-2026-R10',
  'contractor_id': 'C-R10',
  'contractor_name': 'Securi-Guard Limited',
  'id': 'VO-R10',
  'raised_at': 1,
  'source_body': 'Plymouth City Council'},
 {'amount': 1650.0,
  'contract': 'CTR-2026-R11',
  'contractor_id': 'C-R11',
  'contractor_name': 'ATHENA CARE HOMES (CHESTERTON) LIMITED T/A LANGDON HOUSE',
  'id': 'VO-R11',
  'raised_at': 1,
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 1254.98,
  'contract': 'CTR-2026-R12',
  'contractor_id': 'C-R12',
  'contractor_name': 'CLICK TRAVEL',
  'id': 'VO-R12',
  'raised_at': 1,
  'source_body': 'Wirral Metropolitan Borough Council'},
 {'amount': 2200.0,
  'contract': 'CTR-2026-R13',
  'contractor_id': 'C-R13',
  'contractor_name': 'AYNSLEY NURSING HOME',
  'id': 'VO-R13',
  'raised_at': 1,
  'source_body': 'Wirral Metropolitan Borough Council'},
 {'amount': 840.0,
  'contract': 'CTR-2026-R14',
  'contractor_id': 'C-R14',
  'contractor_name': 'Alex Fry Rental Properties Ltd',
  'id': 'VO-R14',
  'raised_at': 1,
  'source_body': 'Bristol City Council'},
 {'amount': 4101.3,
  'contract': 'CTR-2026-R15',
  'contractor_id': 'C-R15',
  'contractor_name': 'BY THE BRIDGE NORTH WEST LIMITED',
  'id': 'VO-R15',
  'raised_at': 1,
  'source_body': 'Wirral Metropolitan Borough Council'},
 {'amount': 1317.36,
  'contract': 'CTR-2026-R16',
  'contractor_id': 'C-R16',
  'contractor_name': 'York Travel Limited',
  'id': 'VO-R16',
  'raised_at': 1,
  'source_body': 'City of York Council'}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_total():
    return round(sum(r["amount"] for r in routine()), 2)


# ---- provision, sized so the provision floor still binds exactly as it did at W=7 ----
# CP-2026-09 provision floor 50,000 at every point. Opening is set so that the routine
# queue plus the three early exception variations leaves a small cushion above the floor,
# so VO-32 and VO-34 wait for the step-4 release, and pulling either forward still breaches.
FLOOR        = 50000.00
HEADROOM     = 500.00
EARLY_EXC    = round(sum(EXC_VALUE[p] for p in EXC_EARLY), 2)      # 48,200
LATE_EXC     = round(sum(EXC_VALUE[p] for p in EXC_LATE), 2)       # 23,500
OPENING      = round(FLOOR + routine_total() + EARLY_EXC + HEADROOM, 2)
RELEASE_AMT  = 40000.00
RELEASE_STEP = 4
RELEASE = ("PE-01", RELEASE_STEP, "acct_contingency", RELEASE_AMT,
           "Quarter 2 contingency release")
ACCOUNT = ("acct_contingency", "Works contingency provision", OPENING, FLOOR)

CONTRACT_WINDOW_CAP = 40000.00
BOARD_RESERVED_ABOVE = 150000.00
