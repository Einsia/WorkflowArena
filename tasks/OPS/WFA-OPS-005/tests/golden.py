#!/usr/bin/env python3
"""Reference solution for OOO-GOV-05. One admissible trajectory, not the only one.

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
    # The routine queue: each instalment is to a distinct grantee on the restricted stream
    # and under 10,000, so it is band A, the programme manager clears it, and it is met
    # from the restricted fund (GC-2026 6.1 / 6.2 / 6.4).
    for n, r in enumerate(ROUTINE, 1):
        erp("u_prog", "grant-approval", "AP-R%02d" % n, r["id"], r["amount"], "instalment")
        erp("u_gm", "post-payment", "DB-R%02d" % n, r["id"], "acct_rgf",
            r["amount"], "AP-R%02d" % n)

    # G-LEIC takes 22,000 and 9,000 in this window, so both of its instalments are band C.
    # The block records against the restricted programme do not disburse GI-45, so it takes
    # two instalment-level authorisations of its own.
    for aid, gid, amt, who in [("AP-41A", "GI-41", 45000, "u_dir"), ("AP-41B", "GI-41", 45000, "u_dir2"),
                               ("AP-42", "GI-42", 28000, "u_head"),
                               ("AP-44A", "GI-44", 22000, "u_dir"), ("AP-44B", "GI-44", 22000, "u_dir3"),
                               ("AP-45A", "GI-45", 60000, "u_dir"), ("AP-45B", "GI-45", 60000, "u_dir2"),
                               ("AP-46A", "GI-46", 9000, "u_dir"), ("AP-46B", "GI-46", 9000, "u_dir3")]:
        erp(who, "grant-approval", aid, gid, amt, "instalment")

    # Core programme instalments come from the core fund, restricted ones from the
    # restricted fund; neither relieves the other.
    erp("u_gm", "post-payment", "DB-44", "GI-44", "acct_core", 22000, "AP-44A+AP-44B")
    erp("u_gm", "post-payment", "DB-46", "GI-46", "acct_core", 9000,  "AP-46A+AP-46B")

    # Disburse as much of the restricted stream as its floor allows before the tranche lands.
    erp("u_gm", "post-payment", "DB-41", "GI-41", "acct_rgf", 45000, "AP-41A+AP-41B")
    erp("u_gm", "post-payment", "DB-42", "GI-42", "acct_rgf", 28000, "AP-42")

    erp("u_gm", "hold-invoice", "GI-43", "grantee under investigation in the grantee master")
    erp("u_gm", "hold-invoice", "GI-47", "falls due in the next funding year")

    # The rest of the restricted stream would take the fund under its floor; the tranche
    # lands at step 5.
    erp("u_gm", "tick", 4)
    erp("u_gm", "post-payment", "DB-45", "GI-45", "acct_rgf", 60000, "AP-45A+AP-45B")

    os.makedirs(SUB, exist_ok=True)
    reg = [(r["id"], "disbursed", "A", "AP-R%02d" % n, "%.2f" % r["amount"])
           for n, r in enumerate(ROUTINE, 1)]
    reg += [("GI-41", "disbursed", "C", "AP-41A+AP-41B", "45000.00"),
            ("GI-42", "disbursed", "B", "AP-42", "28000.00"),
            ("GI-43", "held", "C", "", "0.00"),
            ("GI-44", "disbursed", "C", "AP-44A+AP-44B", "22000.00"),
            ("GI-45", "disbursed", "C", "AP-45A+AP-45B", "60000.00"),
            ("GI-46", "disbursed", "C", "AP-46A+AP-46B", "9000.00"),
            ("GI-47", "held", "B", "", "0.00")]
    with open(os.path.join(SUB, "disbursement_register.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["instalment_id", "disposition", "band", "approval_refs", "amount"])
        w.writerows(reg)
    print("golden done")


if __name__ == "__main__":
    main()
