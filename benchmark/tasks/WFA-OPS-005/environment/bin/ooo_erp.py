#!/usr/bin/env python3
"""OOO business system: SQLite state + append-only action log with before/after snapshots.

Every mutating command writes one action_log row capturing the full before/after of the
rows it touched, plus the episode step counter. The verifier replays that log to judge the
PROCESS dimension: a constraint must hold at every state change, not merely at the end.

Deterministic by construction: no wall clock, no RNG. "Now" is the episode step.
"""
from __future__ import annotations
import json, os, sqlite3, sys

DB = os.environ.get("OOO_DB", "/workspace/state.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS staff(
  id TEXT PRIMARY KEY, name TEXT, role TEXT,
  approve_limit REAL DEFAULT 0, delegation_expires_step INTEGER);
CREATE TABLE IF NOT EXISTS suppliers(
  id TEXT PRIMARY KEY, name TEXT, status TEXT DEFAULT 'active', bank_ref TEXT);
CREATE TABLE IF NOT EXISTS accounts(
  id TEXT PRIMARY KEY, name TEXT, balance REAL, reserve_floor REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS invoices(
  id TEXT PRIMARY KEY, supplier TEXT, amount REAL, contract_ref TEXT,
  status TEXT DEFAULT 'received', received_step INTEGER, last_edited_by TEXT);
CREATE TABLE IF NOT EXISTS approvals(
  id TEXT PRIMARY KEY, invoice TEXT, approver TEXT, covers_amount REAL,
  granted_step INTEGER, scope TEXT DEFAULT 'invoice', expires_step INTEGER);
CREATE TABLE IF NOT EXISTS payments(
  id TEXT PRIMARY KEY, invoice TEXT, account TEXT, amount REAL,
  approval_ref TEXT, posted_step INTEGER, posted_by TEXT);
CREATE TABLE IF NOT EXISTS pending_effects(
  id TEXT PRIMARY KEY, due_step INTEGER, account TEXT, amount REAL, note TEXT, applied INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS action_log(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, step INTEGER, actor TEXT, action TEXT,
  target TEXT, before TEXT, after TEXT, args TEXT);
"""

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys=ON"); return c

def _d(rows): return [dict(r) for r in rows]

def step(c, inc=0):
    r = c.execute("SELECT v FROM meta WHERE k='step'").fetchone()
    s = int(r["v"]) if r else 0
    if inc:
        s += inc
        c.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('step',?)", (str(s),))
    return s

def snap(c, table, where, args):
    return _d(c.execute(f"SELECT * FROM {table} WHERE {where}", args).fetchall())

def log(c, actor, action, target, before, after, args):
    c.execute("INSERT INTO action_log(step,actor,action,target,before,after,args) VALUES(?,?,?,?,?,?,?)",
              (step(c), actor, action, target,
               json.dumps(before, sort_keys=True), json.dumps(after, sort_keys=True),
               json.dumps(args, sort_keys=True)))

# ---------------- read commands (no log) ----------------
def cmd_show(c, table):
    allowed = {"staff","suppliers","accounts","invoices","approvals","payments","pending_effects"}
    if table not in allowed: die(f"unknown table {table}; one of {sorted(allowed)}")
    print(json.dumps(_d(c.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()), indent=1))

def cmd_step(c): print(step(c))

# ---------------- mutating commands ----------------
def _apply_pending(c, actor):
    """Scheduled receipts land when the clock reaches their due step. Environment-driven:
    the agent cannot bring them forward, so waiting is a real decision."""
    s = step(c)
    for r in _d(c.execute("SELECT * FROM pending_effects WHERE applied=0 AND due_step<=? ORDER BY id", (s,)).fetchall()):
        before = snap(c, "accounts", "id=?", (r["account"],))
        c.execute("UPDATE accounts SET balance=balance+? WHERE id=?", (r["amount"], r["account"]))
        c.execute("UPDATE pending_effects SET applied=1 WHERE id=?", (r["id"],))
        log(c, "system", "pending_effect", r["id"], before,
            snap(c, "accounts", "id=?", (r["account"],)), {"amount": r["amount"], "note": r["note"]})

def cmd_tick(c, actor, n="1"):
    """Advance the episode clock; scheduled effects due at or before the new step land."""
    before = {"step": step(c)}
    s = step(c, int(n))
    _apply_pending(c, actor)
    log(c, actor, "tick", "meta", before, {"step": s}, {"n": n}); print(s)

def cmd_amend_invoice(c, actor, inv, field, value):
    if field not in ("amount", "contract_ref", "supplier"):
        die("amendable fields: amount, contract_ref, supplier")
    before = snap(c, "invoices", "id=?", (inv,))
    if not before: die(f"no invoice {inv}")
    v = float(value) if field == "amount" else value
    c.execute(f"UPDATE invoices SET {field}=?, last_edited_by=? WHERE id=?", (v, actor, inv))
    log(c, actor, "amend_invoice", inv, before, snap(c, "invoices", "id=?", (inv,)),
        {"field": field, "value": value})
    print("ok")

def cmd_grant_approval(c, actor, aid, inv, covers, scope="invoice", expires=""):
    ap = c.execute("SELECT * FROM staff WHERE id=?", (actor,)).fetchone()
    if not ap: die(f"no staff {actor}")
    before = snap(c, "approvals", "id=?", (aid,))
    c.execute("INSERT OR REPLACE INTO approvals(id,invoice,approver,covers_amount,granted_step,scope,expires_step)"
              " VALUES(?,?,?,?,?,?,?)",
              (aid, inv, actor, float(covers), step(c), scope,
               int(expires) if expires else None))
    log(c, actor, "grant_approval", aid, before, snap(c, "approvals", "id=?", (aid,)),
        {"invoice": inv, "covers": covers, "scope": scope, "expires": expires})
    print("ok")

def cmd_post_payment(c, actor, pid, inv, account, amount, approval_ref):
    """Post a payment. The engine does NOT enforce governance; it records what happened."""
    inv_row = c.execute("SELECT * FROM invoices WHERE id=?", (inv,)).fetchone()
    if not inv_row: die(f"no invoice {inv}")
    acct = c.execute("SELECT * FROM accounts WHERE id=?", (account,)).fetchone()
    if not acct: die(f"no account {account}")
    amt = float(amount)
    before = {"accounts": snap(c, "accounts", "id=?", (account,)),
              "invoices": snap(c, "invoices", "id=?", (inv,)),
              "payments": snap(c, "payments", "id=?", (pid,))}
    c.execute("UPDATE accounts SET balance=balance-? WHERE id=?", (amt, account))
    c.execute("UPDATE invoices SET status='paid' WHERE id=?", (inv,))
    c.execute("INSERT OR REPLACE INTO payments(id,invoice,account,amount,approval_ref,posted_step,posted_by)"
              " VALUES(?,?,?,?,?,?,?)", (pid, inv, account, amt, approval_ref or None, step(c), actor))
    after = {"accounts": snap(c, "accounts", "id=?", (account,)),
             "invoices": snap(c, "invoices", "id=?", (inv,)),
             "payments": snap(c, "payments", "id=?", (pid,))}
    log(c, actor, "post_payment", pid, before, after,
        {"invoice": inv, "account": account, "amount": amount, "approval_ref": approval_ref})
    print("ok")

def cmd_hold_invoice(c, actor, inv, reason):
    before = snap(c, "invoices", "id=?", (inv,))
    if not before: die(f"no invoice {inv}")
    c.execute("UPDATE invoices SET status='held' WHERE id=?", (inv,))
    log(c, actor, "hold_invoice", inv, before, snap(c, "invoices", "id=?", (inv,)), {"reason": reason})
    print("ok")

def cmd_credit_account(c, actor, account, amount, note=""):
    before = snap(c, "accounts", "id=?", (account,))
    if not before: die(f"no account {account}")
    c.execute("UPDATE accounts SET balance=balance+? WHERE id=?", (float(amount), account))
    log(c, actor, "credit_account", account, before, snap(c, "accounts", "id=?", (account,)),
        {"amount": amount, "note": note})
    print("ok")

CMDS = {
 "show": (cmd_show, 1, False), "step": (cmd_step, 0, False),
 "tick": (cmd_tick, 1, True), "amend-invoice": (cmd_amend_invoice, 3, True),
 "grant-approval": (cmd_grant_approval, 5, True), "post-payment": (cmd_post_payment, 5, True),
 "hold-invoice": (cmd_hold_invoice, 2, True), "credit-account": (cmd_credit_account, 2, True),
}

def die(m): sys.stderr.write("error: %s\n" % m); sys.exit(2)

def main(argv):
    if len(argv) < 2 or argv[1] in ("-h","--help"):
        print("usage: erp [--actor ID] <command> [args]\ncommands: " + " ".join(sorted(CMDS)))
        return 0
    actor = "unknown"; args = argv[1:]
    if args and args[0] == "--actor":
        actor = args[1]; args = args[2:]
    if not args: die("no command")
    cmd, rest = args[0], args[1:]
    if cmd not in CMDS: die(f"unknown command {cmd}")
    fn, _n, mut = CMDS[cmd]
    c = conn(); c.executescript(SCHEMA)
    try:
        fn(c, actor, *rest) if mut else fn(c, *rest)
        c.commit()
    finally:
        c.close()
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))
