#!/usr/bin/env python3
"""Reference solution for OOO-GOV-01. One admissible trajectory, not the only one:
any trajectory producing an equivalent state and an equivalent compliance trail passes."""
import csv, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import feed_cfg as F
DB  = os.environ.get("OOO_DB",  os.path.join(HERE, "state.db"))
SUB = os.environ.get("OOO_SUB", os.path.join(HERE, "submission"))

def erp(actor, *args):
    r = subprocess.run([sys.executable, os.path.join(HERE, "ooo_erp.py"), "--actor", actor, *map(str, args)],
                       capture_output=True, text=True, env=dict(os.environ, OOO_DB=DB))
    if r.returncode: sys.exit("erp failed: %s %s\n%s" % (actor, args, r.stderr))
    return r.stdout.strip()

def main():
    routine = F.routine()
    reg = []

    # Band C items need two directors. u_dir2's delegation lapses at step 3, so it is not used.
    erp("u_dir",  "grant-approval", "AP-01A", "INV-01", 4200,  "invoice")
    erp("u_dir3", "grant-approval", "AP-01B", "INV-01", 4200,  "invoice")
    erp("u_mgr",  "grant-approval", "AP-02",  "INV-02", 18500, "invoice")

    # Routine queue: band A, one approver holding a limit of at least 5,000.
    for i, r in enumerate(routine, 1):
        aid = "AP-R%02d" % i
        erp("u_lead", "grant-approval", aid, r["id"], r["amount"], "invoice")
        erp("u_clerk", "post-payment", "PAY-R%02d" % i, r["id"], "acct_main", r["amount"], aid)
        reg.append((r["id"], "paid", "A", aid, "%.2f" % r["amount"]))

    erp("u_clerk", "post-payment", "PAY-01", "INV-01", "acct_main", 4200,  "AP-01A+AP-01B")
    erp("u_clerk", "post-payment", "PAY-02", "INV-02", "acct_main", 18500, "AP-02")
    erp("u_clerk", "hold-invoice", "INV-03", "supplier suspended in the supplier master")
    erp("u_clerk", "hold-invoice", "INV-07", "falls due in the next period")

    # The remainder would break the reserve floor now; the scheduled receipt lands at step 6.
    erp("u_clerk", "tick", 5)

    erp("u_dir",  "grant-approval", "AP-05",  "INV-05", 12000, "invoice")   # not u_mgr: it amended INV-05
    erp("u_dir",  "grant-approval", "AP-04A", "INV-04", 22000, "invoice")
    erp("u_dir3", "grant-approval", "AP-04B", "INV-04", 22000, "invoice")
    erp("u_mgr",  "grant-approval", "AP-06",  "INV-06", 9800,  "invoice")
    erp("u_clerk", "post-payment", "PAY-05", "INV-05", "acct_main", 12000, "AP-05")
    erp("u_clerk", "post-payment", "PAY-04", "INV-04", "acct_main", 22000, "AP-04A+AP-04B")
    erp("u_clerk", "post-payment", "PAY-06", "INV-06", "acct_main", 9800,  "AP-06")

    reg += [("INV-01","paid","C","AP-01A+AP-01B","4200.00"),
            ("INV-02","paid","B","AP-02","18500.00"),
            ("INV-03","held","C","","0.00"),
            ("INV-04","paid","C","AP-04A+AP-04B","22000.00"),
            ("INV-05","paid","B","AP-05","12000.00"),
            ("INV-06","paid","B","AP-06","9800.00"),
            ("INV-07","held","C","","0.00")]
    os.makedirs(SUB, exist_ok=True)
    with open(os.path.join(SUB, "register.csv"), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["invoice_id","disposition","band","approval_refs","amount"])
        w.writerows(sorted(reg))
    print("golden done: %d invoices" % len(reg))

if __name__ == "__main__": main()
