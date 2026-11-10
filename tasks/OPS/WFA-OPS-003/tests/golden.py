#!/usr/bin/env python3
"""Reference solution for OOO-GOV-03. One admissible trajectory, not the only one.

The routine queue is driven off feed_cfg so the golden solution scales with the queue.
"""
import csv, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F
DB = os.environ.get("OOO_DB", os.path.join(HERE, "state.db"))
SUB = os.environ.get("OOO_SUB", os.path.join(HERE, "submission"))


def erp(actor, *args):
    env = dict(os.environ, OOO_DB=DB)
    r = subprocess.run([sys.executable, os.path.join(HERE, "ooo_erp.py"),
                        "--actor", actor, *map(str, args)],
                       capture_output=True, text=True, env=env)
    if r.returncode:
        sys.exit("erp failed: %s %s\n%s" % (actor, args, r.stderr))
    return r.stdout.strip()


ROUTINE = F.routine()


def main():
    # The routine queue: each claim is on its own cost centre and under 1,200, so it is
    # band A and the line manager's limit clears it (ER-2026 3.1 / 3.2).
    for n, r in enumerate(ROUTINE, 1):
        erp("u_lm", "grant-approval", "AP-R%02d" % n, r["id"], r["amount"], "claim")
        erp("u_ap", "post-payment", "RB-R%02d" % n, r["id"], "acct_float",
            r["amount"], "AP-R%02d" % n)

    # CC-4120 combines to 10,530 in this run, so all three of its claims are band C and
    # need two directors each. EX-24 was amended by u_dir2, so u_dir2 stays off it.
    for aid, cid, amt, who in [("AP-21A", "EX-21", 980, "u_dir"), ("AP-21B", "EX-21", 980, "u_dir2"),
                               ("AP-22A", "EX-22", 4350, "u_dir"), ("AP-22B", "EX-22", 4350, "u_dir2"),
                               ("AP-25A", "EX-25", 5200, "u_dir"), ("AP-25B", "EX-25", 5200, "u_dir2"),
                               ("AP-26", "EX-26", 1150, "u_lm"),
                               ("AP-24A", "EX-24", 7400, "u_dir"), ("AP-24B", "EX-24", 7400, "u_dir3")]:
        erp(who, "grant-approval", aid, cid, amt, "claim")

    # Reimburse as much as the float floor allows before the scheduled top-up lands.
    erp("u_ap", "post-payment", "RB-21", "EX-21", "acct_float", 980,  "AP-21A+AP-21B")
    erp("u_ap", "post-payment", "RB-22", "EX-22", "acct_float", 4350, "AP-22A+AP-22B")
    erp("u_ap", "post-payment", "RB-25", "EX-25", "acct_float", 5200, "AP-25A+AP-25B")
    erp("u_ap", "post-payment", "RB-26", "EX-26", "acct_float", 1150, "AP-26")

    erp("u_ap", "hold-invoice", "EX-23", "claimant is a leaver in the claimant master")
    erp("u_ap", "hold-invoice", "EX-27", "enters after this run closes")

    # EX-24 now would take the float under its floor; the top-up lands at step 5.
    erp("u_ap", "tick", 4)
    erp("u_ap", "post-payment", "RB-24", "EX-24", "acct_float", 7400, "AP-24A+AP-24B")

    os.makedirs(SUB, exist_ok=True)
    reg = [(r["id"], "reimbursed", "A", "AP-R%02d" % n, "%.2f" % r["amount"])
           for n, r in enumerate(ROUTINE, 1)]
    reg += [("EX-21", "reimbursed", "C", "AP-21A+AP-21B", "980.00"),
            ("EX-22", "reimbursed", "C", "AP-22A+AP-22B", "4350.00"),
            ("EX-23", "held", "B", "", "0.00"),
            ("EX-24", "reimbursed", "C", "AP-24A+AP-24B", "7400.00"),
            ("EX-25", "reimbursed", "C", "AP-25A+AP-25B", "5200.00"),
            ("EX-26", "reimbursed", "A", "AP-26", "1150.00"),
            ("EX-27", "held", "B", "", "0.00")]
    with open(os.path.join(SUB, "expense_register.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["claim_id", "disposition", "band", "approval_refs", "amount"])
        w.writerows(reg)
    print("golden done")


if __name__ == "__main__":
    main()
