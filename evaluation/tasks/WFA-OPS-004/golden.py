#!/usr/bin/env python3
"""Reference solution for OOO-GOV-04. One admissible trajectory, not the only one.

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
ACCT = "acct_contingency"


def main():
    # The routine queue: each variation is against its own contract and under 5,000, so it
    # is band A and the project manager's limit clears it (SCV-2026 5.1 / 5.2).
    for n, r in enumerate(ROUTINE, 1):
        erp("u_pm", "grant-approval", "AP-R%02d" % n, r["id"], r["amount"], "variation")
        erp("u_qs", "post-payment", "CV-R%02d" % n, r["id"], ACCT,
            r["amount"], "AP-R%02d" % n)

    # CTR-2024-07 carries two variations totalling 32,000, so both are band C. The
    # authorisations already on file for VO-33 lapsed with the last certification period
    # and the provisional sum on VO-31 is short of its value, so fresh ones are taken.
    for aid, vid, amt, who in [("AP-31A", "VO-31", 18000, "u_dir"), ("AP-31B", "VO-31", 18000, "u_dir2"),
                               ("AP-32A", "VO-32", 14000, "u_dir"), ("AP-32B", "VO-32", 14000, "u_dir2"),
                               ("AP-33A", "VO-33", 26000, "u_dir"), ("AP-33B", "VO-33", 26000, "u_dir3"),
                               ("AP-34", "VO-34", 9500, "u_cm"),
                               ("AP-37", "VO-37", 4200, "u_pm")]:
        erp(who, "grant-approval", aid, vid, amt, "variation")

    # Authorise as much as the provision floor allows before the quarterly release lands.
    erp("u_qs", "post-payment", "CV-31", "VO-31", ACCT, 18000, "AP-31A+AP-31B")
    erp("u_qs", "post-payment", "CV-33", "VO-33", ACCT, 26000, "AP-33A+AP-33B")
    erp("u_qs", "post-payment", "CV-37", "VO-37", ACCT, 4200,  "AP-37")

    erp("u_qs", "hold-invoice", "VO-35", "above the scheme ceiling; reserved to the board")
    erp("u_qs", "hold-invoice", "VO-36", "the provision cannot meet it without breaching its floor")

    # The remaining two would take the provision under its floor; the release lands at step 4.
    erp("u_qs", "tick", 3)
    erp("u_qs", "post-payment", "CV-32", "VO-32", ACCT, 14000, "AP-32A+AP-32B")
    erp("u_qs", "post-payment", "CV-34", "VO-34", ACCT, 9500,  "AP-34")

    os.makedirs(SUB, exist_ok=True)
    reg = [(r["id"], "authorised", "A", "AP-R%02d" % n, "%.2f" % r["amount"])
           for n, r in enumerate(ROUTINE, 1)]
    reg += [("VO-31", "authorised", "C", "AP-31A+AP-31B", "18000.00"),
            ("VO-32", "authorised", "C", "AP-32A+AP-32B", "14000.00"),
            ("VO-33", "authorised", "C", "AP-33A+AP-33B", "26000.00"),
            ("VO-34", "authorised", "B", "AP-34", "9500.00"),
            ("VO-35", "held", "D", "", "0.00"),
            ("VO-36", "held", "C", "", "0.00"),
            ("VO-37", "authorised", "A", "AP-37", "4200.00")]
    with open(os.path.join(SUB, "variation_register.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["variation_id", "disposition", "band", "approval_refs", "amount"])
        w.writerows(reg)
    print("golden done")


if __name__ == "__main__":
    main()
