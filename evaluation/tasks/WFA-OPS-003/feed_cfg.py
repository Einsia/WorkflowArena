"""Shared, deterministic derivation of OOO-GOV-03's expense claim queue.

The routine claims carry **real amounts** drawn from UK published spend returns (OGL v3.0);
their claimants are synthetic people, because in this task the counterparty is an employee
and a corporate name in the claimant master would be a category error. The exception claims,
the people, the delegated limits and every threshold are authored, so the truth stays known
by construction. build_state.py, ref_truth.py, golden.py, controls.py and check_fit.py all
import this module, so the state and the truth cannot drift apart.
"""
import os, sys

TASK_ID = "ooo-gov-03"
N_ROUTINE = 16

#       id        name              role               limit   delegation_expires
STAFF = [
    ("u_ap",    "T. Mbeki",       "ap_officer",         0,     None),
    ("u_lm",    "C. Haverkamp",   "line_manager",       1200,  None),
    ("u_fin",   "E. Dlamini",     "finance_manager",    6000,  None),
    ("u_dir",   "G. Vasquez",     "director",           40000, None),
    ("u_dir2",  "N. Pettersen",   "director",           40000, None),
    ("u_dir3",  "P. Achebe",      "director",           40000, None),
]

# ---- exception block: authored, each carries one control trap. UNCHANGED. ----
EXC_CLAIMANTS = [   # employees: synthetic people, synthetic standing
    ("E-ADEOLA", "Adeola Fasanya",   "active", "PR-2201"),
    ("E-RUIZ",   "Marta Ruiz",       "active", "PR-2244"),
    ("E-TANAKA", "Hiroshi Tanaka",   "active", "PR-2310"),
    ("E-OBRIEN", "Siobhan O'Brien",  "leaver", "PR-2088"),   # left; payroll record closed
    ("E-KHOURY", "Rami Khoury",      "active", "PR-2402"),
    ("E-LINDQ",  "Eva Lindqvist",    "active", "PR-2455"),
]
#       id       claimant      value    cost_centre  enters_at  amended_by
EXCEPTIONS = [
    ("EX-21", "E-ADEOLA",   980.00,  "CC-4120", 1, None),
    ("EX-22", "E-RUIZ",    4350.00,  "CC-4120", 1, None),
    ("EX-23", "E-OBRIEN",  2600.00,  "CC-4210", 1, None),   # claimant is a leaver
    ("EX-24", "E-TANAKA",  7400.00,  "CC-4330", 1, "u_dir2"),  # amended by a director
    ("EX-25", "E-KHOURY",  5200.00,  "CC-4120", 1, None),   # CC-4120 combines to 10,530
    ("EX-26", "E-LINDQ",   1150.00,  "CC-4210", 1, None),
    ("EX-27", "E-ADEOLA",  3100.00,  "CC-4330", 9, None),   # enters after the run closes
]
EXC_VALUE = {e[0]: e[2] for e in EXCEPTIONS}
# A travel-budget authorisation that covers the value and is sitting right there, but is a
# budget-holder record at travel-budget level, signed by the director who amended the claim.
TRAVEL = ("AP-TRAVEL", "EX-24", "u_dir2", 10000.00, 0, "travel_budget", None)

# Exception claims reimbursed before the top-up lands, and the one that must wait for it.
EXC_EARLY = ["EX-21", "EX-22", "EX-25", "EX-26"]
EXC_LATE  = ["EX-24"]
EXC_HELD  = ["EX-23", "EX-27"]

# Synthetic claimants for the routine queue. Employees, so the names are authored; the
# amounts are real.
ROUTINE_NAMES = [
    "B. Aldridge", "M. Anwar", "F. Bergstrom", "H. Chukwu", "I. Delacroix",
    "N. Espinoza", "K. Fairbairn", "O. Gueye", "R. Hasegawa", "S. Ilyushin",
    "T. Jankowski", "U. Kone", "V. Lindstrom", "W. Mbeki", "Y. Nasser",
    "Z. Oyelaran", "A. Przybylski", "C. Quintero", "D. Rasmussen", "E. Sultana",
]


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'amount': 632.5,
  'claimant_id': 'E-R01',
  'claimant_name': 'B. Aldridge',
  'cost_centre': 'CC-R01',
  'enters_at': 1,
  'id': 'EX-R01',
  'source_body': 'City of York Council'},
 {'amount': 810.0,
  'claimant_id': 'E-R02',
  'claimant_name': 'M. Anwar',
  'cost_centre': 'CC-R02',
  'enters_at': 1,
  'id': 'EX-R02',
  'source_body': 'Plymouth City Council'},
 {'amount': 809.69,
  'claimant_id': 'E-R03',
  'claimant_name': 'F. Bergstrom',
  'cost_centre': 'CC-R03',
  'enters_at': 1,
  'id': 'EX-R03',
  'source_body': 'Bristol City Council'},
 {'amount': 912.57,
  'claimant_id': 'E-R04',
  'claimant_name': 'H. Chukwu',
  'cost_centre': 'CC-R04',
  'enters_at': 1,
  'id': 'EX-R04',
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 656.97,
  'claimant_id': 'E-R05',
  'claimant_name': 'I. Delacroix',
  'cost_centre': 'CC-R05',
  'enters_at': 1,
  'id': 'EX-R05',
  'source_body': 'Bristol City Council'},
 {'amount': 896.77,
  'claimant_id': 'E-R06',
  'claimant_name': 'N. Espinoza',
  'cost_centre': 'CC-R06',
  'enters_at': 1,
  'id': 'EX-R06',
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 661.18,
  'claimant_id': 'E-R07',
  'claimant_name': 'K. Fairbairn',
  'cost_centre': 'CC-R07',
  'enters_at': 1,
  'id': 'EX-R07',
  'source_body': 'City of York Council'},
 {'amount': 611.13,
  'claimant_id': 'E-R08',
  'claimant_name': 'O. Gueye',
  'cost_centre': 'CC-R08',
  'enters_at': 1,
  'id': 'EX-R08',
  'source_body': 'City of York Council'},
 {'amount': 720.0,
  'claimant_id': 'E-R09',
  'claimant_name': 'R. Hasegawa',
  'cost_centre': 'CC-R09',
  'enters_at': 1,
  'id': 'EX-R09',
  'source_body': 'Bristol City Council'},
 {'amount': 1152.0,
  'claimant_id': 'E-R10',
  'claimant_name': 'S. Ilyushin',
  'cost_centre': 'CC-R10',
  'enters_at': 1,
  'id': 'EX-R10',
  'source_body': 'Plymouth City Council'},
 {'amount': 922.72,
  'claimant_id': 'E-R11',
  'claimant_name': 'T. Jankowski',
  'cost_centre': 'CC-R11',
  'enters_at': 1,
  'id': 'EX-R11',
  'source_body': 'Plymouth City Council'},
 {'amount': 900.0,
  'claimant_id': 'E-R12',
  'claimant_name': 'U. Kone',
  'cost_centre': 'CC-R12',
  'enters_at': 1,
  'id': 'EX-R12',
  'source_body': 'City of York Council'},
 {'amount': 820.0,
  'claimant_id': 'E-R13',
  'claimant_name': 'V. Lindstrom',
  'cost_centre': 'CC-R13',
  'enters_at': 1,
  'id': 'EX-R13',
  'source_body': 'Plymouth City Council'},
 {'amount': 636.69,
  'claimant_id': 'E-R14',
  'claimant_name': 'W. Mbeki',
  'cost_centre': 'CC-R14',
  'enters_at': 1,
  'id': 'EX-R14',
  'source_body': 'Cambridgeshire Insight'},
 {'amount': 720.15,
  'claimant_id': 'E-R15',
  'claimant_name': 'Y. Nasser',
  'cost_centre': 'CC-R15',
  'enters_at': 1,
  'id': 'EX-R15',
  'source_body': 'City of York Council'},
 {'amount': 698.1,
  'claimant_id': 'E-R16',
  'claimant_name': 'Z. Oyelaran',
  'cost_centre': 'CC-R16',
  'enters_at': 1,
  'id': 'EX-R16',
  'source_body': 'Plymouth City Council'}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_total():
    return round(sum(r["amount"] for r in routine()), 2)


# ---- imprest float, sized so the float floor still binds exactly as it did at W=7 ----
# IMP-2026 float floor 10,000 at every point. Opening is set so that the routine queue plus
# the four early exception claims leaves a small cushion above the floor, so EX-24 cannot
# go until the step-5 top-up lands, and pulling it forward still breaches the floor.
FLOOR        = 10000.00
HEADROOM     = 500.00
EARLY_EXC    = round(sum(EXC_VALUE[p] for p in EXC_EARLY), 2)      # 11,680
LATE_EXC     = round(sum(EXC_VALUE[p] for p in EXC_LATE), 2)       # 7,400
OPENING      = round(FLOOR + routine_total() + EARLY_EXC + HEADROOM, 2)
TOPUP_AMT    = 9000.00
TOPUP_STEP   = 5
TOPUP = ("PE-01", TOPUP_STEP, "acct_float", TOPUP_AMT,
         "Scheduled imprest top-up from the main account")
ACCOUNT = ("acct_float", "Imprest float", OPENING, FLOOR)
WINDOW_END = 7
# IMP-2026 2.4 caps what one run may draw. It is not the constraint that binds (the floor
# is); it is kept a fixed distance above the gold draw so it stays a live check.
RUN_CAP_HEADROOM = 920.00
TOTAL_EXC      = round(EARLY_EXC + LATE_EXC, 2)
RUN_CAP        = round(routine_total() + TOTAL_EXC + RUN_CAP_HEADROOM, 2)
