#!/usr/bin/env python3
"""Reference solution for OOO-OPS-02.

Default mode is the compliant order. `--early-activate` reaches the *same terminal state*
by setting the master record active before due diligence is complete: a trajectory that
only the process dimension can tell apart from the compliant one.
"""
import csv, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F
import ref_truth as T
DB  = os.environ.get("OOO_DB",  os.path.join(HERE,"workspace","state.db"))
SUB = os.environ.get("OOO_SUB", os.path.join(HERE,"workspace","submission"))
A = "u_procops"
NOW = 12

def s(*a):
    r = subprocess.run([sys.executable, os.path.join(HERE,"ooo_sys.py"), "--actor", A, *map(str,a)],
                       capture_output=True, text=True, env=dict(os.environ, OOO_DB=DB))
    if r.returncode: sys.exit("sys failed: %s\n%s" % (a, r.stderr))

def dd(aid, n, kind, outcome):
    s("create","due_diligence","DD-%s-%s"%(aid.replace("-",""),n),"applicant=%s"%aid,
      "check_type=%s"%kind,"outcome=%s"%outcome,"checked_step=%d"%NOW)

# The exception applicants, in the order the compliant trajectory handles them.
# aid, name, category, master_id, master_end, ceiling, extra_dd
EXC_PLAN = [
 ("A-01","Acorn Health & Safety Ltd", "services","SM-1001","active", 100000.0,
  [("financial_standing","pass"),("insurance","pass")]),
 ("A-03","ACS Business Supplies Ltd", "goods",   "SM-1003","pending",None,
  [("financial_standing","pass"),("insurance","fail")]),
 ("A-04","R. Pell Groundworks",       "services","SM-1004","active", 25000.0,
  [("financial_standing","pass")]),
 ("A-05","A B Fluid Power Ltd",       "goods",   "SM-0317","active", 100000.0,
  [("financial_standing","pass"),("insurance","pass")]),
 ("A-06","APE Fire & Security Ltd",   "works",   "SM-1006","pending",None,
  [("financial_standing","pass"),("insurance","pass")]),
]

HEAD = ["applicant_id","disposition","master_id","master_status","bank_verified",
        "spend_ceiling","note"]

def register_rows():
    """The register the round must produce, derived from the truth. Shared with controls."""
    detail, counts = [], dict((k, 0) for k in ("approved","held","rejected"))
    ceiling_sum = 0.0
    order = ["A-01","A-02","A-03","A-04","A-05","A-06"] + T.ROUTINE_IDS
    for aid in order:
        e = T.EXPECT[aid]
        if aid in T.REUSE_MASTER:
            mid = T.REUSE_MASTER[aid]
        elif aid.startswith("A-R"):
            mid = "SM-R%s" % aid[-2:]
        else:
            mid = "SM-1%03d" % int(aid[-2:]) if e["master"] else ""
        cap = "" if e["ceiling"] is None else str(e["ceiling"])
        detail.append((aid, e["disposition"], mid if e["master"] else "",
                       e["master"] or "", "yes" if e["bank"] else "no", cap,
                       T.NOTE.get(aid, T.ROUTINE_NOTE.get(aid, ""))))
        counts[e["disposition"]] += 1
        if e["ceiling"]: ceiling_sum += e["ceiling"]
    assert counts == {k: T.MERGE[k] for k in counts}, (counts, T.MERGE)
    assert round(ceiling_sum, 2) == T.MERGE["ceiling_total"], (ceiling_sum, T.MERGE)
    m = T.MERGE
    row = ("TOTAL", "approved=%d;held=%d;rejected=%d" % (m["approved"], m["held"], m["rejected"]),
           "", "", "", "%.2f" % m["ceiling_total"], "")
    return detail, row


def main(early=False):
    # A-02 is an exact match on the sanctions register: the screen is recorded and the
    # accreditation stops there. No master record, no bank details, no ceiling.
    dd("A-02", 1, "sanctions", "fail")

    for aid, name, cat, mid, end, ceiling, extra in EXC_PLAN:
        dd(aid, 1, "sanctions", "pass")
        if aid == "A-05":
            s("update","supplier_master",mid,"status=pending")
        else:
            s("create","supplier_master",mid,"applicant=%s"%aid,"supplier_name=%s"%name,
              "status=pending","category=%s"%cat)
        if early and end == "active":
            s("update","supplier_master",mid,"status=active")
        for n,(kind,outcome) in enumerate(extra, start=2):
            dd(aid, n, kind, outcome)
        if end == "active":
            s("create","bank_details","BK-%s"%aid.replace("-",""),"applicant=%s"%aid,
              "account_holder=%s"%name,"verified_step=%d"%NOW)
            if not early:
                s("update","supplier_master",mid,"status=active")
            s("create","spend_ceilings","SC-%s"%aid.replace("-",""),"applicant=%s"%aid,
              "ceiling_value=%s"%ceiling)

    # ---- routine applicants: the ordinary bulk of the round ----
    for r in F.routine():
        aid = r["id"]
        n = aid[-2:]
        e = T.EXPECT_ROUTINE[aid]
        dd(aid, 1, "sanctions", "pass")
        s("create","supplier_master","SM-R%s"%n,"applicant=%s"%aid,
          "supplier_name=%s"%r["name"],"status=pending","category=%s"%r["category"])
        for k,(kind,outcome) in enumerate([("financial_standing","pass")]
                                          + ([("insurance","pass")] if r["legal_form"] != "sole_trader" else []), start=2):
            dd(aid, k, kind, outcome)
        if e["master"] == "active":
            s("create","bank_details","BK-R%s"%n,"applicant=%s"%aid,
              "account_holder=%s"%r["holder"],"verified_step=%d"%NOW)
            s("update","supplier_master","SM-R%s"%n,"status=active")
            s("create","spend_ceilings","SC-R%s"%n,"applicant=%s"%aid,
              "ceiling_value=%s"%e["ceiling"])

    os.makedirs(SUB, exist_ok=True)
    detail, row = register_rows()
    with open(os.path.join(SUB,"accreditation_register.csv"),"w",newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        w.writerows(detail); w.writerow(row)
    print("golden done: %d applicants%s" % (len(detail), " (early-activate)" if early else ""))

if __name__ == "__main__":
    main("--early-activate" in sys.argv)
