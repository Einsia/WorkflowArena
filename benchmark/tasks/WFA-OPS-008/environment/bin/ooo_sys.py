#!/usr/bin/env python3
"""Generic record system for OOO tasks: SQLite state + append-only action log.

The schema is supplied per task in `schema.sql` next to the database. Every mutating
command records one action_log row with the full before/after of the rows it touched and
the episode step, so a verifier can judge the process, not only the final state.

Deterministic: no wall clock, no RNG. "Now" is the episode step.
"""
from __future__ import annotations
import json, os, sqlite3, sys

DB = os.environ.get("OOO_DB", "/workspace/state.db")
BASE = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS action_log(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, step INTEGER, actor TEXT, action TEXT,
  table_name TEXT, target TEXT, before TEXT, after TEXT, args TEXT);
CREATE TABLE IF NOT EXISTS pending_effects(
  id TEXT PRIMARY KEY, due_step INTEGER, table_name TEXT, target TEXT,
  field TEXT, delta REAL, note TEXT, applied INTEGER DEFAULT 0);
"""

def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; return c

def _d(rows): return [dict(r) for r in rows]
def die(m): sys.stderr.write("error: %s\n" % m); sys.exit(2)

def tables(c):
    return {r["name"] for r in c.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()} - {"action_log", "meta", "pending_effects"}

def step(c, inc=0):
    r = c.execute("SELECT v FROM meta WHERE k='step'").fetchone()
    s = int(r["v"]) if r else 0
    if inc:
        s += inc; c.execute("INSERT OR REPLACE INTO meta(k,v) VALUES('step',?)", (str(s),))
    return s

def snap(c, t, tid):
    try: return _d(c.execute(f"SELECT * FROM {t} WHERE id=?", (tid,)).fetchall())
    except sqlite3.OperationalError: return []

def log(c, actor, action, t, tid, before, after, args):
    c.execute("INSERT INTO action_log(step,actor,action,table_name,target,before,after,args)"
              " VALUES(?,?,?,?,?,?,?,?)",
              (step(c), actor, action, t, tid, json.dumps(before, sort_keys=True),
               json.dumps(after, sort_keys=True), json.dumps(args, sort_keys=True)))

def _cols(c, t): return [r[1] for r in c.execute(f"PRAGMA table_info({t})").fetchall()]

def cmd_show(c, t, *rest):
    if t not in tables(c): die("unknown table %s; one of %s" % (t, sorted(tables(c))))
    print(json.dumps(_d(c.execute(f"SELECT * FROM {t} ORDER BY id").fetchall()), indent=1))

def cmd_step(c, *rest): print(step(c))

def cmd_tick(c, actor, n="1"):
    before = {"step": step(c)}; s = step(c, int(n))
    for r in _d(c.execute("SELECT * FROM pending_effects WHERE applied=0 AND due_step<=? ORDER BY id",
                          (s,)).fetchall()):
        b = snap(c, r["table_name"], r["target"])
        c.execute(f"UPDATE {r['table_name']} SET {r['field']}={r['field']}+? WHERE id=?",
                  (r["delta"], r["target"]))
        c.execute("UPDATE pending_effects SET applied=1 WHERE id=?", (r["id"],))
        log(c, "system", "pending_effect", r["table_name"], r["target"], b,
            snap(c, r["table_name"], r["target"]), {"delta": r["delta"], "note": r["note"]})
    log(c, actor, "tick", "meta", "step", before, {"step": s}, {"n": n}); print(s)

def cmd_create(c, actor, t, tid, *kv):
    if t not in tables(c): die("unknown table %s" % t)
    if snap(c, t, tid): die("%s %s already exists" % (t, tid))
    d = dict(x.split("=", 1) for x in kv)
    cols = _cols(c, t)
    bad = [k for k in d if k not in cols]
    if bad: die("unknown field(s) %s for %s; fields: %s" % (bad, t, cols))
    d["id"] = tid
    c.execute(f"INSERT INTO {t} ({','.join(d)}) VALUES ({','.join('?' * len(d))})", tuple(d.values()))
    log(c, actor, "create", t, tid, [], snap(c, t, tid), d); print("ok")

def cmd_update(c, actor, t, tid, *kv):
    if t not in tables(c): die("unknown table %s" % t)
    before = snap(c, t, tid)
    if not before: die("no %s %s" % (t, tid))
    d = dict(x.split("=", 1) for x in kv)
    cols = _cols(c, t)
    bad = [k for k in d if k not in cols or k == "id"]
    if bad: die("cannot set %s on %s" % (bad, t))
    c.execute(f"UPDATE {t} SET {','.join(k + '=?' for k in d)} WHERE id=?", (*d.values(), tid))
    log(c, actor, "update", t, tid, before, snap(c, t, tid), d); print("ok")

def cmd_delete(c, actor, t, tid):
    before = snap(c, t, tid)
    if not before: die("no %s %s" % (t, tid))
    c.execute(f"DELETE FROM {t} WHERE id=?", (tid,))
    log(c, actor, "delete", t, tid, before, [], {}); print("ok")

CMDS = {"show": (cmd_show, False), "step": (cmd_step, False), "tick": (cmd_tick, True),
        "create": (cmd_create, True), "update": (cmd_update, True), "delete": (cmd_delete, True)}

def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print("usage: sys [--actor ID] <show|step|tick|create|update|delete> ...\n"
              "  show   <table>\n  create <table> <id> field=value ...\n"
              "  update <table> <id> field=value ...\n  delete <table> <id>\n  tick [n]")
        return 0
    actor, args = "unknown", argv[1:]
    if args[0] == "--actor": actor, args = args[1], args[2:]
    if not args: die("no command")
    cmd, rest = args[0], args[1:]
    if cmd not in CMDS: die("unknown command %s" % cmd)
    fn, mut = CMDS[cmd]
    c = conn(); c.executescript(BASE)
    sch = os.path.join(os.path.dirname(os.path.abspath(DB)), "schema.sql")
    if os.path.exists(sch): c.executescript(open(sch).read())
    try:
        fn(c, actor, *rest) if mut else fn(c, *rest)
        c.commit()
    finally:
        c.close()
    return 0

if __name__ == "__main__": sys.exit(main(sys.argv))
