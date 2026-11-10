"""Shared, deterministic derivation of OOO-OPS-06's renewal list.

The routine contracts are held with real counterparties: the trading name comes from the
frozen OGL v3.0 spend returns, and it has to be carried from the contract register onto the
CRM opportunity verbatim. Each routine contract is an ordinary renewal: the index for its
series in the renewal period applies, the indexed value stays under the re-tender threshold,
the legal review for that period is cleared, the contract has not already been renewed, no
notice has been served, and the indexed value lands inside one signatory band or the next.

The exception contracts (K-01..K-06) are authored and carry every planted trap. They are
reproduced here unchanged from the first edition.

build_state.py, ref_truth.py, golden.py and controls.py all import this module.
"""
import os, re, sys


# real_feed draws rows verbatim from the published returns, and those returns carry a few
# rows that are not organisations at all: placeholders ("REDACTED", "Redacted personal
# data") where the paying body suppressed the payee, and sole traders published under a
# personal name. A counterparty the task then has to match, route or own has to be an
# organisation, so those rows are skipped and the draw continues with a different salt.
_NOT_ORG = re.compile(
    r"REDACT|PERSONAL DATA|^N/?A$|^VARIOUS\b|^MR\b|^MRS\b|^MS\b|^MISS\b|^DR\b|\s-\s",
    re.I)


def _norm_name(s):
    return re.sub(r"[^A-Z0-9]", "", str(s).upper())


def _orgs(n, lo=600.0, hi=24000.0):
    """n distinct real organisation names, placeholders and sole traders skipped."""
    out, seen = [], set()
    for k in range(12):
        salt = "" if k == 0 else "-org%d" % k
        for x in real_feed.draw(TASK_ID + salt, n * 3, lo=lo, hi=hi):
            nm = re.sub(r"\s+", " ", x["supplier"]).strip()
            if _NOT_ORG.search(nm):
                continue
            kk = _norm_name(nm)
            if kk in seen:
                continue
            seen.add(kk)
            out.append(dict(x, supplier=nm))
            if len(out) >= n:
                return out
    return out



TASK_ID = "ooo-ops-06"
N_ROUTINE = 16

NOW = 52
PERIOD = "2028"
RETENDER_THRESHOLD = 500000.0
START_STEP = 60
EXECUTABLE = ("cleared", "cleared_with_conditions")

# ---------------------------------------------------------------- authored exceptions
# id, counterparty, current_value, index_series, notice_state, renewed_through, term_end_step
EXCEPTIONS = [
 ("K-01", "Structural Soils Ltd.",         120000.0, "CPIH",   "none",                 "2027", 59),
 ("K-02", "City & Guilds Ltd",             487000.0, "CPIH",   "none",                 "2027", 59),
 ("K-03", "Learning Partnership West Cic",  90000.0, "CPIH",   "none",                 "2027", 59),
 ("K-04", "Neopost Ltd",                    76000.0, "CPIH",   "none",                 "2028", 119),
 ("K-05", "Gas Flare Services Ltd",        210000.0, "ENERGY", "served_by_counterparty","2027", 59),
 ("K-06", "Shared Lives South West",       143000.0, "ENERGY", "none",                 "2027", 59),
]
EXC_INDICES = [
 ("IDX-CPIH-2027",   "CPIH",   "2027", 10210),
 ("IDX-CPIH-2028",   "CPIH",   "2028", 10450),
 ("IDX-ENERGY-2027", "ENERGY", "2027", 10340),
 ("IDX-ENERGY-2028", "ENERGY", "2028", 10800),
 ("IDX-RPI-2028",    "RPI",    "2028", 10620),
]
EXC_REVIEWS = [
 ("LR-2027-01", "K-01", "2027", "unresolved",            "V. Okonkwo"),
 ("LR-2028-01", "K-01", "2028", "cleared",               "V. Okonkwo"),
 ("LR-2028-02", "K-02", "2028", "cleared",               "V. Okonkwo"),
 ("LR-2027-03", "K-03", "2027", "cleared",               "N. Baptiste"),
 ("LR-2028-03", "K-03", "2028", "unresolved",            "N. Baptiste"),
 ("LR-2028-04", "K-04", "2028", "cleared",               "V. Okonkwo"),
 ("LR-2028-05", "K-05", "2028", "cleared",               "N. Baptiste"),
 ("LR-2028-06", "K-06", "2028", "cleared_with_conditions","N. Baptiste"),
]
SIGNATORIES = [
 ("S-LOW",  "R. Abioye",    150000.0,  "active"),
 ("S-MID",  "P. Castellan", 400000.0,  "active"),
 ("S-HIGH", "M. Trevelyan", 2000000.0, "active"),
 ("S-OLD",  "H. Dunmore",   600000.0,  "revoked"),
]
EXC_OPPS      = [("OPP-0041", "K-04", "Neopost Ltd", "closed_won", 79420.0)]
EXC_SCHEDULES = [("FS-0041", "K-04", 79420.0, 60, "S-LOW")]

# Truth for the exception contracts. Unchanged from the first edition.
EXC_EXPECT = {
 "K-01": {"disp": "renewed",         "value": 125400.0, "stage": "closed_won",
          "schedule": True,  "signatory": "S-LOW"},
 "K-02": {"disp": "re_tender",       "value": 508915.0, "stage": "re_tender",
          "schedule": False, "signatory": ""},
 "K-03": {"disp": "legal_hold",      "value": 94050.0,  "stage": "legal_hold",
          "schedule": False, "signatory": ""},
 "K-04": {"disp": "already_renewed", "value": None,     "stage": None,
          "schedule": False, "signatory": ""},
 "K-05": {"disp": "lapsed",          "value": 226800.0, "stage": "lapsed",
          "schedule": False, "signatory": ""},
 "K-06": {"disp": "renewed",         "value": 154440.0, "stage": "closed_won",
          "schedule": True,  "signatory": "S-MID"},
}
EXC_TRAP = {"K-01": "stale_review_period", "K-02": "indexed_value_crosses_retender",
            "K-03": "legal_unresolved", "K-04": "already_renewed",
            "K-05": "notice_served", "K-06": "signatory_band_crossed"}
EXC_INITIAL_OPPS = {"OPP-0041"}
EXC_INITIAL_SCHEDULES = {"FS-0041"}


# ---------------------------------------------------------------- the index
def factors():
    """series -> {period: factor}, built from the authored indices."""
    f = {}
    for _, series, period, bp in EXC_INDICES:
        f.setdefault(series, {})[period] = bp / 10000.0
    return f

FACTOR = factors()

def indexed(series, current):
    return round(current * FACTOR[series][PERIOD], 2)

def signatory_for(value):
    """The active signatory of lowest authority whose limit covers the value."""
    elig = [s for s in SIGNATORIES if s[3] == "active" and s[2] >= value]
    elig.sort(key=lambda s: s[2])
    return elig[0][0] if elig else ""


# ---------------------------------------------------------------- routine contracts
# Values chosen so the indexed figure lands inside a band, and so at least a few of them
# cross from one band into the next -- the signatory step is then a real lookup rather than
# a constant.
ROUTINE_PLAN = [
 # (current_value, series)
 ( 60000.0, "CPIH"), ( 95000.0, "CPIH"), (110000.0, "CPIH"), ( 72000.0, "CPIH"),
 (130000.0, "ENERGY"), ( 68000.0, "ENERGY"), ( 88000.0, "ENERGY"), (118000.0, "ENERGY"),
 (145000.0, "CPIH"), ( 52000.0, "ENERGY"), (200000.0, "CPIH"), ( 80000.0, "CPIH"),
 ( 99000.0, "ENERGY"), (125000.0, "CPIH"), ( 61000.0, "ENERGY"), (105000.0, "CPIH"),
]
REVIEWERS = ["V. Okonkwo", "N. Baptiste"]


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'counterparty': 'BROAD OAKS VCT LTD',
  'current_value': 60000.0,
  'id': 'K-R01',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'V. Okonkwo',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 62700.0},
 {'counterparty': 'Jala Minibuses Gb Ltd',
  'current_value': 95000.0,
  'id': 'K-R02',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'N. Baptiste',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 99275.0},
 {'counterparty': 'York Pullman Bus Company Ltd',
  'current_value': 110000.0,
  'id': 'K-R03',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'V. Okonkwo',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 114950.0},
 {'counterparty': 'F1 Security Services Ltd',
  'current_value': 72000.0,
  'id': 'K-R04',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'N. Baptiste',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 75240.0},
 {'counterparty': 'Streamline Taxi & Private Hire Car Ass',
  'current_value': 130000.0,
  'id': 'K-R05',
  'index_series': 'ENERGY',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'V. Okonkwo',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 140400.0},
 {'counterparty': 'FOSTERING PEOPLE LIMITED',
  'current_value': 68000.0,
  'id': 'K-R06',
  'index_series': 'ENERGY',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'N. Baptiste',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 73440.0},
 {'counterparty': 'ATHENA HEALTHCARE (NEW BRIGHTON TWO) LIMITED',
  'current_value': 88000.0,
  'id': 'K-R07',
  'index_series': 'ENERGY',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'V. Okonkwo',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 95040.0},
 {'counterparty': 'Ian Williams Ltd',
  'current_value': 118000.0,
  'id': 'K-R08',
  'index_series': 'ENERGY',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'N. Baptiste',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 127440.0},
 {'counterparty': 'Ben Thornber & Sons Ltd',
  'current_value': 145000.0,
  'id': 'K-R09',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'V. Okonkwo',
  'signatory': 'S-MID',
  'term_end_step': 59,
  'value': 151525.0},
 {'counterparty': 'Housing 21',
  'current_value': 52000.0,
  'id': 'K-R10',
  'index_series': 'ENERGY',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'N. Baptiste',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 56160.0},
 {'counterparty': '365 CARE HOMES LIMITED T/A LABURNUM LODGE',
  'current_value': 200000.0,
  'id': 'K-R11',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'V. Okonkwo',
  'signatory': 'S-MID',
  'term_end_step': 59,
  'value': 209000.0},
 {'counterparty': 'SOUTH CAMBRIDGESHIRE DISTRICT COUNCIL',
  'current_value': 80000.0,
  'id': 'K-R12',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'N. Baptiste',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 83600.0},
 {'counterparty': 'National Fostering Agency',
  'current_value': 99000.0,
  'id': 'K-R13',
  'index_series': 'ENERGY',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'V. Okonkwo',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 106920.0},
 {'counterparty': 'Richard Bray',
  'current_value': 125000.0,
  'id': 'K-R14',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'N. Baptiste',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 130625.0},
 {'counterparty': 'Boringdon Hall Hotel',
  'current_value': 61000.0,
  'id': 'K-R15',
  'index_series': 'ENERGY',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'V. Okonkwo',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 65880.0},
 {'counterparty': 'BEES CARE LTD',
  'current_value': 105000.0,
  'id': 'K-R16',
  'index_series': 'CPIH',
  'notice_state': 'none',
  'renewed_through': '2027',
  'reviewer': 'N. Baptiste',
  'signatory': 'S-LOW',
  'term_end_step': 59,
  'value': 109725.0}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_contracts():
    return [(r["id"], r["counterparty"], r["current_value"], r["index_series"],
             r["notice_state"], r["renewed_through"], r["term_end_step"]) for r in routine()]


def routine_reviews():
    """Every routine contract has a cleared review for the renewal period."""
    return [("LR-R%02d" % i, r["id"], PERIOD, "cleared", r["reviewer"])
            for i, r in enumerate(routine(), 1)]


def all_contracts(): return list(EXCEPTIONS) + routine_contracts()
def all_indices():   return list(EXC_INDICES)
def all_reviews():   return list(EXC_REVIEWS) + routine_reviews()
def all_opps():      return list(EXC_OPPS)
def all_schedules(): return list(EXC_SCHEDULES)
