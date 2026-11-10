"""Shared, deterministic derivation of OOO-GOV-05's instalment queue.

The routine instalments are drawn from real UK published spend returns (OGL v3.0): real
grantee names, real values, real paying bodies. The seven exception instalments, the
people, the delegated limits and every threshold are authored, so the truth stays known by
construction. build_state.py, ref_truth.py, golden.py, controls.py and check_fit.py all
import this module, so the state and the truth cannot drift apart.
"""
import os, sys

TASK_ID = "ooo-gov-05"
N_ROUTINE = 15

#       id        name             role                    limit    delegation_expires
STAFF = [
    ("u_gm",   "A. Sowande",    "grants_officer",           0,      None),
    ("u_prog", "L. Petrov",     "programme_manager",        10000,  None),
    ("u_head", "D. Nakamura",   "head_of_grants",           30000,  None),
    ("u_dir",  "M. Eriksen",    "director_of_funding",      200000, None),
    ("u_dir2", "J. Okolie",     "finance_director",         200000, None),
    ("u_dir3", "V. Halabi",     "director_of_funding",      200000, None),
]

# ---- exception block: authored, each carries one funding-control trap. UNCHANGED. ----
EXC_GRANTEES = [    # real names from published spend returns; standing is synthetic
    ("G-KENDAL", "KENDAL COLLEGE",              "active",             "BK-3326"),
    ("G-HINCK",  "HINCKLEY & BOSWORTH COUNCIL", "active",             "BK-7781"),
    ("G-LEIC",   "LEICESTER COLLEGE",           "active",             "BK-5512"),
    ("G-NORTH",  "NORTHUMBRIA UNIVERSITY",      "active",             "BK-6108"),
    ("G-BARN",   "BARNSLEY COLLEGE",            "under_investigation","BK-2274"),
    ("G-SOUTH",  "SOUTH ESSEX COLLEGE",         "active",             "BK-4490"),
]
#       id       grantee      value      programme        due_at  amended_by
EXCEPTIONS = [
    ("GI-41", "G-KENDAL", 45000.00, "PRG-RESTRICT", 1,  None),
    ("GI-42", "G-HINCK",  28000.00, "PRG-RESTRICT", 1,  None),
    ("GI-43", "G-BARN",   32000.00, "PRG-RESTRICT", 1,  None),  # grantee under investigation
    ("GI-44", "G-LEIC",   22000.00, "PRG-CORE",     1,  None),
    ("GI-45", "G-NORTH",  60000.00, "PRG-RESTRICT", 1,  None),
    ("GI-46", "G-LEIC",    9000.00, "PRG-CORE",     1,  None),  # + GI-44 = 31,000 for G-LEIC
    ("GI-47", "G-KENDAL", 18000.00, "PRG-RESTRICT", 11, None),  # falls due in the next year
]
EXC_VALUE = {e[0]: e[2] for e in EXCEPTIONS}
# Two programme-level authorisations for the restricted stream. They cover the value and
# both approvers hold a director's limit, but they are block records against the programme.
BLOCK = [
    ("AP-BLOCK-A", "GI-45", "u_dir",  200000.00, 0, "programme", None),
    ("AP-BLOCK-B", "GI-45", "u_dir2", 200000.00, 0, "programme", None),
]
# Exception instalments met from the restricted fund before the tranche lands, and the one
# that must wait for it.
EXC_EARLY = ["GI-41", "GI-42"]
EXC_LATE  = ["GI-45"]
EXC_HELD  = ["GI-43", "GI-47"]
CORE_IDS  = ["GI-44", "GI-46"]          # met from acct_core, outside the restricted stream

# Which fund each programme must be met from (GC-2026 6.4)
FUND_OF = {"PRG-RESTRICT": "acct_rgf", "PRG-CORE": "acct_core"}


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'amount': 4050.0,
  'due_at': 1,
  'grantee_id': 'G-R01',
  'grantee_name': '1-2 ACHIEVE',
  'id': 'GI-R01',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 3556.95,
  'due_at': 1,
  'grantee_id': 'G-R02',
  'grantee_name': 'WEST MERCIA ENERGY - ELECTRICITY - PRINCE OF WALES STADIUM    -   '
                  '01/11/2019-30/11/2019',
  'id': 'GI-R02',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Cheltenham Borough Council'},
 {'amount': 1356.46,
  'due_at': 1,
  'grantee_id': 'G-R03',
  'grantee_name': 'Sunshine Care',
  'id': 'GI-R03',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Plymouth City Council'},
 {'amount': 2384.0,
  'due_at': 1,
  'grantee_id': 'G-R04',
  'grantee_name': 'FLIGHTCARE LIMITED',
  'id': 'GI-R04',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Wirral Metropolitan Borough Council'},
 {'amount': 1812.0,
  'due_at': 1,
  'grantee_id': 'G-R05',
  'grantee_name': 'Newground Together',
  'id': 'GI-R05',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Calderdale Metropolitan Borough Council'},
 {'amount': 1128.23,
  'due_at': 1,
  'grantee_id': 'G-R06',
  'grantee_name': 'BROAD OAKS VCT LTD',
  'id': 'GI-R06',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 1237.63,
  'due_at': 1,
  'grantee_id': 'G-R07',
  'grantee_name': 'BULB',
  'id': 'GI-R07',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Wirral Metropolitan Borough Council'},
 {'amount': 2125.0,
  'due_at': 1,
  'grantee_id': 'G-R08',
  'grantee_name': 'Venn Group',
  'id': 'GI-R08',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Plymouth City Council'},
 {'amount': 5040.0,
  'due_at': 1,
  'grantee_id': 'G-R09',
  'grantee_name': 'Peep Learning Ltd',
  'id': 'GI-R09',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Calderdale Metropolitan Borough Council'},
 {'amount': 1487.85,
  'due_at': 1,
  'grantee_id': 'G-R10',
  'grantee_name': 'Michael Batt Foundation',
  'id': 'GI-R10',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Plymouth City Council'},
 {'amount': 984.66,
  'due_at': 1,
  'grantee_id': 'G-R11',
  'grantee_name': 'ASKHAM SERVICES LIMITED',
  'id': 'GI-R11',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 1086.72,
  'due_at': 1,
  'grantee_id': 'G-R12',
  'grantee_name': 'York Council For Voluntary Service',
  'id': 'GI-R12',
  'programme': 'PRG-RESTRICT',
  'source_body': 'City of York Council'},
 {'amount': 1000.0,
  'due_at': 1,
  'grantee_id': 'G-R13',
  'grantee_name': 'Broadway House Chambers',
  'id': 'GI-R13',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Calderdale Metropolitan Borough Council'},
 {'amount': 2284.0,
  'due_at': 1,
  'grantee_id': 'G-R14',
  'grantee_name': 'COURSECHANGE LIMITED T/A GRANGE NURSING HOME',
  'id': 'GI-R14',
  'programme': 'PRG-RESTRICT',
  'source_body': 'Wirral Metropolitan Borough Council'},
 {'amount': 745.67,
  'due_at': 1,
  'grantee_id': 'G-R15',
  'grantee_name': 'Tarmac Ltd',
  'id': 'GI-R15',
  'programme': 'PRG-RESTRICT',
  'source_body': 'City of York Council'}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_total():
    return round(sum(r["amount"] for r in routine()), 2)


# ---- restricted fund, sized so the fund floor still binds exactly as it did at W=7 ----
# RF-2026-04 restricted fund floor 60,000 at every point. At W=7 the whole restricted stream
# (133,000) would have left 47,000 against a 60,000 floor: a 13,000 shortfall, cleared by
# the step-5 tranche to 97,000. Here the deferred item (GI-45, 60,000) is larger than the
# tranche, so the constraint binds on the *cumulative* stream, not on the last item: the
# opening balance is rescaled to keep that same 13,000 shortfall and that same 37,000
# headroom after the tranche, with the routine queue folded in.
FLOOR        = 60000.00
DEFICIT      = 13000.00        # pre-tranche shortfall against the floor, as at W=7
EARLY_EXC    = round(sum(EXC_VALUE[p] for p in EXC_EARLY), 2)      # 73,000
LATE_EXC     = round(sum(EXC_VALUE[p] for p in EXC_LATE), 2)       # 60,000
RGF_EXC      = round(EARLY_EXC + LATE_EXC, 2)                      # 133,000
OPENING      = round(FLOOR - DEFICIT + routine_total() + RGF_EXC, 2)
TRANCHE_AMT  = 50000.00
TRANCHE_STEP = 5
TRANCHE = ("PE-01", TRANCHE_STEP, "acct_rgf", TRANCHE_AMT, "Second tranche from the funder")
# The core fund is untouched by the routine queue: only the two authored core instalments
# draw on it, so its floor is not in play.
CORE_OPENING = 45000.00
CORE_FLOOR   = 10000.00
ACCOUNTS = [
    ("acct_rgf",  "Restricted grant fund 2026-27", OPENING, FLOOR),
    ("acct_core", "Core programme fund 2026-27", CORE_OPENING, CORE_FLOOR),
]
WINDOW_END = 10
