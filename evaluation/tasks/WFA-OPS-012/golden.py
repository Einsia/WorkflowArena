#!/usr/bin/env python3
"""Reference solution for OOO-OPS-07. Replayable; the log is derived from the truth so it
scales with the queue."""
import csv, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F
import ref_truth as T
DB  = os.environ.get("OOO_DB",  os.path.join(HERE,"workspace","state.db"))
SUB = os.environ.get("OOO_SUB", os.path.join(HERE,"workspace","submission"))
A = "u_inforights"

HEAD = ["request_id","disposition","identity_outcome","records_considered",
        "records_released","records_withheld","withhold_grounds"]

def s(*a):
    r = subprocess.run([sys.executable, os.path.join(HERE,"ooo_sys.py"), "--actor", A, *map(str,a)],
                       capture_output=True, text=True, env=dict(os.environ, OOO_DB=DB))
    if r.returncode: sys.exit("sys failed: %s\n%s" % (a, r.stderr))
    return r.stdout

GROUND_NOTE = {
 "R-02": "identity not verified",
 "R-05": "not an access request",
 "R-06": "manifestly unfounded repeat request",
}

def main():
    s("show","dsar_requests"); s("show","records_index"); s("show","exemptions")
    rows = []

    def handle(rq, evidence, expect, note=""):
        """Verify identity, then release what the rules allow, then close the case."""
        tag = rq.replace("-", "")          # R-01 -> R01, R-R01 -> RR01: no collisions
        s("create","identity_checks","IDC-%s"%tag,"request=%s"%rq,
          "method=%s"%evidence,"outcome=%s"%expect["identity"],"checked_step=%d"%T_NOW)
        for n, rec in enumerate(expect["release"], 1):
            if rec in T.NEEDS_REDACTION:
                rid = "RD-%s-%d" % (tag, n)
                s("create","redaction_log",rid,"record=%s"%rec,
                  "redacted_fields=third_party_name;third_party_address","logged_step=%d"%T_NOW)
                s("create","disclosure_packs","DP-%s-%d"%(tag,n),"request=%s"%rq,
                  "record=%s"%rec,"released_step=%d"%T_NOW,"redaction_ref=%s"%rid)
            else:
                s("create","disclosure_packs","DP-%s-%d"%(tag,n),"request=%s"%rq,
                  "record=%s"%rec,"released_step=%d"%T_NOW)
        s("create","case_outcomes","CO-%s"%tag,"request=%s"%rq,
          "disposition=%s"%expect["disposition"],"closed_step=%d"%T_NOW)
        rows.append((rq, expect["disposition"], expect["identity"], expect["considered"],
                     len(expect["release"]), expect["considered"] - len(expect["release"]), note))

    T_NOW = T.NOW
    # ---- authored exceptions, each carrying its trap ----
    handle("R-01","passport+utility_bill", T.EXPECT_EXC["R-01"], "")
    handle("R-02","utility_bill", T.EXPECT_EXC["R-02"], GROUND_NOTE["R-02"])
    handle("R-03","driving_licence+bank_statement", T.EXPECT_EXC["R-03"],
           "legal privilege (EX-01)")
    handle("R-04","passport+tenancy_agreement", T.EXPECT_EXC["R-04"], "")
    handle("R-05","national_id_card+council_tax_bill", T.EXPECT_EXC["R-05"], GROUND_NOTE["R-05"])
    handle("R-06","driving_licence+utility_bill", T.EXPECT_EXC["R-06"], GROUND_NOTE["R-06"])

    # ---- routine requests ----
    for r in T.ROUTINE:
        rq = r["id"]; e = T.EXPECT_ROUTINE[rq]
        note = ""
        if e["disposition"] == "fulfilled_in_part":
            withheld = [x["id"] for x in T.ROUTINE_RECORDS
                        if x["subject"] == r["subject"] and x["id"] not in e["release"]]
            exs = [x for x in T.ROUTINE_EXEMPTIONS if x[1] in withheld and x[3] == "active"]
            note = ", ".join("%s (%s)" % (x[2].replace("_", " "), x[0]) for x in exs)
        handle(rq, r["id_evidence"], e, note)

    os.makedirs(SUB, exist_ok=True)
    rows.append(("TOTAL","","", T.TOTALS["considered"], T.TOTALS["released"],
                 T.TOTALS["withheld"], ""))
    with open(os.path.join(SUB,"dsar_log.csv"),"w",newline="") as fh:
        w = csv.writer(fh)
        w.writerow(HEAD)
        w.writerows(rows)
    print("golden done: %d requests" % (len(rows) - 1))

if __name__ == "__main__": main()
