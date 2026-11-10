"""Shared, deterministic derivation of OOO-OPS-01's joiner queue.

The routine joiners are placements onto real client engagements: the client body each one
is posted to is a real UK public body taken from the frozen OGL v3.0 spend returns, and
that body's name has to be carried from the joiner register into the HR record. The joiner
names themselves are synthetic -- real individuals are never used as task subjects.

The exception joiners (J-01..J-06) are authored and carry every planted trap. They are
reproduced here byte-for-byte from the first edition and must not be edited.

build_state.py, ref_truth.py, golden.py and controls.py all import this module, so the
state and the truth cannot drift apart.
"""
import os, sys

TASK_ID = "ooo-ops-01"
N_ROUTINE = 16

# ---------------------------------------------------------------- authored exceptions
# id, name, engagement, role, site, start_step, clearance, prior_record
EXCEPTIONS = [
 ("J-01","A. Mensah",    "employee",  "analyst",   "Leeds",    1,"granted", None),
 ("J-02","B. Lindqvist", "employee",  "analyst",   "Leeds",    1,"granted", "HR-0042"),
 ("J-03","C. Varga",     "contractor","engineer",  "Bristol",  1,"granted", None),
 ("J-04","D. Oyelaran",  "employee",  "field_tech","Plymouth", 1,"granted", None),
 ("J-05","E. Thackeray", "employee",  "analyst",   "Leeds",    9,"granted", None),
 ("J-06","F. Nurmi",     "employee",  "auditor",   "Leeds",    1,"pending", None),
]

# What each exception joiner must end up with. Unchanged from the first edition.
EXC_EXPECT = {
 "J-01": {"hr":"active","payroll":True, "access":["corefin","intranet"], "asset":"laptop"},
 "J-02": {"hr":"active","payroll":True, "access":["corefin","intranet"], "asset":"laptop"},
 "J-03": {"hr":"active","payroll":False,"access":["intranet"],           "asset":"laptop"},
 "J-04": {"hr":"active","payroll":True, "access":["corefin","intranet"], "asset":None},
 "J-05": {"hr":"pending_start","payroll":True,"access":[],               "asset":None},
 "J-06": {"hr":"active","payroll":True, "access":["intranet"],           "asset":"laptop"},
}
EXC_HOLD = {"J-04":"field_kit out of stock","J-05":"start date in a future period",
            "J-06":"clearance pending for corefin"}
EXC_TRAP = {"J-02":"duplicate_record","J-03":"contractor_no_payroll","J-04":"stock_hold",
            "J-05":"future_start_no_access","J-06":"clearance_gate"}
EXC_REUSE = {"J-02":"HR-0042"}

# ---------------------------------------------------------------- routine placements
# Synthetic surnames for the routine joiners. Deterministic, fixed order, no clock.
SURNAMES = ["Abernethy","Baretto","Chaudhari","Dellapiane","Ekwueme","Falkenrath","Grigorescu",
            "Haraldsen","Ivashchenko","Jablonski","Kuranosuke","Lemarchand","Mbatha","Novosel",
            "Oyarzabal","Pietrangeli","Quintanilla","Radulescu","Sigurdsdottir","Tsakalidis"]
INITIALS = "GKRTMNWDLSEBPFHJVCYZ"
BANDS = ["B1","B2","B3"]


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'band': 'B1',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R01',
  'name': 'G. Abernethy',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Cambridgeshire Insight',
  'start_step': 1,
  'supplier_context': 'REED TALENT SOLUTIONS T/A CONSULTANCY PLUS'},
 {'band': 'B2',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R02',
  'name': 'K. Baretto',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Cheltenham Borough Council',
  'start_step': 1,
  'supplier_context': 'A & E Fire and Security Ltd'},
 {'band': 'B3',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R03',
  'name': 'R. Chaudhari',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Plymouth City Council',
  'start_step': 1,
  'supplier_context': 'Plymouth Hospitals Nhs Trust'},
 {'band': 'B1',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R04',
  'name': 'T. Dellapiane',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Bristol City Council',
  'start_step': 1,
  'supplier_context': 'Bristol Housing & Support Ltd'},
 {'band': 'B2',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R05',
  'name': 'M. Ekwueme',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Calderdale Metropolitan Borough Council',
  'start_step': 1,
  'supplier_context': 'Creative Support Ltd'},
 {'band': 'B3',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R06',
  'name': 'N. Falkenrath',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Calderdale Metropolitan Borough Council',
  'start_step': 1,
  'supplier_context': 'Northern Star Academies Trust'},
 {'band': 'B1',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R07',
  'name': 'W. Grigorescu',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Wirral Metropolitan Borough Council',
  'start_step': 1,
  'supplier_context': 'J P F SYSTEMS LIMITED'},
 {'band': 'B2',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R08',
  'name': 'D. Haraldsen',
  'prior_record': None,
  'role': 'analyst',
  'site': 'City of York Council',
  'start_step': 1,
  'supplier_context': 'York Council For Voluntary Service'},
 {'band': 'B3',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R09',
  'name': 'L. Ivashchenko',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Plymouth City Council',
  'start_step': 1,
  'supplier_context': 'South West Water'},
 {'band': 'B1',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R10',
  'name': 'S. Jablonski',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Cambridgeshire Insight',
  'start_step': 1,
  'supplier_context': 'AISLING LODGE (MD CARE HOMES)'},
 {'band': 'B2',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R11',
  'name': 'E. Kuranosuke',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Cambridgeshire Insight',
  'start_step': 1,
  'supplier_context': 'BRAMLEY COURT'},
 {'band': 'B3',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R12',
  'name': 'B. Lemarchand',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Plymouth City Council',
  'start_step': 1,
  'supplier_context': 'Action for Children'},
 {'band': 'B1',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R13',
  'name': 'P. Mbatha',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Bristol City Council',
  'start_step': 1,
  'supplier_context': 'Black Southwest Network'},
 {'band': 'B2',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R14',
  'name': 'F. Novosel',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Bristol City Council',
  'start_step': 1,
  'supplier_context': 'Alex Fry Rental Properties Ltd'},
 {'band': 'B3',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R15',
  'name': 'H. Oyarzabal',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Wirral Metropolitan Borough Council',
  'start_step': 1,
  'supplier_context': 'AYNSLEY NURSING HOME'},
 {'band': 'B1',
  'clearance': 'granted',
  'engagement': 'employee',
  'id': 'J-R16',
  'name': 'J. Pietrangeli',
  'prior_record': None,
  'role': 'analyst',
  'site': 'Bristol City Council',
  'start_step': 1,
  'supplier_context': 'Airtech Environmental Systems'}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_rows():
    """The routine joiners in joiners-table column order."""
    return [(r["id"], r["name"], r["engagement"], r["role"], r["site"],
             r["start_step"], r["clearance"], r["prior_record"]) for r in routine()]


def all_joiner_rows():
    return list(EXCEPTIONS) + routine_rows()


def site_of():
    """joiner id -> the client body its HR record must name."""
    d = {e[0]: e[4] for e in EXCEPTIONS}
    d.update({r["id"]: r["site"] for r in routine()})
    return d


# ---------------------------------------------------------------- asset capacity
# Laptop stock is sized to exactly cover the entitled issues, so the capacity constraint
# binds: one laptop beyond entitlement overdraws the store. field_kit stays at zero, which
# is what keeps J-04 on hold.
def laptop_demand():
    n = sum(1 for e in EXC_EXPECT.values() if e["asset"] == "laptop")
    return n + N_ROUTINE


LAPTOP_STOCK   = laptop_demand()          # exactly sufficient
FIELD_KIT_STOCK = 0                       # unchanged: the planted stock hold
TABLET_STOCK   = 6                        # unchanged

def stock_rows():
    return [("ST-LAP", "laptop", LAPTOP_STOCK),
            ("ST-TOOL", "field_kit", FIELD_KIT_STOCK),
            ("ST-TAB", "tablet", TABLET_STOCK)]

def stock_after():
    return {"laptop": LAPTOP_STOCK - laptop_demand(), "field_kit": FIELD_KIT_STOCK,
            "tablet": TABLET_STOCK}
