#!/usr/bin/env python3
"""Reference solution for OOO-OPS-03. Replayable; no clock, no RNG."""
import csv, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F
import ref_truth as T
DB  = os.environ.get("OOO_DB",  os.path.join(HERE,"workspace","state.db"))
SUB = os.environ.get("OOO_SUB", os.path.join(HERE,"workspace","submission"))
A = "u_itops"

def s(actor,*a):
    r=subprocess.run([sys.executable,os.path.join(HERE,"ooo_sys.py"),"--actor",actor,*map(str,a)],
                     capture_output=True,text=True,env=dict(os.environ,OOO_DB=DB))
    if r.returncode: sys.exit("sys failed: %s %s\n%s"%(actor,a,r.stderr))

def main(late_handover=False):
    rows = []
    # ---- L-01 resignation, last day reached: full recovery. The lapsed delegation D-02 and
    # the already closed case C-02 are not live and are left alone. ----
    for g in ("AG-01","AG-02"): s(A,"update","access_grants",g,"status=revoked","revoked_step=1")
    s(A,"update","payroll_entries","PR-01","status=closed","close_step=1")
    s(A,"create","asset_returns","AR-1001","person=L-01","asset_class=laptop","serial=LPT-7001","received_step=1")
    rows.append(("L-01","revoked","closed","1","",""))

    # ---- L-02 last day is in a future period: nothing is withdrawn yet. ----
    rows.append(("L-02","retained","open","0","","last day falls in a future period"))
    # ---- L-03 is an internal transfer, not a leaver: nothing is withdrawn at all. ----
    rows.append(("L-03","retained","open","0","","internal transfer, not a leaver"))

    # ---- L-04 garden leave: access goes now, pay and assets run to the last day. ----
    for g in ("AG-07","AG-08"): s(A,"update","access_grants",g,"status=revoked","revoked_step=1")
    rows.append(("L-04","revoked","open","0","","garden leave: pay runs to the last day"))

    # ---- L-05 retirement, holds a live approval delegation: it passes to the line manager
    # before any access is removed. ----
    if late_handover:
        # the same terminal state, reached by taking the access away before the delegation
        # has moved: only the process dimension can tell this apart from the compliant order
        for g in ("AG-09","AG-10","AG-11"): s(A,"update","access_grants",g,"status=revoked","revoked_step=1")
        s(A,"update","delegations","D-01","status=reassigned","reassigned_to=M-Hollis")
    else:
        s(A,"update","delegations","D-01","status=reassigned","reassigned_to=M-Hollis")
        for g in ("AG-09","AG-10","AG-11"): s(A,"update","access_grants",g,"status=revoked","revoked_step=1")
    s(A,"update","payroll_entries","PR-05","status=closed","close_step=1")
    s(A,"create","asset_returns","AR-1005","person=L-05","asset_class=laptop","serial=LPT-7005","received_step=1")
    rows.append(("L-05","revoked","closed","1","D-01",""))

    # ---- L-06 contract end: the open case passes to the line manager first, then access
    # goes. No payroll entry exists for a contractor and none is opened. ----
    s(A,"update","open_cases","C-01","status=reassigned","reassigned_to=M-Okonjo")
    for g in ("AG-12","AG-13"): s(A,"update","access_grants",g,"status=revoked","revoked_step=1")
    s(A,"create","asset_returns","AR-1006","person=L-06","asset_class=field_kit","serial=FKT-3006","received_step=1")
    rows.append(("L-06","revoked","none","1","C-01",""))

    # ---- routine leavers: ordinary completed resignations ----
    for i, r in enumerate(T.ROUTINE, 1):
        p = r["id"]; case = "C-R%02d" % i
        # the live case leaves the person's hands before their access does
        s(A,"update","open_cases",case,"status=reassigned","reassigned_to=%s"%r["manager"])
        for sy in ("corefin","intranet"):
            s(A,"update","access_grants","AG-R%02d-%s"%(i,sy[:3]),"status=revoked","revoked_step=1")
        s(A,"update","payroll_entries","PR-R%02d"%i,"status=closed","close_step=1")
        s(A,"create","asset_returns","AR-R%02d"%i,"person=%s"%p,"asset_class=laptop",
          "serial=%s"%r["serial"],"received_step=1")
        rows.append((p,"revoked","closed","1",case,""))

    m = T.MERGE
    rows.append(("TOTAL", str(m["access_revoked"]), str(m["payroll_closed"]),
                 str(m["assets_returned"]), str(m["handovers"]), ""))
    os.makedirs(SUB,exist_ok=True)
    with open(os.path.join(SUB,"offboarding_report.csv"),"w",newline="") as fh:
        w=csv.writer(fh)
        w.writerow(["person_id","access_action","payroll_action","assets_returned",
                    "handover_ref","hold_reason"])
        w.writerows(rows)
    print("golden done: %d leavers" % (len(rows) - 1))

if __name__=="__main__": main("--late-handover" in sys.argv)
