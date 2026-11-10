#!/usr/bin/env python3
"""Reference solution for OOO-GOV-07. One admissible trajectory, not the only one.

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
ACCT = "acct_assetbase"


def main():
    # The routine queue: each disposal is to a distinct buyer under 10,000, so it is band A
    # and the asset manager's limit clears it. No auction route applies below band C
    # (ADP-2026 7.1 / 7.2 / 7.3).
    for n, r in enumerate(ROUTINE, 1):
        erp("u_am", "grant-approval", "AP-R%02d" % n, r["id"], r["amount"], "disposal")
        erp("u_est", "post-payment", "DS-R%02d" % n, r["id"], ACCT,
            r["amount"], "AP-R%02d" % n)

    # Yorwaste takes 38,000 and 52,000 in this programme, so both of its lots are band C:
    # two directors each, and open auction rather than private treaty. AD-63 was revalued
    # by the valuation officer, so the asset manager approves it instead.
    for aid, did, amt, who, scope in [
            ("AP-61A", "AD-61", 38000, "u_dir",  "auction"),
            ("AP-61B", "AD-61", 38000, "u_dir2", "auction"),
            ("AP-62A", "AD-62", 52000, "u_dir",  "auction"),
            ("AP-62B", "AD-62", 52000, "u_dir3", "auction"),
            ("AP-63",  "AD-63", 9000,  "u_am",   "disposal"),
            ("AP-64",  "AD-64", 14000, "u_am",   "disposal"),
            ("AP-65",  "AD-65", 22000, "u_am",   "disposal")]:
        erp(who, "grant-approval", aid, did, amt, scope)

    # Write down as much as the asset base floor allows before the revaluation is certified.
    erp("u_est", "post-payment", "DS-62", "AD-62", ACCT, 52000, "AP-62A+AP-62B")
    erp("u_est", "post-payment", "DS-61", "AD-61", ACCT, 38000, "AP-61A+AP-61B")
    erp("u_est", "post-payment", "DS-64", "AD-64", ACCT, 14000, "AP-64")
    erp("u_est", "post-payment", "DS-63", "AD-63", ACCT, 9000,  "AP-63")

    erp("u_est", "hold-invoice", "AD-66", "buyer barred in the buyer register")
    erp("u_est", "hold-invoice", "AD-67", "still inside its minimum retention period")

    # AD-65 now would take the asset base under its floor; the revaluation lands at step 5.
    erp("u_est", "tick", 4)
    erp("u_est", "post-payment", "DS-65", "AD-65", ACCT, 22000, "AP-65")

    os.makedirs(SUB, exist_ok=True)
    reg = [(r["id"], "disposed", "A", "AP-R%02d" % n, "%.2f" % r["amount"])
           for n, r in enumerate(ROUTINE, 1)]
    reg += [("AD-61", "disposed", "C", "AP-61A+AP-61B", "38000.00"),
            ("AD-62", "disposed", "C", "AP-62A+AP-62B", "52000.00"),
            ("AD-63", "disposed", "A", "AP-63", "9000.00"),
            ("AD-64", "disposed", "B", "AP-64", "14000.00"),
            ("AD-65", "disposed", "B", "AP-65", "22000.00"),
            ("AD-66", "held", "C", "", "0.00"),
            ("AD-67", "held", "B", "", "0.00")]
    with open(os.path.join(SUB, "disposal_register.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["asset_id", "disposition", "band", "approval_refs", "amount"])
        w.writerows(reg)
    print("golden done")


if __name__ == "__main__":
    main()
