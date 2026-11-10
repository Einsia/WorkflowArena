"""Shared, deterministic derivation of OOO-OPS-02's applicant queue.

The routine applicants are real trading names: the supplier naming and the expected annual
value come from the frozen OGL v3.0 spend returns, so the name written into the supplier
master has to be carried across verbatim from the application. Every routine applicant is an
ordinary case -- a clean company, sole-sanctions-screen, financial standing and insurance in
order, an account in its own name -- and is processed under the published band rule.

The exception applicants (A-01..A-06) are authored and carry every planted trap. They are
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



TASK_ID = "ooo-ops-02"
N_ROUTINE = 16

# ---------------------------------------------------------------- authored exceptions
# id, supplier_name, legal_form, category, expected_annual_value,
# insurance_expiry_step, bank_account_holder, existing_master_id
EXCEPTIONS = [
 ("A-01","Acorn Health & Safety Ltd",  "company",    "services", 40000.0, 40,
  "Acorn Health & Safety Ltd",   None),
 ("A-02","AVL Solutions Ltd",          "company",    "works",    90000.0, 40,
  "AVL Solutions Ltd",           None),
 ("A-03","ACS Business Supplies Ltd",  "company",    "goods",    18000.0,  8,
  "ACS Business Supplies Ltd",   None),
 ("A-04","R. Pell Groundworks",        "sole_trader","services", 12000.0, None,
  "R. Pell Groundworks",         None),
 ("A-05","A B Fluid Power Ltd",        "company",    "goods",    60000.0, 40,
  "A B Fluid Power Ltd",         "SM-0317"),
 ("A-06","APE Fire & Security Ltd",    "company",    "works",    55000.0, 40,
  "Alder Park Holdings Ltd",     None),
]

SANCTIONS = [
 ("SR-01","AVL Solutions Ltd",              "asset_freeze"),
 ("SR-02","ACS Business Supplies (Wales) Ltd","asset_freeze"),
 ("SR-03","Orbis Marine Trading SA",        "trade_restriction"),
 ("SR-04","Acorn Minerals Ltd",             "trade_restriction"),
 ("SR-05","Penrose Shipping Company",       "asset_freeze"),
]

# Truth for the exception applicants. Unchanged from the first edition.
EXC_EXPECT = {
 "A-01": {"dd": {"sanctions":"pass","financial_standing":"pass","insurance":"pass"},
          "master":"active",  "bank":True,  "ceiling":100000.0, "disposition":"approved"},
 "A-02": {"dd": {"sanctions":"fail"},
          "master":None,      "bank":False, "ceiling":None,     "disposition":"rejected"},
 "A-03": {"dd": {"sanctions":"pass","financial_standing":"pass","insurance":"fail"},
          "master":"pending", "bank":False, "ceiling":None,     "disposition":"held"},
 "A-04": {"dd": {"sanctions":"pass","financial_standing":"pass"},
          "master":"active",  "bank":True,  "ceiling":25000.0,  "disposition":"approved"},
 "A-05": {"dd": {"sanctions":"pass","financial_standing":"pass","insurance":"pass"},
          "master":"active",  "bank":True,  "ceiling":100000.0, "disposition":"approved"},
 "A-06": {"dd": {"sanctions":"pass","financial_standing":"pass","insurance":"pass"},
          "master":"pending", "bank":False, "ceiling":None,     "disposition":"held"},
}
EXC_REUSE = {"A-05": "SM-0317"}
EXC_NOTE = {
 "A-02": "named on the sanctions register",
 "A-03": "employers liability insurance lapsed",
 "A-06": "bank account holder is not the applicant",
}
EXC_TRAP = {"A-02":"sanctions_match","A-03":"insurance_lapsed","A-04":"sole_trader_exempt",
            "A-05":"duplicate_master","A-06":"bank_holder_mismatch"}

# ---------------------------------------------------------------- band rule
# As published in workspace/policies/bank-details-and-spend-ceilings.md.
def band_ceiling(v):
    """Ceiling implied by the expected annual value; None where the board sets it."""
    if v is None: return None
    if v < 25000.0:   return 25000.0
    if v <= 100000.0: return 100000.0
    return None


_PERSON = re.compile(r"^(mr|mrs|ms|miss|dr)\b", re.I)
_PLACEHOLDER = re.compile(r"REDACT|PERSONAL DATA|^N/?A$|^VARIOUS\b", re.I)

def _legal_form(name):
    """Real spend data contains unincorporated traders as well as companies. An individual
    trading name is a sole trader: it is exempt from the employers liability check."""
    return "sole_trader" if _PERSON.match(name.strip()) else "company"


def _draw_band(lo, hi, n, tag):
    """Draw n real trading names whose real spend falls inside [lo, hi]."""
    banned = {s[1].lower() for s in SANCTIONS}
    out, seen = [], set()
    for k in range(12):
        salt = "" if k == 0 else "-org%d" % k
        for x in real_feed.draw(TASK_ID + "-" + tag + salt, 400, lo=lo, hi=hi):
            name = re.sub(r"\s+", " ", x["supplier"]).strip()
            # a placeholder is not an applicant at all; a sole trader is, and is kept
            if _PLACEHOLDER.search(name):
                continue
            key = _norm_name(name)
            if name.lower() in banned or key in seen:
                continue
            seen.add(key); out.append(dict(x, supplier=name))
            if len(out) >= n:
                return out
    return out


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'board': False,
  'category': 'goods',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'Brayborne Facilities Services Limited',
  'id': 'A-R00',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'Brayborne Facilities Services Limited',
  'value': 3980.34},
 {'board': False,
  'category': 'services',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'Halcrow Group Limited',
  'id': 'A-R01',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'Halcrow Group Limited',
  'value': 4170.41},
 {'board': False,
  'category': 'works',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'INFORM CPI LIMITED',
  'id': 'A-R02',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'INFORM CPI LIMITED',
  'value': 10050.0},
 {'board': False,
  'category': 'goods',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'CALENDULA BEBINGTON LIMITED',
  'id': 'A-R03',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'CALENDULA BEBINGTON LIMITED',
  'value': 2532.0},
 {'board': False,
  'category': 'services',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'York Council For Voluntary Service',
  'id': 'A-R04',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'York Council For Voluntary Service',
  'value': 5233.56},
 {'board': False,
  'category': 'works',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'Lifeways Community Care',
  'id': 'A-R05',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'Lifeways Community Care',
  'value': 1439.2},
 {'board': False,
  'category': 'goods',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'Ms Synthetic Sole Trader 006',
  'id': 'A-R06',
  'insurance': None,
  'legal_form': 'sole_trader',
  'name': 'Ms Synthetic Sole Trader 006',
  'value': 1350.0},
 {'board': False,
  'category': 'services',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'Abacus Environmental Assessments Ltd',
  'id': 'A-R07',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'Abacus Environmental Assessments Ltd',
  'value': 1327.51},
 {'board': False,
  'category': 'works',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'York Travel Limited',
  'id': 'A-R08',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'York Travel Limited',
  'value': 1099.98},
 {'board': False,
  'category': 'goods',
  'ceiling': 25000.0,
  'existing': None,
  'holder': 'Boningale Nurseries',
  'id': 'A-R09',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'Boningale Nurseries',
  'value': 1332.0},
 {'board': False,
  'category': 'services',
  'ceiling': 100000.0,
  'existing': None,
  'holder': 'C & K Careers Ltd',
  'id': 'A-R10',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'C & K Careers Ltd',
  'value': 26213.42},
 {'board': False,
  'category': 'works',
  'ceiling': 100000.0,
  'existing': None,
  'holder': 'Hexagon Care Services Ltd',
  'id': 'A-R11',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'Hexagon Care Services Ltd',
  'value': 26250.68},
 {'board': False,
  'category': 'goods',
  'ceiling': 100000.0,
  'existing': None,
  'holder': 'NHS West Yorkshire Integrated Care Board',
  'id': 'A-R12',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'NHS West Yorkshire Integrated Care Board',
  'value': 45532.03},
 {'board': False,
  'category': 'services',
  'ceiling': 100000.0,
  'existing': None,
  'holder': 'INDEPENDENCE SUPPORT LIMITED',
  'id': 'A-R13',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'INDEPENDENCE SUPPORT LIMITED',
  'value': 92725.64},
 {'board': True,
  'category': 'works',
  'ceiling': None,
  'existing': None,
  'holder': 'BRIGHT HORIZONS @ ELY',
  'id': 'A-R14',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'BRIGHT HORIZONS @ ELY',
  'value': 323384.8},
 {'board': True,
  'category': 'goods',
  'ceiling': None,
  'existing': None,
  'holder': 'LADYBIRD DAY NURSERY ICP',
  'id': 'A-R15',
  'insurance': 40,
  'legal_form': 'company',
  'name': 'LADYBIRD DAY NURSERY ICP',
  'value': 219959.89}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_rows():
    return [(r["id"], r["name"], r["legal_form"], r["category"], r["value"],
             r["insurance"], r["holder"], r["existing"]) for r in routine()]


def exception_rows():
    return list(EXCEPTIONS)


def all_applicant_rows():
    return exception_rows() + routine_rows()
