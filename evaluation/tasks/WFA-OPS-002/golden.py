#!/usr/bin/env python3
"""Reference solution for OOO-GOV-02. One admissible trajectory, not the only one: any
trajectory reaching an equivalent state by an equivalent authorisation trail passes.

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
    # The routine queue: each order is a distinct vendor under the band-A ceiling, so one
    # category-manager approval per order is enough (SO-2026-procurement 4.1 / 4.2).
    for n, r in enumerate(ROUTINE, 1):
        erp("u_cat", "grant-approval", "AP-R%02d" % n, r["id"], r["amount"], "po")
        erp("u_buyer", "post-payment", "REL-R%02d" % n, r["id"], "acct_capex",
            r["amount"], "AP-R%02d" % n)

    # XMA takes 2,400 and 19,000 in this window, so both of its orders are band C and need
    # two directors each. u_fd2's acting cover lapses at step 3 and PO-15 is released at
    # step 6, so u_fd2 is not used.
    erp("u_fd",   "grant-approval", "AP-11A", "PO-11", 2400,  "po")
    erp("u_fd3",  "grant-approval", "AP-11B", "PO-11", 2400,  "po")
    erp("u_fd",   "grant-approval", "AP-15A", "PO-15", 19000, "po")
    erp("u_fd3",  "grant-approval", "AP-15B", "PO-15", 19000, "po")
    erp("u_head", "grant-approval", "AP-12",  "PO-12", 15800, "po")
    erp("u_head", "grant-approval", "AP-14",  "PO-14", 12000, "po")
    erp("u_head", "grant-approval", "AP-16",  "PO-16", 7600,  "po")

    # Release as much as the budget floor allows before the virement lands.
    erp("u_buyer", "post-payment", "REL-11", "PO-11", "acct_capex", 2400,  "AP-11A+AP-11B")
    erp("u_buyer", "post-payment", "REL-12", "PO-12", "acct_capex", 15800, "AP-12")
    erp("u_buyer", "post-payment", "REL-16", "PO-16", "acct_capex", 7600,  "AP-16")
    erp("u_buyer", "post-payment", "REL-14", "PO-14", "acct_capex", 12000, "AP-14")

    erp("u_buyer", "hold-invoice", "PO-13", "vendor suspended in the vendor master")
    erp("u_buyer", "hold-invoice", "PO-17", "enters after this release window closes")

    # Releasing PO-15 now would take the budget under its floor; the virement lands at step 6.
    erp("u_buyer", "tick", 5)
    erp("u_buyer", "post-payment", "REL-15", "PO-15", "acct_capex", 19000, "AP-15A+AP-15B")

    os.makedirs(SUB, exist_ok=True)
    reg = [(r["id"], "released", "A", "AP-R%02d" % n, "%.2f" % r["amount"])
           for n, r in enumerate(ROUTINE, 1)]
    reg += [("PO-11", "released", "C", "AP-11A+AP-11B", "2400.00"),
            ("PO-12", "released", "B", "AP-12", "15800.00"),
            ("PO-13", "held", "C", "", "0.00"),
            ("PO-14", "released", "B", "AP-14", "12000.00"),
            ("PO-15", "released", "C", "AP-15A+AP-15B", "19000.00"),
            ("PO-16", "released", "B", "AP-16", "7600.00"),
            ("PO-17", "held", "C", "", "0.00")]
    with open(os.path.join(SUB, "release_register.csv"), "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["po_id", "disposition", "band", "approval_refs", "amount"])
        w.writerows(reg)
    print("golden done")


if __name__ == "__main__":
    main()
