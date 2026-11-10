#!/usr/bin/env python3
"""WorkflowArena Lean grader (mathlib-family and lean-blueprint), runs inside the verifier image.

  grade_lean.py grade    --spec /tests/spec.json --workspace /workspace --out-dir /logs/verifier
  grade_lean.py stub-ref --spec /tests/spec.json --workspace /workspace --out /opt/wfs/stub_ref.json

Reward 1 iff: the build targets compile in the verifier's own clean checkout (only the allowed files are
taken from the submission), every required constant exists with a type whose structural fingerprint
(Lean `Expr.hash`, binder names ignored) equals the reference, its axioms are within
{propext, Classical.choice, Quot.sound}, and no submitted file mentions `skipKernelTC`.

Fingerprint and axiom probes are the ones of WorkflowDatasetBuilder/scripts/verify_lean_task.py /
grade_submission.py (same Lean snippets, same parsing). Python stdlib only.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ALLOWED = {"propext", "Classical.choice", "Quot.sound"}
FORBIDDEN = re.compile(r"skipKernelTC")

FINGERPRINT_EVAL = """open Lean Meta in
#eval show MetaM Unit from do
  let env ← getEnv
  for s in [{names}] do
    let n := s.toName
    match env.find? n with
    | none => IO.println s!"WDBTYPE {{s}} MISSING"
    | some ci =>
      let us := (List.range ci.levelParams.length).map fun i => Level.param (Name.mkSimple s!"u_{{i+1}}")
      let t := ci.type.instantiateLevelParams ci.levelParams us
      IO.println s!"WDBTYPE {{s}} {{hash t}}"
"""


def run(cmd, cwd, timeout, log=None):
    t = time.time()
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        out, code = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        out, code = f"TIMEOUT after {timeout}s\n" + out, 124
    if log is not None:
        with open(log, "a") as f:
            f.write(f"\n$ {' '.join(cmd)}  [rc={code} {time.time() - t:.0f}s]\n{out[-20000:]}\n")
    return code, out, round(time.time() - t, 1)


def fingerprint_snippet(names):
    return FINGERPRINT_EVAL.format(names=", ".join(json.dumps(n) for n in names))


def parse_types(out):
    types = {}
    for line in out.splitlines():
        if line.startswith("WDBTYPE "):
            _, n, h = line.split(" ", 2)
            types[n] = h.strip()
    return types


def probe_text(imp, names):
    lines = [f"import {imp}", "set_option pp.universes false", "set_option pp.fieldNotation false",
             "set_option pp.mvars false", "set_option pp.funBinderTypes true", ""]
    for n in names:
        lines += [f"#check @{n}", f"#print axioms {n}"]
    return "\n".join(lines) + "\n"


def axioms_of(probe, n):
    m = re.search(rf"'{re.escape(n)}' depends on axioms: \[([^\]]*)\]", probe)
    if m:
        return sorted(x.strip() for x in m[1].split(",") if x.strip())
    if re.search(rf"'{re.escape(n)}' does not depend on any axioms", probe):
        return []
    return None


def norm(name):
    return name[2:] if name.startswith("./") else name


def collect(spec, ws: Path, log):
    """lean-blueprint: keep the verifier's pristine sources; take only the target file and new .lean files."""
    c = spec["collect"]
    with tarfile.open(c["pristine_tar"]) as tf:
        pristine = {norm(m.name) for m in tf.getmembers() if m.isfile()}
    sub = Path("/tmp/wfs-submission")
    shutil.rmtree(sub, ignore_errors=True)
    sub.mkdir(parents=True)
    taken, ignored = [], 0
    for d in c["dirs"]:
        src = ws / d
        if src.exists():
            shutil.move(str(src), str(sub / d))
    with tarfile.open(c["pristine_tar"]) as tf:
        members = [m for m in tf.getmembers() if any(norm(m.name) == d or norm(m.name).startswith(d + "/")
                                                     for d in c["dirs"])]
        tf.extractall(ws, members=members, filter="data")
    for d in c["dirs"]:
        root = sub / d
        if not root.exists():
            continue
        for p in sorted(root.rglob("*")):
            if not p.is_file() or p.is_symlink():
                continue
            rel = str(p.relative_to(sub))
            if rel == c["target_file"] or (rel.endswith(".lean") and rel not in pristine):
                dst = ws / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(p, dst)
                taken.append(rel)
            else:
                ignored += 1
    with open(log, "a") as f:
        f.write(f"collected {len(taken)} files, ignored {ignored}: {taken}\n")
    return taken


def cmd_stub_ref(a, spec):
    """Reference fingerprint of the target statement, elaborated from the clean start stub."""
    ws = Path(a.workspace)
    names = spec["names"]
    text = (ws / spec["collect"]["target_file"]).read_text()
    # A probe file is not a module: drop module-system headers (they do not affect the statement).
    lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if s == "module" or re.fullmatch(r"@\[expose\]\s+public\s+section", s) or s == "public section":
            continue
        ln = re.sub(r"^(\s*)public\s+(meta\s+)?import\b", r"\1import", ln)
        lines.append(ln)
    probe = Path("/opt/wfs/WFSStubRef.lean")
    probe.parent.mkdir(parents=True, exist_ok=True)
    probe.write_text("\n".join(lines) + "\n\n" + fingerprint_snippet(names))
    code, out, _ = run(["lake", "env", "lean", "-DwarningAsError=false", str(probe)], ws, 7200)
    types = parse_types(out)
    if not types or any(types.get(n, "MISSING") == "MISSING" for n in names):
        sys.stderr.write(out[-6000:])
        sys.exit("stub-ref: could not fingerprint the target statement")
    Path(a.out).write_text(json.dumps(types, indent=2) + "\n")
    print(json.dumps(types))


def cmd_grade(a, spec):
    ws = Path(a.workspace)
    out_dir = Path(a.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for f in ("reward.txt", "reward.json"):
        (out_dir / f).unlink(missing_ok=True)
    log = out_dir / "grade.log"
    ref = json.loads(Path(spec["ref_types_file"]).read_text())
    names = sorted(ref)
    res = {"kind": spec["kind"], "required": len(names)}
    if spec.get("collect"):
        scanned = collect(spec, ws, log)
        res["collected_files"] = scanned
    else:
        scanned = [str(p.relative_to(ws)) for g in spec["scan_globs"] for p in ws.glob(g) if p.is_file()]
    hits = []
    for rel in scanned:
        try:
            if FORBIDDEN.search((ws / rel).read_text(errors="ignore")):
                hits.append(rel)
        except OSError:
            pass
    res["forbidden_hits"] = hits
    code, out, sec = run(["lake", "build", *spec["build_targets"]], ws, spec.get("build_timeout", 10800), log)
    res["build"] = {"ok": code == 0, "rc": code, "seconds": sec, "tail": out[-3000:] if code else ""}
    per = {}
    if code == 0:
        fp = ws / "WFSTypes.lean"
        fp.write_text(f"import {spec['import']}\n" + fingerprint_snippet(names))
        fcode, fout, _ = run(["lake", "env", "lean", fp.name], ws, 3600, log)
        types = parse_types(fout)
        if not types:
            sys.stderr.write(fout[-4000:])
            print(json.dumps(res, indent=2))
            sys.exit("grader error: fingerprint probe produced no output")
        pp = ws / "WFSProbe.lean"
        pp.write_text(probe_text(spec["import"], names))
        _, probe, _ = run(["lake", "env", "lean", pp.name], ws, 3600, log)
        for n in names:
            ax = axioms_of(probe, n)
            per[n] = {"present": types.get(n, "MISSING") != "MISSING", "type_matches": types.get(n) == ref[n],
                      "axioms": ax, "axioms_ok": ax is not None and set(ax) <= ALLOWED}
    else:
        per = {n: {"present": False, "type_matches": False, "axioms": None, "axioms_ok": False} for n in names}
    res["declarations"] = per
    ok = [n for n, v in per.items() if v["present"] and v["type_matches"] and v["axioms_ok"]]
    passed = res["build"]["ok"] and not hits and len(ok) == len(names) and len(names) > 0
    res["passed"] = passed
    (out_dir / "details.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    reward = 1 if passed else 0
    (out_dir / "reward.json").write_text(json.dumps({
        "reward": reward, "build_ok": int(res["build"]["ok"]), "n_required": len(names), "n_matched": len(ok),
        "fraction": round(len(ok) / max(1, len(names)), 4), "forbidden_hits": len(hits)}) + "\n")
    (out_dir / "reward.txt").write_text(f"{reward}\n")
    print(json.dumps({"reward": reward, "build_ok": res["build"]["ok"], "matched": len(ok), "required": len(names),
                      "forbidden_hits": hits}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["grade", "stub-ref"])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--workspace", default="/workspace")
    ap.add_argument("--out-dir", default="/logs/verifier")
    ap.add_argument("--out", default="/opt/wfs/stub_ref.json")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    os.environ.setdefault("LAKE_NO_UPDATE", "1")
    (cmd_stub_ref if a.cmd == "stub-ref" else cmd_grade)(a, spec)


if __name__ == "__main__":
    main()
