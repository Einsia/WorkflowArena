#!/usr/bin/env python3
"""Reference solution for OOO-OPS-06. One admissible trajectory; the register is derived
from the truth so it scales with the queue."""
import csv, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F
import ref_truth as T
DB  = os.environ.get("OOO_DB",  os.path.join(HERE, "workspace", "state.db"))
SUB = os.environ.get("OOO_SUB", os.path.join(HERE, "workspace", "submission"))
A = "u_commercial"

HEADER = ["contract_id", "disposition", "annual_value", "signatory", "opportunity_stage"]

# The exception contracts, in the order the compliant trajectory handles them.
EXC_ORDER = ["K-01", "K-02", "K-03", "K-05", "K-06"]

def s(*a):
    r = subprocess.run([sys.executable, os.path.join(HERE, "ooo_sys.py"), "--actor", A, *map(str, a)],
                       capture_output=True, text=True, env=dict(os.environ, OOO_DB=DB))
    if r.returncode: sys.exit("sys failed: %s\n%s" % (a, r.stderr))

def write_report(sub, rows):
    os.makedirs(sub, exist_ok=True)
    with open(os.path.join(sub, "renewal_report.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(HEADER); w.writerows(rows)

def fmt(v):
    return "" if v is None else ("%d" % v if float(v).is_integer() else "%s" % v)

def main():
    rows = []
    # ---- K-01 CPIH 2028 is 1.0450 -> 125,400. The 2028 review is cleared (the 2027 one is
    # not the review that governs). 125,400 is inside S-LOW's limit. ----
    # ---- K-02 indexed to 508,915, over the re-tender threshold: back to the market. ----
    # ---- K-03 the 2028 review is unresolved: the opportunity is prepared and held. ----
    # ---- K-05 the counterparty has served notice: the contract lapses. ----
    # ---- K-06 ENERGY 2028 is 1.0800 -> 154,440, which crosses out of S-LOW's band. ----
    for n, kid in enumerate(EXC_ORDER, 1):
        e = T.EXPECT_EXC[kid]
        cp = next(c[1] for c in F.EXCEPTIONS if c[0] == kid)
        s("create", "crm_opportunities", "OPP-10%02d" % n, "contract=%s" % kid,
          "counterparty=%s" % cp, "stage=%s" % e["stage"], "value=%s" % fmt(e["value"]))
        if e["schedule"]:
            s("create", "finance_schedules", "FS-10%02d" % n, "contract=%s" % kid,
              "annual_value=%s" % fmt(e["value"]), "start_step=%d" % T.START_STEP,
              "signatory=%s" % e["signatory"])
    # K-04 is already renewed through 2028: nothing to do and nothing to touch.

    # ---- routine contracts: ordinary renewals, each an opportunity then a schedule ----
    for i, r in enumerate(T.ROUTINE, 1):
        e = T.EXPECT_ROUTINE[r["id"]]
        s("create", "crm_opportunities", "OPP-R%02d" % i, "contract=%s" % r["id"],
          "counterparty=%s" % r["counterparty"], "stage=closed_won",
          "value=%s" % fmt(e["value"]))
        s("create", "finance_schedules", "FS-R%02d" % i, "contract=%s" % r["id"],
          "annual_value=%s" % fmt(e["value"]), "start_step=%d" % T.START_STEP,
          "signatory=%s" % e["signatory"])

    order = ["K-01", "K-02", "K-03", "K-04", "K-05", "K-06"] + T.ROUTINE_IDS
    for kid in order:
        e = T.EXPECT[kid]
        rows.append((kid, e["disp"], fmt(e["value"]), e["signatory"], e["stage"] or ""))

    renewed = [e for e in T.EXPECT.values() if e["disp"] == "renewed"]
    total_value = sum(e["value"] for e in renewed)
    rows.append(("TOTAL", str(len(renewed)), fmt(total_value),
                 str(len(T.EXPECT) - len(renewed)), ""))
    assert len(renewed) == T.RENEWED and round(total_value, 2) == T.RENEWED_VALUE

    write_report(SUB, rows)
    print("golden done: %d contracts" % (len(rows) - 1))


if __name__ == "__main__": main()
