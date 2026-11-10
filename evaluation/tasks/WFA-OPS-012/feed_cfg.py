"""Shared, deterministic derivation of OOO-OPS-07's request queue.

The routine requests are ordinary access requests from individual data subjects. Subject
names are synthetic -- a DSAR is about a person, and real individuals are never used as task
subjects. What is real is the estate behind them: every routine casework record is *about* a
real organisation taken from the frozen OGL v3.0 spend returns, and where that organisation's
staff or counterparties appear in the record the record carries third-party data and cannot
be released without a redaction. The counterparty name is what makes the redaction decision
concrete rather than hypothetical.

The exception requests (R-01..R-06) are authored and carry every planted trap. They are
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



TASK_ID = "ooo-ops-07"
N_ROUTINE = 15

NOW = 10
REPEAT_WINDOW = 8
PHOTO_DOCS   = {"passport", "driving_licence", "national_id_card"}
ADDRESS_DOCS = {"utility_bill", "tenancy_agreement", "bank_statement", "council_tax_bill"}

# ---------------------------------------------------------------- authored exceptions
# id, subject, subject_name, request_type, received_step, prior_response_step, id_evidence, channel
EXCEPTIONS = [
 ("R-01","S-01","H. Abimbola",  "access",  10, 1,    "passport+utility_bill",          "post"),
 ("R-02","S-02","J. Castellanos","access",  9, None, "utility_bill",                   "email"),
 ("R-03","S-03","K. Delacroix", "access",   8, None, "driving_licence+bank_statement", "portal"),
 ("R-04","S-04","L. Mwangi",    "access",   9, None, "passport+tenancy_agreement",     "post"),
 ("R-05","S-05","M. Oyibo",     "erasure", 10, None, "national_id_card+council_tax_bill","portal"),
 ("R-06","S-06","N. Pasqualini","access",   9, 4,    "driving_licence+utility_bill",   "email"),
]
EXC_RECORDS = [
 ("REC-0101","S-01","casework",      "CW/2024/88121","routine"),
 ("REC-0102","S-01","contact_centre","CC/551207",    "routine"),
 ("REC-0103","S-01","benefits",      "BN/4410933",   "routine"),
 ("REC-0201","S-02","casework",      "CW/2023/40115","routine"),
 ("REC-0202","S-02","payroll_hr",    "HR/77214",     "routine"),
 ("REC-0301","S-03","casework",      "CW/2025/10402","routine"),
 ("REC-0302","S-03","archive",       "AR/1998/0071", "routine"),
 ("REC-0303","S-03","casework",      "CW/2025/10477","routine"),
 ("REC-0401","S-04","contact_centre","CC/551884",    "routine"),
 ("REC-0402","S-04","casework",      "CW/2024/90330","third_party"),
 ("REC-0501","S-05","benefits",      "BN/4411502",   "routine"),
 ("REC-0502","S-05","casework",      "CW/2022/33810","routine"),
 ("REC-0601","S-06","casework",      "CW/2025/11903","routine"),
 ("REC-0602","S-06","contact_centre","CC/552310",    "routine"),
]
EXC_EXEMPTIONS = [
 ("EX-01","REC-0303","legal_privilege",      "active",  7),
 ("EX-02","REC-0302","ongoing_investigation","lapsed",  2),
 ("EX-03","REC-0202","ongoing_investigation","active",  6),
 ("EX-04","REC-7731","legal_privilege",      "active",  5),
]

# Truth for the exception requests. Unchanged from the first edition.
EXC_EXPECT = {
 "R-01": {"identity":"passed","disposition":"fulfilled",
          "release":["REC-0101","REC-0102","REC-0103"], "considered":3},
 "R-02": {"identity":"failed","disposition":"identity_not_verified",
          "release":[],                                  "considered":2},
 "R-03": {"identity":"passed","disposition":"fulfilled_in_part",
          "release":["REC-0301","REC-0302"],             "considered":3},
 "R-04": {"identity":"passed","disposition":"fulfilled",
          "release":["REC-0401","REC-0402"],             "considered":2},
 "R-05": {"identity":"passed","disposition":"not_an_access_request",
          "release":[],                                  "considered":2},
 "R-06": {"identity":"passed","disposition":"refused_unfounded",
          "release":[],                                  "considered":2},
}
EXC_TRAP = {"R-01":"repeat_window_near_miss","R-02":"identity_not_verified",
            "R-03":"privilege_vs_lapsed_exemption","R-04":"third_party_redaction",
            "R-05":"wrong_route_erasure","R-06":"manifestly_unfounded"}

# ---------------------------------------------------------------- routine requests
SURNAMES = ["Adeyemi","Blomqvist","Chowdhury","Dimitrova","Esposito","Ferreira","Gundersen",
            "Hashimi","Iversen","Jovanovic","Kowalczyk","Larsen","Mbeki","Novak","Oyelaran"]
INITIALS = "OPQRSTUVWXYZABCDE"

# Per-unit shape. Each routine unit is an ordinary in-time, fully-verified access request.
# The variation is in the estate, which is what the rules act on:
#   exempt_active  an active exemption withholds that record
#   exempt_lapsed  a lapsed exemption must not withhold
#   third_party    the record carries data about a real organisation: redact first
#   prior_outside  a previous response outside the repeat window: not refused
PLAN = [
 dict(n_rec=3, exempt_active=0, exempt_lapsed=0, third_party=True,  prior=None),
 dict(n_rec=2, exempt_active=1, exempt_lapsed=0, third_party=False, prior=None),
 dict(n_rec=3, exempt_active=0, exempt_lapsed=1, third_party=False, prior=NOW - 20),
 dict(n_rec=2, exempt_active=0, exempt_lapsed=0, third_party=True,  prior=None),
 dict(n_rec=4, exempt_active=1, exempt_lapsed=1, third_party=False, prior=None),
 dict(n_rec=2, exempt_active=0, exempt_lapsed=0, third_party=False, prior=NOW - 12),
 dict(n_rec=3, exempt_active=1, exempt_lapsed=0, third_party=True,  prior=None),
 dict(n_rec=2, exempt_active=0, exempt_lapsed=0, third_party=False, prior=None),
 dict(n_rec=3, exempt_active=0, exempt_lapsed=0, third_party=True,  prior=None),
 dict(n_rec=2, exempt_active=1, exempt_lapsed=0, third_party=False, prior=None),
 dict(n_rec=3, exempt_active=0, exempt_lapsed=1, third_party=False, prior=NOW - 30),
 dict(n_rec=2, exempt_active=0, exempt_lapsed=0, third_party=False, prior=None),
 dict(n_rec=4, exempt_active=1, exempt_lapsed=0, third_party=True,  prior=None),
 dict(n_rec=2, exempt_active=0, exempt_lapsed=0, third_party=False, prior=None),
 dict(n_rec=3, exempt_active=0, exempt_lapsed=0, third_party=True,  prior=None),
]
SYSTEMS = ["casework", "contact_centre", "benefits", "payroll_hr", "archive"]
CHANNELS = ["post", "email", "portal"]
GROUNDS = ["legal_privilege", "ongoing_investigation"]


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'channel': 'post',
  'counterparty': 'BROOKHURST PRE SCHOOL',
  'id': 'R-R01',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 0,
           'n_rec': 3,
           'prior': None,
           'third_party': True},
  'prior_response_step': None,
  'received_step': 9,
  'request_type': 'access',
  'subject': 'S-R01',
  'subject_name': 'O. Adeyemi'},
 {'channel': 'email',
  'counterparty': 'ANCHOR HANOVER GROUP T/A NELSON LODGE',
  'id': 'R-R02',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 1,
           'exempt_lapsed': 0,
           'n_rec': 2,
           'prior': None,
           'third_party': False},
  'prior_response_step': None,
  'received_step': 8,
  'request_type': 'access',
  'subject': 'S-R02',
  'subject_name': 'P. Blomqvist'},
 {'channel': 'portal',
  'counterparty': 'Bulrush Horticulture Ltd',
  'id': 'R-R03',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 1,
           'n_rec': 3,
           'prior': -10,
           'third_party': False},
  'prior_response_step': -10,
  'received_step': 10,
  'request_type': 'access',
  'subject': 'S-R03',
  'subject_name': 'Q. Chowdhury'},
 {'channel': 'post',
  'counterparty': 'Housing 21',
  'id': 'R-R04',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 0,
           'n_rec': 2,
           'prior': None,
           'third_party': True},
  'prior_response_step': None,
  'received_step': 9,
  'request_type': 'access',
  'subject': 'S-R04',
  'subject_name': 'R. Dimitrova'},
 {'channel': 'email',
  'counterparty': 'Paradise House Association Ltd',
  'id': 'R-R05',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 1,
           'exempt_lapsed': 1,
           'n_rec': 4,
           'prior': None,
           'third_party': False},
  'prior_response_step': None,
  'received_step': 8,
  'request_type': 'access',
  'subject': 'S-R05',
  'subject_name': 'S. Esposito'},
 {'channel': 'portal',
  'counterparty': 'RED BALLOON LEARNER CENTRE CAMBRIDGE',
  'id': 'R-R06',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0, 'exempt_lapsed': 0, 'n_rec': 2, 'prior': -2, 'third_party': False},
  'prior_response_step': -2,
  'received_step': 10,
  'request_type': 'access',
  'subject': 'S-R06',
  'subject_name': 'T. Ferreira'},
 {'channel': 'post',
  'counterparty': 'RADIS COMMUNITY CARE',
  'id': 'R-R07',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 1,
           'exempt_lapsed': 0,
           'n_rec': 3,
           'prior': None,
           'third_party': True},
  'prior_response_step': None,
  'received_step': 9,
  'request_type': 'access',
  'subject': 'S-R07',
  'subject_name': 'U. Gundersen'},
 {'channel': 'email',
  'counterparty': 'Five Rivers Child Care Limited',
  'id': 'R-R08',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 0,
           'n_rec': 2,
           'prior': None,
           'third_party': False},
  'prior_response_step': None,
  'received_step': 8,
  'request_type': 'access',
  'subject': 'S-R08',
  'subject_name': 'V. Hashimi'},
 {'channel': 'portal',
  'counterparty': "AUNTIE EM'S CHILDMINDING SERVICE",
  'id': 'R-R09',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 0,
           'n_rec': 3,
           'prior': None,
           'third_party': True},
  'prior_response_step': None,
  'received_step': 10,
  'request_type': 'access',
  'subject': 'S-R09',
  'subject_name': 'W. Iversen'},
 {'channel': 'post',
  'counterparty': 'Lorne Stewart PLC',
  'id': 'R-R10',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 1,
           'exempt_lapsed': 0,
           'n_rec': 2,
           'prior': None,
           'third_party': False},
  'prior_response_step': None,
  'received_step': 9,
  'request_type': 'access',
  'subject': 'S-R10',
  'subject_name': 'X. Jovanovic'},
 {'channel': 'email',
  'counterparty': 'Crowther & Shaw Ltd',
  'id': 'R-R11',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 1,
           'n_rec': 3,
           'prior': -20,
           'third_party': False},
  'prior_response_step': -20,
  'received_step': 8,
  'request_type': 'access',
  'subject': 'S-R11',
  'subject_name': 'Y. Kowalczyk'},
 {'channel': 'portal',
  'counterparty': 'Mencap',
  'id': 'R-R12',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 0,
           'n_rec': 2,
           'prior': None,
           'third_party': False},
  'prior_response_step': None,
  'received_step': 10,
  'request_type': 'access',
  'subject': 'S-R12',
  'subject_name': 'Z. Larsen'},
 {'channel': 'post',
  'counterparty': 'Abholly (2008) Ltd',
  'id': 'R-R13',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 1,
           'exempt_lapsed': 0,
           'n_rec': 4,
           'prior': None,
           'third_party': True},
  'prior_response_step': None,
  'received_step': 9,
  'request_type': 'access',
  'subject': 'S-R13',
  'subject_name': 'A. Mbeki'},
 {'channel': 'email',
  'counterparty': 'Npower',
  'id': 'R-R14',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 0,
           'n_rec': 2,
           'prior': None,
           'third_party': False},
  'prior_response_step': None,
  'received_step': 8,
  'request_type': 'access',
  'subject': 'S-R14',
  'subject_name': 'B. Novak'},
 {'channel': 'portal',
  'counterparty': 'ALIWAL HEALTHCARE LTD',
  'id': 'R-R15',
  'id_evidence': 'passport+utility_bill',
  'plan': {'exempt_active': 0,
           'exempt_lapsed': 0,
           'n_rec': 3,
           'prior': None,
           'third_party': True},
  'prior_response_step': None,
  'received_step': 10,
  'request_type': 'access',
  'subject': 'S-R15',
  'subject_name': 'C. Oyelaran'}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_records():
    """Records for each routine subject, plus the counterparty where a record is about one."""
    out = []
    for r in routine():
        spec = r["plan"]; n = spec["n_rec"]
        for k in range(1, n + 1):
            system = SYSTEMS[(int(r["id"][-2:]) + k) % len(SYSTEMS)]
            tp = spec["third_party"] and k == n      # the last record is the third-party one
            out.append({
                "id": "REC-R%s%02d" % (r["id"][-2:], k),
                "subject": r["subject"],
                "holding_system": system,
                "record_ref": "CW/R%s/%02d" % (r["id"][-2:], k),
                "sensitivity": "third_party" if tp else "routine",
                "counterparty": r["counterparty"] if tp else None,
            })
    return out


def routine_exemptions():
    """Active exemptions withhold; lapsed ones do not."""
    out, k = [], 0
    for r in routine():
        spec = r["plan"]; n = spec["n_rec"]
        recs = [x for x in routine_records() if x["subject"] == r["subject"]]
        if spec["exempt_active"]:
            k += 1
            out.append(("EX-R%02d" % k, recs[0]["id"], GROUNDS[k % 2], "active", NOW - 2))
        if spec["exempt_lapsed"]:
            k += 1
            out.append(("EX-R%02d" % k, recs[-1]["id"], GROUNDS[k % 2], "lapsed", NOW - 6))
    return out


def all_requests(): return list(EXCEPTIONS) + [(r["id"], r["subject"], r["subject_name"],
                                                r["request_type"], r["received_step"],
                                                r["prior_response_step"], r["id_evidence"],
                                                r["channel"]) for r in routine()]
def all_records():
    return list(EXC_RECORDS) + [(x["id"], x["subject"], x["holding_system"], x["record_ref"],
                                 x["sensitivity"]) for x in routine_records()]
def all_exemptions(): return list(EXC_EXEMPTIONS) + routine_exemptions()
def all_counterparties(): return {x["id"]: x["counterparty"] for x in routine_records()
                                  if x["counterparty"]}
