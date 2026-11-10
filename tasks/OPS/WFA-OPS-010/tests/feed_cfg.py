"""Shared, deterministic derivation of OOO-OPS-05's complaint queue.

The routine complaints are raised by real customer organisations: the complainant name, and
therefore the account name it must be matched against in the customer master, comes from the
frozen OGL v3.0 spend returns. Matching is the whole first step of the task -- a complaint
whose complainant has no account is not a service complaint -- so a queue of real trading
names makes that step real rather than a formality.

The exception complaints (C-01..C-06) are authored and carry every planted trap. They are
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



TASK_ID = "ooo-ops-05"
N_ROUTINE = 16

NOW = 38
IN_TIME_WINDOW = 12
DELEGATED_LIMIT = 300

# ---------------------------------------------------------------- authored exceptions
# id, complainant, subject, received_step, channel
EXCEPTIONS = [
 ("C-01", "Aurora Orchard Manor",            "service_failure", 34, "email"),
 ("C-02", "Barchester Healthcare Homes Ltd", "billing_error",   33, "portal"),
 ("C-03", "Hillview Residential Home",       "service_failure", 35, "phone"),
 ("C-04", "Four Acres Academy",              "service_failure", 21, "letter"),
 ("C-05", "Missing Link Ltd",                "access_dispute",  36, "portal"),
 ("C-06", "Shared Lives South West",         "service_failure", 37, "email"),
]
EXC_ACCOUNTS = [
 ("A-002", "Barchester Healthcare Homes Ltd", 3, "basic",   "none",       "general"),
 ("A-003", "Hillview Residential Home",       1, "basic",   "registered", "regulated_care"),
 ("A-004", "Four Acres Academy",              2, "managed", "none",       "general"),
 ("A-005", "Missing Link Ltd",                2, "basic",   "none",       "general"),
 ("A-006", "Shared Lives South West",         2, "managed", "none",       "general"),
 ("A-007", "Tracsis Traffic Data Ltd",        1, "managed", "registered", "regulated_care"),
]
EXC_CASES = [
 ("CS-0310", "A-002", "billing_error",  "open",   "C-0188", 29),
 ("CS-0290", "A-005", "access_dispute", "closed", "C-0121", 14),
]
EXC_CLOCKS = [("SLA-0310", "CS-0310", "extended", 44)]

# Truth for the exception complaints. Unchanged from the first edition.
EXC_EXPECT = {
 "C-01": {"account": "",      "disp": "no_account",   "case": None,      "new_case": False,
          "subject": None,            "queue": "",         "due": "",   "scheme": None, "comp": 0},
 "C-02": {"account": "A-002", "disp": "attached",     "case": "CS-0310", "new_case": False,
          "subject": "billing_error", "queue": "extended", "due": "44", "scheme": None, "comp": 0},
 "C-03": {"account": "A-003", "disp": "opened",       "case": None,      "new_case": True,
          "subject": "service_failure", "queue": "priority", "due": "40",
          "scheme": "care_standards", "comp": 0},
 "C-04": {"account": "A-004", "disp": "out_of_time",  "case": None,      "new_case": False,
          "subject": None,            "queue": "",         "due": "",   "scheme": None, "comp": 0},
 "C-05": {"account": "A-005", "disp": "opened",       "case": None,      "new_case": True,
          "subject": "access_dispute", "queue": "standard", "due": "46", "scheme": None, "comp": 0},
 "C-06": {"account": "A-006", "disp": "opened",       "case": None,      "new_case": True,
          "subject": "service_failure", "queue": "standard", "due": "47", "scheme": None,
          "comp": 250},
}
EXC_TRAP = {"C-01": "no_account", "C-02": "duplicate_open_case", "C-03": "mandatory_referral",
            "C-04": "out_of_time", "C-05": "closed_case_is_not_a_duplicate",
            "C-06": "goodwill_entitlement"}

QUEUE_OF = {1: ("priority", 5), 2: ("standard", 10), 3: ("extended", 15)}
SCHEME_OF = {"regulated_care": "care_standards", "regulated_water": "water_redress"}
GOODWILL_OF = {1: 400, 2: 250, 3: 150}

# ---------------------------------------------------------------- routine queue
# Routine complaints span the whole rule space on purpose: some are plain service failures
# on a managed contract (goodwill is due), some are billing or access matters (no goodwill),
# one is a regulated-sector account carrying a vulnerability marker (a referral is due), and
# one is a restatement of an already-open case (attach, do not open). All are in time and all
# have an account, so none of them is a trap -- they are the bulk the rules have to be
# applied to, over and over.
SUBJECTS = ["service_failure", "billing_error", "access_dispute", "service_failure",
            "service_failure", "billing_error", "access_dispute", "service_failure"]
CHANNELS = ["email", "portal", "phone", "letter"]

# Which routine units exercise which special rule.
ATTACH_IDX   = {6}          # restates an open case: attach
REFER_IDX    = {3}          # regulated sector + vulnerability marker: refer
REGULATED_IDX = {3, 6, 11, 14}   # regulated-sector accounts; only the marked ones are referred
REGULATED_UNMARKED_IDX = {6, 14}  # regulated sector but no marker: no referral is due


# self-contained: no authoring-time paths at runtime
# --- frozen at packaging time: the same deterministic draw, resolved to literals ---
_ROUTINE_FROZEN = [{'account': 'A-R01',
  'attach_to': None,
  'channel': 'email',
  'complainant': 'R S M H C & A Western Divisional',
  'contract': 'managed',
  'due': 43,
  'goodwill': 0,
  'id': 'C-R01',
  'queue': 'priority',
  'received_step': 37,
  'scheme': None,
  'sector': 'general',
  'subject': 'service_failure',
  'tier': 1,
  'vulnerability': 'none',
  'window': 5},
 {'account': 'A-R02',
  'attach_to': None,
  'channel': 'portal',
  'complainant': 'York Council For Voluntary Service',
  'contract': 'basic',
  'due': 48,
  'goodwill': 0,
  'id': 'C-R02',
  'queue': 'standard',
  'received_step': 36,
  'scheme': None,
  'sector': 'general',
  'subject': 'billing_error',
  'tier': 2,
  'vulnerability': 'none',
  'window': 10},
 {'account': 'A-R03',
  'attach_to': None,
  'channel': 'phone',
  'complainant': 'Growing Minds Day Nursery Limited',
  'contract': 'managed',
  'due': 53,
  'goodwill': 0,
  'id': 'C-R03',
  'queue': 'extended',
  'received_step': 35,
  'scheme': None,
  'sector': 'general',
  'subject': 'access_dispute',
  'tier': 3,
  'vulnerability': 'none',
  'window': 15},
 {'account': 'A-R04',
  'attach_to': None,
  'channel': 'letter',
  'complainant': 'Sewell Education (york) Ltd',
  'contract': 'managed',
  'due': 43,
  'goodwill': 250,
  'id': 'C-R04',
  'queue': 'priority',
  'received_step': 37,
  'scheme': 'care_standards',
  'sector': 'regulated_care',
  'subject': 'service_failure',
  'tier': 2,
  'vulnerability': 'registered',
  'window': 5},
 {'account': 'A-R05',
  'attach_to': None,
  'channel': 'email',
  'complainant': 'Workman LLP',
  'contract': 'managed',
  'due': 43,
  'goodwill': 0,
  'id': 'C-R05',
  'queue': 'priority',
  'received_step': 36,
  'scheme': None,
  'sector': 'general',
  'subject': 'service_failure',
  'tier': 1,
  'vulnerability': 'none',
  'window': 5},
 {'account': 'A-R06',
  'attach_to': None,
  'channel': 'portal',
  'complainant': 'BARCHESTER HEALTHCARE HOMES LTD',
  'contract': 'basic',
  'due': 48,
  'goodwill': 0,
  'id': 'C-R06',
  'queue': 'standard',
  'received_step': 35,
  'scheme': None,
  'sector': 'general',
  'subject': 'billing_error',
  'tier': 2,
  'vulnerability': 'none',
  'window': 10},
 {'account': 'A-R07',
  'attach_to': 'CS-R07',
  'channel': 'phone',
  'complainant': 'Stoneplan Construction',
  'contract': 'managed',
  'due': 53,
  'goodwill': 0,
  'id': 'C-R07',
  'queue': 'extended',
  'received_step': 37,
  'scheme': None,
  'sector': 'regulated_care',
  'subject': 'access_dispute',
  'tier': 3,
  'vulnerability': 'none',
  'window': 15},
 {'account': 'A-R08',
  'attach_to': None,
  'channel': 'letter',
  'complainant': 'EGERTON HOUSE CIC WIRRAL LIMITED',
  'contract': 'managed',
  'due': 48,
  'goodwill': 250,
  'id': 'C-R08',
  'queue': 'standard',
  'received_step': 36,
  'scheme': None,
  'sector': 'general',
  'subject': 'service_failure',
  'tier': 2,
  'vulnerability': 'none',
  'window': 10},
 {'account': 'A-R09',
  'attach_to': None,
  'channel': 'email',
  'complainant': 'North Halifax Partnership Jubilee Family Hub',
  'contract': 'managed',
  'due': 43,
  'goodwill': 0,
  'id': 'C-R09',
  'queue': 'priority',
  'received_step': 35,
  'scheme': None,
  'sector': 'general',
  'subject': 'service_failure',
  'tier': 1,
  'vulnerability': 'none',
  'window': 5},
 {'account': 'A-R10',
  'attach_to': None,
  'channel': 'portal',
  'complainant': 'Ilminster Avenue E-Act Academy',
  'contract': 'basic',
  'due': 48,
  'goodwill': 0,
  'id': 'C-R10',
  'queue': 'standard',
  'received_step': 37,
  'scheme': None,
  'sector': 'general',
  'subject': 'billing_error',
  'tier': 2,
  'vulnerability': 'none',
  'window': 10},
 {'account': 'A-R11',
  'attach_to': None,
  'channel': 'phone',
  'complainant': 'Box It Document Solutions Limited',
  'contract': 'managed',
  'due': 53,
  'goodwill': 0,
  'id': 'C-R11',
  'queue': 'extended',
  'received_step': 36,
  'scheme': None,
  'sector': 'general',
  'subject': 'access_dispute',
  'tier': 3,
  'vulnerability': 'none',
  'window': 15},
 {'account': 'A-R12',
  'attach_to': None,
  'channel': 'letter',
  'complainant': 'Paradise House Association Ltd',
  'contract': 'managed',
  'due': 43,
  'goodwill': 250,
  'id': 'C-R12',
  'queue': 'priority',
  'received_step': 35,
  'scheme': 'care_standards',
  'sector': 'regulated_care',
  'subject': 'service_failure',
  'tier': 2,
  'vulnerability': 'registered',
  'window': 5},
 {'account': 'A-R13',
  'attach_to': None,
  'channel': 'email',
  'complainant': 'MAGENTA LIVING',
  'contract': 'managed',
  'due': 43,
  'goodwill': 0,
  'id': 'C-R13',
  'queue': 'priority',
  'received_step': 37,
  'scheme': None,
  'sector': 'general',
  'subject': 'service_failure',
  'tier': 1,
  'vulnerability': 'none',
  'window': 5},
 {'account': 'A-R14',
  'attach_to': None,
  'channel': 'portal',
  'complainant': 'Families First (SW) LLP',
  'contract': 'basic',
  'due': 48,
  'goodwill': 0,
  'id': 'C-R14',
  'queue': 'standard',
  'received_step': 36,
  'scheme': None,
  'sector': 'general',
  'subject': 'billing_error',
  'tier': 2,
  'vulnerability': 'none',
  'window': 10},
 {'account': 'A-R15',
  'attach_to': None,
  'channel': 'phone',
  'complainant': '2MINDS NLP LIMITED',
  'contract': 'managed',
  'due': 53,
  'goodwill': 0,
  'id': 'C-R15',
  'queue': 'extended',
  'received_step': 35,
  'scheme': None,
  'sector': 'regulated_care',
  'subject': 'access_dispute',
  'tier': 3,
  'vulnerability': 'none',
  'window': 15},
 {'account': 'A-R16',
  'attach_to': None,
  'channel': 'letter',
  'complainant': 'ALIWAL HEALTHCARE LTD',
  'contract': 'managed',
  'due': 48,
  'goodwill': 250,
  'id': 'C-R16',
  'queue': 'standard',
  'received_step': 37,
  'scheme': None,
  'sector': 'general',
  'subject': 'service_failure',
  'tier': 2,
  'vulnerability': 'none',
  'window': 10}]


def routine():
    return [dict(x) for x in _ROUTINE_FROZEN]


def routine_complaints():
    return [(r["id"], r["complainant"], r["subject"], r["received_step"], r["channel"])
            for r in routine()]


def routine_accounts():
    return [(r["account"], r["complainant"], r["tier"], r["contract"],
             r["vulnerability"], r["sector"]) for r in routine()]


def routine_open_cases():
    """The cases already open when the episode starts: one per routine unit that restates one."""
    return [("CS-R%02d" % i, "A-R%02d" % i, r["subject"], "open", "C-RX%02d" % i, NOW - 6)
            for i, r in enumerate(routine(), 1) if r["attach_to"]]


def routine_open_clocks():
    """The clocks already running on those open cases."""
    return [("SLA-R%02d" % i, "CS-R%02d" % i, r["queue"], r["due"] - 3)
            for i, r in enumerate(routine(), 1) if r["attach_to"]]


def all_complaints(): return list(EXCEPTIONS) + routine_complaints()
def all_accounts():   return list(EXC_ACCOUNTS) + routine_accounts()
def all_cases():      return list(EXC_CASES) + routine_open_cases()
def all_clocks():     return list(EXC_CLOCKS) + routine_open_clocks()
