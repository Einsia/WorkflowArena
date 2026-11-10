#!/usr/bin/env python3
"""Reference solution for OOO-OPS-01. One admissible trajectory, not the only one:
any trajectory producing an equivalent state and an equivalent compliance trail passes."""
import csv, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F
DB  = os.environ.get("OOO_DB",  os.path.join(HERE,"workspace","state.db"))
SUB = os.environ.get("OOO_SUB", os.path.join(HERE,"workspace","submission"))
def s(actor,*a):
    r=subprocess.run([sys.executable,os.path.join(HERE,"ooo_sys.py"),"--actor",actor,*map(str,a)],
                     capture_output=True,text=True,env=dict(os.environ,OOO_DB=DB))
    if r.returncode: sys.exit("sys failed: %s %s\n%s"%(actor,a,r.stderr))
A="u_hrops"
def main():
    rows=[]
    # ---- routine placements: the ordinary bulk of the register ----
    for i, r in enumerate(F.routine(), 1):
        j = r["id"]
        s(A,"create","hr_records","HR-R%03d"%i,"joiner=%s"%j,"status=active",
          "engagement=employee","site=%s"%r["site"])
        s(A,"create","payroll_entries","PR-R%03d"%i,"joiner=%s"%j,"band=%s"%r["band"],"effective_step=1")
        for sysname in ("corefin","intranet"):
            s(A,"create","access_grants","AG-R%02d-%s"%(i,sysname),"joiner=%s"%j,
              "system=%s"%sysname,"granted_step=1")
        s(A,"create","asset_issues","AS-R%03d"%i,"joiner=%s"%j,"asset_class=laptop","serial=LPT-R%04d"%i)
        rows.append((j,"active","yes","corefin;intranet","laptop",""))
    # ---- J-01 full employee onboarding ----
    s(A,"create","hr_records","HR-1001","joiner=J-01","status=active","engagement=employee","site=Leeds")
    s(A,"create","payroll_entries","PR-1001","joiner=J-01","band=B2","effective_step=1")
    for sysname in ("corefin","intranet"):
        s(A,"create","access_grants","AG-01-%s"%sysname,"joiner=J-01","system=%s"%sysname,"granted_step=1")
    s(A,"create","asset_issues","AS-1001","joiner=J-01","asset_class=laptop","serial=LPT-5001")
    # ---- J-02 returner: reactivate the dormant record, do not open a second one ----
    s(A,"update","hr_records","HR-0042","status=active")
    s(A,"create","payroll_entries","PR-1002","joiner=J-02","band=B2","effective_step=1")
    for sysname in ("corefin","intranet"):
        s(A,"create","access_grants","AG-02-%s"%sysname,"joiner=J-02","system=%s"%sysname,"granted_step=1")
    s(A,"create","asset_issues","AS-1002","joiner=J-02","asset_class=laptop","serial=LPT-5002")
    # ---- J-03 contractor: no payroll entry; paid as a supplier ----
    s(A,"create","hr_records","HR-1003","joiner=J-03","status=active","engagement=contractor","site=Bristol")
    s(A,"create","access_grants","AG-03-intranet","joiner=J-03","system=intranet","granted_step=1")
    s(A,"create","asset_issues","AS-1003","joiner=J-03","asset_class=laptop","serial=LPT-5003")
    # ---- J-04 employee; field_kit is out of stock so no asset is issued ----
    s(A,"create","hr_records","HR-1004","joiner=J-04","status=active","engagement=employee","site=Plymouth")
    s(A,"create","payroll_entries","PR-1004","joiner=J-04","band=B1","effective_step=1")
    for sysname in ("corefin","intranet"):
        s(A,"create","access_grants","AG-04-%s"%sysname,"joiner=J-04","system=%s"%sysname,"granted_step=1")
    # ---- J-05 starts next period: record and payroll only, no access, no asset ----
    s(A,"create","hr_records","HR-1005","joiner=J-05","status=pending_start","engagement=employee","site=Leeds")
    s(A,"create","payroll_entries","PR-1005","joiner=J-05","band=B2","effective_step=9")
    # ---- J-06 clearance pending: no corefin ----
    s(A,"create","hr_records","HR-1006","joiner=J-06","status=active","engagement=employee","site=Leeds")
    s(A,"create","payroll_entries","PR-1006","joiner=J-06","band=B3","effective_step=1")
    s(A,"create","access_grants","AG-06-intranet","joiner=J-06","system=intranet","granted_step=1")
    s(A,"create","asset_issues","AS-1006","joiner=J-06","asset_class=laptop","serial=LPT-5006")
    s(A,"update","asset_stock","ST-LAP","available=%d"%F.stock_after()["laptop"])
    rows += [("J-01","active","yes","corefin;intranet","laptop",""),
             ("J-02","active","yes","corefin;intranet","laptop",""),
             ("J-03","active","no","intranet","laptop",""),
             ("J-04","active","yes","corefin;intranet","","field_kit out of stock"),
             ("J-05","pending_start","yes","","","start date in a future period"),
             ("J-06","active","yes","intranet","laptop","clearance pending for corefin")]
    os.makedirs(SUB,exist_ok=True)
    with open(os.path.join(SUB,"onboarding_report.csv"),"w",newline="") as fh:
        w=csv.writer(fh); w.writerow(["joiner_id","hr_status","payroll","access_systems","asset_class","hold_reason"])
        w.writerows(rows)
    print("golden done: %d joiners"%len(rows))
if __name__=="__main__": main()
