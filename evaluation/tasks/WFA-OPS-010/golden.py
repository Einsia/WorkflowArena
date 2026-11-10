#!/usr/bin/env python3
"""Reference solution for OOO-OPS-05. One admissible trajectory; the register is derived
from the truth so it scales with the queue."""
import csv, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F
import ref_truth as T
DB  = os.environ.get("OOO_DB",  os.path.join(HERE, "workspace", "state.db"))
SUB = os.environ.get("OOO_SUB", os.path.join(HERE, "workspace", "submission"))
A = "u_complaints"

HEADER = ["complaint_id", "account_id", "disposition", "case_ref", "queue",
          "sla_due_step", "referral_scheme", "compensation"]

def s(*a):
    r = subprocess.run([sys.executable, os.path.join(HERE, "ooo_sys.py"), "--actor", A, *map(str, a)],
                       capture_output=True, text=True, env=dict(os.environ, OOO_DB=DB))
    if r.returncode: sys.exit("sys failed: %s\n%s" % (a, r.stderr))

def case_id_for(cid):
    return "CS-1%s" % cid[-3:] if cid.startswith("C-") and not cid.startswith("C-R") \
        else "CS-1%s" % cid[-2:]

def write_report(sub, rows):
    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(sub, "routing_report.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(HEADER); w.writerows(rows)

def main():
    rows = []
    # ---- C-01 Aurora Orchard Manor is not in the customer master: nothing is provisioned.
    # ---- C-04 arrived at step 21, outside the in-time window: nothing is provisioned.
    for cid in ("C-01", "C-04"):
        e = T.EXPECT[cid]
        rows.append((cid, e["account"], e["disp"], "", "", "", "", "0"))

    # ---- C-02 restates the open billing case CS-0310: attach, do not open a second case.
    s("update", "cases", "CS-0310", "complaints=C-0188;C-02")
    rows.append(("C-02", "A-002", "attached", "CS-0310", "extended", "44", "", "0"))

    # ---- C-03 tier 1, vulnerability marker, regulated_care: priority queue + referral.
    s("create", "cases", "CS-1003", "account=A-003", "subject=service_failure",
      "status=open", "complaints=C-03", "opened_step=38")
    s("create", "sla_clocks", "SLA-1003", "case_ref=CS-1003", "queue=priority", "due_step=40")
    s("create", "regulatory_referrals", "RR-1003", "case_ref=CS-1003", "account=A-003",
      "scheme=care_standards")
    rows.append(("C-03", "A-003", "opened", "CS-1003", "priority", "40", "care_standards", "0"))

    # ---- C-05 the only prior case for this account and subject is closed: open a new one.
    s("create", "cases", "CS-1005", "account=A-005", "subject=access_dispute",
      "status=open", "complaints=C-05", "opened_step=38")
    s("create", "sla_clocks", "SLA-1005", "case_ref=CS-1005", "queue=standard", "due_step=46")
    rows.append(("C-05", "A-005", "opened", "CS-1005", "standard", "46", "", "0"))

    # ---- C-06 service_failure on a managed contract, tier 2: goodwill of 250.
    s("create", "cases", "CS-1006", "account=A-006", "subject=service_failure",
      "status=open", "complaints=C-06", "opened_step=38")
    s("create", "sla_clocks", "SLA-1006", "case_ref=CS-1006", "queue=standard", "due_step=47")
    s("create", "compensation_payments", "CP-1006", "account=A-006", "case_ref=CS-1006",
      "amount=250")
    rows.append(("C-06", "A-006", "opened", "CS-1006", "standard", "47", "", "250"))

    # ---- routine complaints: the ordinary bulk, each handled under the same rules ----
    for r in T.ROUTINE:
        cid = r["id"]; e = T.EXPECT_ROUTINE[cid]
        if r["attach_to"]:
            # restates an open case: attach, do not open a second one
            s("update", "cases", r["attach_to"], "complaints=C-RX%02d;%s" % (int(cid[-2:]), cid))
            rows.append((cid, e["account"], "attached", r["attach_to"], e["queue"],
                         e["due"], e["scheme"] or "", str(e["comp"])))
            continue
        cs = "CS-R%02d" % int(cid[-2:])
        s("create", "cases", cs, "account=%s" % e["account"], "subject=%s" % e["subject"],
          "status=open", "complaints=%s" % cid, "opened_step=38")
        s("create", "sla_clocks", "SLA-R%02d" % int(cid[-2:]), "case_ref=%s" % cs,
          "queue=%s" % e["queue"], "due_step=%s" % e["due"])
        if e["scheme"]:
            s("create", "regulatory_referrals", "RR-R%02d" % int(cid[-2:]), "case_ref=%s" % cs,
              "account=%s" % e["account"], "scheme=%s" % e["scheme"])
        if e["comp"]:
            s("create", "compensation_payments", "CP-R%02d" % int(cid[-2:]), "account=%s" % e["account"],
              "case_ref=%s" % cs, "amount=%s" % e["comp"])
        rows.append((cid, e["account"], "opened", cs, e["queue"], e["due"],
                     e["scheme"] or "", str(e["comp"])))

    rows.append(("TOTAL", str(T.ACTIONED), "total", str(T.NEW_CASES), "", "",
                 str(T.REFERRALS), str(T.COMP_TOTAL)))
    write_report(SUB, rows)
    print("golden done: %d complaints" % (len(rows) - 1))

if __name__ == "__main__": main()
