"""Shared, deterministic derivation of OOO-OPS-03's leaver queue.

The routine leavers are ordinary resignations whose last day has already passed, so every
one of them is a full recovery: access revoked, payroll closed, laptop taken back, and the
open case they were carrying handed to their line manager first. The *case subject* names a
real counterparty organisation taken from the frozen OGL v3.0 spend returns, and that name
has to survive the handover verbatim -- a case is passed on, never rewritten.

Leaver names themselves are synthetic: real individuals are never used as task subjects.

The exception leavers (L-01..L-06) are authored and carry every planted trap. They are
reproduced here unchanged from the first edition.

build_state.py, ref_truth.py, golden.py and controls.py all import this module.
"""
import os, sys

TASK_ID = "ooo-ops-03"
N_ROUTINE = 15

# ---------------------------------------------------------------- authored exceptions
# id, name, engagement, role, site, leave_type, last_day_step, manager
EXCEPTIONS = [
 ("L-01","G. Abiodun",    "employee",  "analyst",     "Leeds",    "resignation",       1,"M-Hollis"),
 ("L-02","H. Petrova",    "employee",  "analyst",     "Leeds",    "resignation",       9,"M-Hollis"),
 ("L-03","I. Fairweather","employee",  "coordinator", "Bristol",  "internal_transfer", 1,"M-Okonjo"),
 ("L-04","J. Castellan",  "employee",  "buyer",       "Plymouth", "garden_leave",      9,"M-Okonjo"),
 ("L-05","K. Rasmussen",  "employee",  "finance_mgr", "Leeds",    "retirement",        1,"M-Hollis"),
 ("L-06","L. Nwachukwu",  "contractor","engineer",    "Bristol",  "contract_end",      1,"M-Okonjo"),
]

# Truth for the exception leavers. Unchanged from the first edition.
EXC_EXPECT = {
 "L-01": {"access":"revoked","payroll":"closed","returns":["LPT-7001"],"handover":[]},
 "L-02": {"access":"active", "payroll":"active","returns":[],          "handover":[]},
 "L-03": {"access":"active", "payroll":"active","returns":[],          "handover":[]},
 "L-04": {"access":"revoked","payroll":"active","returns":[],          "handover":[]},
 "L-05": {"access":"revoked","payroll":"closed","returns":["LPT-7005"],"handover":["D-01"]},
 "L-06": {"access":"revoked","payroll":None,    "returns":["FKT-3006"],"handover":["C-01"]},
}
EXC_HOLD = {
 "L-02":"last day falls in a future period",
 "L-03":"internal transfer, not a leaver",
 "L-04":"garden leave: pay runs to the last day",
}
EXC_TRAP = {"L-02":"future_last_day","L-03":"internal_transfer","L-04":"garden_leave",
            "L-05":"held_delegation","L-06":"contractor_no_payroll"}

# ---------------------------------------------------------------- routine leavers
SURNAMES = ["Achterberg","Balogun","Cieslak","Duarte","Erlandsson","Fontaine","Gyamfi",
            "Halvorsen","Iordanou","Jankowski","Kabore","Lindstrom","Moreira","Nakamura",
            "Okonkwo","Petrossian","Quintero","Rautio","Stavrou","Takahashi"]
INITIALS = "NOPQRSTUVWXYZABCDEFGHIJKLM"
MANAGERS = ["M-Hollis", "M-Okonjo"]


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'band': 'B2',
  'counterparty': 'CHARTWELL HOUSE',
  'engagement': 'employee',
  'id': 'L-R01',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Hollis',
  'name': 'N. Achterberg',
  'role': 'analyst',
  'serial': 'LPT-R0001',
  'site': 'Leeds',
  'subject': 'supplier reconciliation: CHARTWELL HOUSE'},
 {'band': 'B2',
  'counterparty': 'ACHIEVE TOGETHER LTD',
  'engagement': 'employee',
  'id': 'L-R02',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Okonjo',
  'name': 'O. Balogun',
  'role': 'analyst',
  'serial': 'LPT-R0002',
  'site': 'Bristol',
  'subject': 'supplier reconciliation: ACHIEVE TOGETHER LTD'},
 {'band': 'B2',
  'counterparty': 'AFFINITY TRUST',
  'engagement': 'employee',
  'id': 'L-R03',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Hollis',
  'name': 'P. Cieslak',
  'role': 'analyst',
  'serial': 'LPT-R0003',
  'site': 'Plymouth',
  'subject': 'supplier reconciliation: AFFINITY TRUST'},
 {'band': 'B2',
  'counterparty': 'SOUTHWELL COURT',
  'engagement': 'employee',
  'id': 'L-R04',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Okonjo',
  'name': 'Q. Duarte',
  'role': 'analyst',
  'serial': 'LPT-R0004',
  'site': 'Leeds',
  'subject': 'supplier reconciliation: SOUTHWELL COURT'},
 {'band': 'B2',
  'counterparty': 'BARCHESTER HEALTHCARE HOMES LTD',
  'engagement': 'employee',
  'id': 'L-R05',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Hollis',
  'name': 'R. Erlandsson',
  'role': 'analyst',
  'serial': 'LPT-R0005',
  'site': 'Bristol',
  'subject': 'supplier reconciliation: BARCHESTER HEALTHCARE HOMES LTD'},
 {'band': 'B2',
  'counterparty': '365 CARE HOMES LIMITED T/A LABURNUM LODGE',
  'engagement': 'employee',
  'id': 'L-R06',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Okonjo',
  'name': 'S. Fontaine',
  'role': 'analyst',
  'serial': 'LPT-R0006',
  'site': 'Plymouth',
  'subject': 'supplier reconciliation: 365 CARE HOMES LIMITED T/A LABURNUM LODGE'},
 {'band': 'B2',
  'counterparty': 'Airtech Environmental Systems',
  'engagement': 'employee',
  'id': 'L-R07',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Hollis',
  'name': 'T. Gyamfi',
  'role': 'analyst',
  'serial': 'LPT-R0007',
  'site': 'Leeds',
  'subject': 'supplier reconciliation: Airtech Environmental Systems'},
 {'band': 'B2',
  'counterparty': 'York Council For Voluntary Service',
  'engagement': 'employee',
  'id': 'L-R08',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Okonjo',
  'name': 'U. Halvorsen',
  'role': 'analyst',
  'serial': 'LPT-R0008',
  'site': 'Bristol',
  'subject': 'supplier reconciliation: York Council For Voluntary Service'},
 {'band': 'B2',
  'counterparty': 'York Travel Limited',
  'engagement': 'employee',
  'id': 'L-R09',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Hollis',
  'name': 'V. Iordanou',
  'role': 'analyst',
  'serial': 'LPT-R0009',
  'site': 'Plymouth',
  'subject': 'supplier reconciliation: York Travel Limited'},
 {'band': 'B2',
  'counterparty': 'Newcross Healthcare Solutions Ltd',
  'engagement': 'employee',
  'id': 'L-R10',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Okonjo',
  'name': 'W. Jankowski',
  'role': 'analyst',
  'serial': 'LPT-R0010',
  'site': 'Leeds',
  'subject': 'supplier reconciliation: Newcross Healthcare Solutions Ltd'},
 {'band': 'B2',
  'counterparty': 'Capita Business Services Ltd',
  'engagement': 'employee',
  'id': 'L-R11',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Hollis',
  'name': 'X. Kabore',
  'role': 'analyst',
  'serial': 'LPT-R0011',
  'site': 'Bristol',
  'subject': 'supplier reconciliation: Capita Business Services Ltd'},
 {'band': 'B2',
  'counterparty': 'Sheffield Hallam University',
  'engagement': 'employee',
  'id': 'L-R12',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Okonjo',
  'name': 'Y. Lindstrom',
  'role': 'analyst',
  'serial': 'LPT-R0012',
  'site': 'Plymouth',
  'subject': 'supplier reconciliation: Sheffield Hallam University'},
 {'band': 'B2',
  'counterparty': 'Michael Batt Foundation',
  'engagement': 'employee',
  'id': 'L-R13',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Hollis',
  'name': 'Z. Moreira',
  'role': 'analyst',
  'serial': 'LPT-R0013',
  'site': 'Leeds',
  'subject': 'supplier reconciliation: Michael Batt Foundation'},
 {'band': 'B2',
  'counterparty': 'Computacenter UK Ltd',
  'engagement': 'employee',
  'id': 'L-R14',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Okonjo',
  'name': 'A. Nakamura',
  'role': 'analyst',
  'serial': 'LPT-R0014',
  'site': 'Bristol',
  'subject': 'supplier reconciliation: Computacenter UK Ltd'},
 {'band': 'B2',
  'counterparty': 'Dunning Plant Hire',
  'engagement': 'employee',
  'id': 'L-R15',
  'last_day_step': 1,
  'leave_type': 'resignation',
  'manager': 'M-Hollis',
  'name': 'B. Okonkwo',
  'role': 'analyst',
  'serial': 'LPT-R0015',
  'site': 'Plymouth',
  'subject': 'supplier reconciliation: Dunning Plant Hire'}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_rows():
    return [(r["id"], r["name"], r["engagement"], r["role"], r["site"],
             r["leave_type"], r["last_day_step"], r["manager"]) for r in routine()]


def all_leaver_rows():
    return list(EXCEPTIONS) + routine_rows()


# ---------------------------------------------------------------- the systems
# id, person, asset_class, serial, status  -- the exception assets, unchanged
EXC_ASSETS = [
 ("IA-01","L-01","laptop",   "LPT-7001","issued"),
 ("IA-02","L-02","laptop",   "LPT-7002","issued"),
 ("IA-03","L-03","laptop",   "LPT-7003","issued"),
 ("IA-04","L-04","laptop",   "LPT-7004","issued"),
 ("IA-05","L-05","laptop",   "LPT-7005","issued"),
 ("IA-06","L-06","field_kit","FKT-3006","issued"),
 ("IA-07","L-04","tablet",   "TAB-9004","issued"),
]
EXC_ACCESS = [
 ("AG-01","L-01","corefin",  "active",None),("AG-02","L-01","intranet","active",None),
 ("AG-03","L-02","corefin",  "active",None),("AG-04","L-02","intranet","active",None),
 ("AG-05","L-03","casework", "active",None),("AG-06","L-03","intranet","active",None),
 ("AG-07","L-04","corefin",  "active",None),("AG-08","L-04","intranet","active",None),
 ("AG-09","L-05","corefin",  "active",None),("AG-10","L-05","intranet","active",None),
 ("AG-11","L-05","approvals","active",None),
 ("AG-12","L-06","fieldops", "active",None),("AG-13","L-06","intranet","active",None),
]
EXC_PAYROLL = [
 ("PR-01","L-01","B2","active",None),("PR-02","L-02","B2","active",None),
 ("PR-03","L-03","B2","active",None),("PR-04","L-04","B3","active",None),
 ("PR-05","L-05","B4","active",None),
]
EXC_DELEGATIONS = [
 ("D-01","L-05",     "approvals_25k","active",None),
 ("D-02","L-01",     "expenses_500", "lapsed",None),
 ("D-03","M-Hollis", "approvals_50k","active",None),
]
EXC_CASES = [
 ("C-01","L-06","Bristol depot survey",         "open",  None),
 ("C-02","L-01","Leeds licence renewal",        "closed",None),
 ("C-03","L-03","Bristol tenancy audit",        "open",  None),
 ("C-04","L-02","Leeds supplier reconciliation","open",  None),
]


def routine_assets():
    return [("IA-R%02d" % i, r["id"], "laptop", r["serial"], "issued")
            for i, r in enumerate(routine(), 1)]


def routine_access():
    out = []
    for i, r in enumerate(routine(), 1):
        for sy in ("corefin", "intranet"):
            out.append(("AG-R%02d-%s" % (i, sy[:3]), r["id"], sy, "active", None))
    return out


def routine_payroll():
    return [("PR-R%02d" % i, r["id"], r["band"], "active", None)
            for i, r in enumerate(routine(), 1)]


def routine_cases():
    return [("C-R%02d" % i, r["id"], r["subject"], "open", None)
            for i, r in enumerate(routine(), 1)]


def all_assets():   return EXC_ASSETS + routine_assets()
def all_access():   return EXC_ACCESS + routine_access()
def all_payroll():  return EXC_PAYROLL + routine_payroll()
def all_delegations(): return list(EXC_DELEGATIONS)
def all_cases():    return EXC_CASES + routine_cases()
