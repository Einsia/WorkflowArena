#!/usr/bin/env python3
"""Counterparty channel for OOO-COORD tasks.

A deterministic kernel decides what a counterparty discloses: `ask <role> <topic>` releases
a fact only when its precondition is already known, otherwise it returns a deflection. The
LLM is not in the loop, so the environment cannot drift (tau2-bench measured a 16% error
rate in LLM-simulated counterparties).

Every ask is logged, so a verifier can tell a fact that was obtained from one that was
invented.
"""
from __future__ import annotations
import json, os, sqlite3, sys
DB = os.environ.get("OOO_DB", "/workspace/state.db")
BASE = """
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
CREATE TABLE IF NOT EXISTS roles(id TEXT PRIMARY KEY, name TEXT, org TEXT, note TEXT);
CREATE TABLE IF NOT EXISTS facts(
  id TEXT PRIMARY KEY, role TEXT, topic TEXT, requires TEXT,
  value TEXT, released INTEGER DEFAULT 0, deflection TEXT);
CREATE TABLE IF NOT EXISTS ask_log(
  seq INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT, topic TEXT, outcome TEXT, fact TEXT);
"""
def conn():
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row; c.executescript(BASE); return c
def die(m): sys.stderr.write("error: %s\n" % m); sys.exit(2)

def cmd_roles(c):
    print(json.dumps([dict(r) for r in c.execute("SELECT id,name,org,note FROM roles ORDER BY id")], indent=1))

def cmd_topics(c, role):
    rs = [dict(r) for r in c.execute("SELECT topic FROM facts WHERE role=? ORDER BY topic", (role,))]
    if not rs: die("no counterparty %s" % role)
    print(json.dumps([r["topic"] for r in rs], indent=1))

def cmd_ask(c, role, topic):
    f = c.execute("SELECT * FROM facts WHERE role=? AND topic=?", (role, topic)).fetchone()
    if not f:
        c.execute("INSERT INTO ask_log(role,topic,outcome,fact) VALUES(?,?,'no_such_topic',NULL)", (role, topic))
        c.commit(); print(json.dumps({"reply": "I have nothing on that."})); return
    req = f["requires"]
    if req:
        done = c.execute("SELECT released FROM facts WHERE id=?", (req,)).fetchone()
        if not done or not done["released"]:
            c.execute("INSERT INTO ask_log(role,topic,outcome,fact) VALUES(?,?,'withheld',?)", (role, topic, f["id"]))
            c.commit(); print(json.dumps({"reply": f["deflection"]})); return
    c.execute("UPDATE facts SET released=1 WHERE id=?", (f["id"],))
    c.execute("INSERT INTO ask_log(role,topic,outcome,fact) VALUES(?,?,'released',?)", (role, topic, f["id"]))
    c.commit(); print(json.dumps({"reply": f["value"]}))

CMDS = {"roles": (cmd_roles, 0), "topics": (cmd_topics, 1), "ask": (cmd_ask, 2)}
def main(a):
    if len(a) < 2 or a[1] in ("-h", "--help"):
        print("usage: npc roles | npc topics <role> | npc ask <role> <topic>"); return 0
    cmd = a[1]
    if cmd not in CMDS: die("unknown command %s" % cmd)
    fn, n = CMDS[cmd]
    if len(a) - 2 < n: die("%s needs %d argument(s)" % (cmd, n))
    c = conn()
    try: fn(c, *a[2:2 + n]); c.commit()
    finally: c.close()
    return 0
if __name__ == "__main__": sys.exit(main(sys.argv))
