#!/usr/bin/env python3
"""WorkflowArena Lean grader (mathlib-family and lean-blueprint), runs inside the verifier image.

  grade_lean.py grade    --spec /tests/spec.json --workspace /workspace --out-dir /logs/verifier
  grade_lean.py stub-ref --spec /tests/spec.json --workspace /workspace --out /opt/wfs/stub_ref.json
  grade_lean.py ref-values --spec /tests/spec.json --workspace /workspace --patch reference.patch --out values.json

Reward 1 iff: the build targets compile in the verifier's own clean checkout (only the allowed files are
taken from the submission), every required constant exists with a type whose structural fingerprint
(Lean `Expr.hash`, binder names ignored) equals the reference, its axioms are within
{propext, Classical.choice, Quot.sound}, and no submitted file mentions `skipKernelTC`.

mathlib-family specs may add (both off for lean-blueprint specs, whose behaviour is unchanged):
  "restore": every file of the pristine tree under restore.dirs that is not listed in restore.keep is put back
    to its pristine content (new files and the kept files stay as submitted); pristine `import` lines missing
    from restore.root_file are re-added, so the whole existing library stays imported and unmodified.
  "ref_values_file": value fingerprints of the reference (written by `ref-values` on the oracle build): every
    required non-theorem constant and every non-theorem constant of the reference's new modules reachable from
    the required constants must exist with the same kind, type and value fingerprint (Expr.hash with level
    params renamed and levels normalized, every proof subterm, i.e. a subterm headed by a Prop-valued theorem, erased, and constants
    with macro scopes inlined as their own fingerprint; inductive types/structures: type, parameter/index counts
    and constructor names and types).

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


VALUES_LEAN = r"""open Lean Meta

def wfsInst (ci : ConstantInfo) (e : Expr) : Expr :=
  e.instantiateLevelParams ci.levelParams
    ((List.range ci.levelParams.length).map fun i => Level.param (Name.mkSimple s!"u_{i+1}"))

/-- Replace every subterm headed by a Prop-valued theorem (a proof) by a fixed marker. -/
def wfsErase (e : Expr) : MetaM Expr := do
  let env ← getEnv
  let mut s : NameSet := {}
  for c in e.getUsedConstants do
    if let some (.thmInfo t) := env.find? c then
      if (← try isProp t.type catch _ => pure false) then s := s.insert c
  return e.replace fun x => match x.getAppFn with
    | .const n _ => if s.contains n then some (.const `WFS.proof []) else none
    | _ => none

mutual
/-- Normalize universe levels, erase proofs and inline constants with macro scopes (e.g. the hygienic helpers of `irreducible_def`,
whose names depend on the source position) by their own fingerprint. -/
partial def wfsNorm (e : Expr) : MetaM Expr := do
  let e ← wfsErase (e.replaceLevel fun l => some l.normalize)
  let mut m : Array (Name × Name) := #[]
  for c in e.getUsedConstants do
    if c.hasMacroScopes then m := m.push (c, Name.mkSimple s!"WFS.hyg {← wfsFp c}")
  if m.isEmpty then return e
  return e.replace fun x => match x with
    | .const n _ => (m.find? (·.1 == n)).map fun p => .const p.2 []
    | _ => none

partial def wfsFp (n : Name) : MetaM String := do
  let env ← getEnv
  let some ci := env.find? n | return "MISSING"
  let ty := hash (← wfsNorm (wfsInst ci ci.type))
  match ci with
  | .thmInfo _ => return s!"thm {ty}"
  | .defnInfo d => return s!"def {ty} {hash (← wfsNorm (wfsInst ci d.value))}"
  | .opaqueInfo d => return s!"opaque {ty} {hash (← wfsNorm (wfsInst ci d.value))}"
  | .inductInfo d =>
    let mut h : UInt64 := ty
    for c in d.ctors do
      let some cc := env.find? c | return "BADCTOR"
      h := mixHash h (mixHash (hash c) (hash (← wfsNorm (wfsInst ci cc.type))))
    return s!"ind {ty} {d.numParams} {d.numIndices} {h}"
  | .axiomInfo _ => return s!"axiom {ty}"
  | .ctorInfo _ => return s!"ctor {ty}"
  | .recInfo _ => return s!"rec {ty}"
  | .quotInfo _ => return s!"quot {ty}"
end

def wfsDeps (n : Name) : MetaM (Array Name) := do
  let env ← getEnv
  let some ci := env.find? n | return #[]
  let mut es : Array Expr := #[ci.type]
  match ci with
  | .defnInfo d => es := es.push (← wfsErase d.value)
  | .opaqueInfo d => es := es.push (← wfsErase d.value)
  | .inductInfo d => for c in d.ctors do es := es.push (.const c [])
  | _ => pure ()
  return es.foldl (fun acc e => acc ++ e.getUsedConstants) #[]

/-- Reference mode: required names plus every non-theorem constant of the new modules reachable from them. -/
def wfsClosure (req : List String) (newMods : List String) : MetaM Unit := do
  let env ← getEnv
  let mods : NameSet := newMods.foldl (fun s m => s.insert m.toName) {}
  let isNew (c : Name) : Bool := match env.getModuleIdxFor? c with
    | some i => mods.contains (env.header.moduleNames[i.toNat]!)
    | none => false
  let mut seen : NameSet := {}
  let mut todo : Array Name := #[]
  for s in req do
    seen := seen.insert s.toName
    todo := todo.push s.toName
  while todo.size > 0 do
    let n := todo[todo.size - 1]!
    todo := todo.pop
    let req? := req.contains n.toString
    if !n.hasMacroScopes then
      let fp ← wfsFp n
      if !(fp.startsWith "thm") || req? then
        IO.println s!"WDBVAL {n} {if req? then "req" else "dep"} {fp}"
      if fp.startsWith "thm" && !req? then continue
    for c in ← wfsDeps n do
      if !seen.contains c && isNew c then
        seen := seen.insert c
        todo := todo.push c

/-- Grade mode: fingerprint the given constants (looked up by name, else by printed name). -/
def wfsCheck (ns : List String) : MetaM Unit := do
  let env ← getEnv
  let mut left : List String := []
  for s in ns do
    if (env.find? s.toName).isSome then IO.println s!"WDBVAL {s} chk {← wfsFp s.toName}"
    else left := s :: left
  if !left.isEmpty then
    let found := env.constants.fold (fun acc n _ => if left.contains n.toString then (n.toString, n) :: acc else acc) []
    for s in left do
      match found.lookup s with
      | some n => IO.println s!"WDBVAL {s} chk {← wfsFp n}"
      | none => IO.println s!"WDBVAL {s} chk MISSING"
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


IMPORT_RE = re.compile(r"^\s*(?:public\s+)?(?:meta\s+)?import\s+(\S+)")


def restore(spec, ws: Path, log):
    """mathlib-family: put every pristine file under restore.dirs (except restore.keep) back; keep new files."""
    c = spec["restore"]
    keep = set(c.get("keep", []))
    dirs = c["dirs"]
    for d in dirs:  # never write pristine content through a submitted symlink
        root = ws / d
        if root.is_symlink():
            root.unlink()
        elif root.exists():
            for p in sorted(root.rglob("*"), reverse=True):
                if p.is_symlink():
                    p.unlink()
    restored, pristine = [], set()
    with tarfile.open(c["pristine_tar"]) as tf:
        for m in tf.getmembers():
            rel = norm(m.name)
            if not m.isfile() or rel in keep or not any(rel.startswith(d + "/") for d in dirs):
                continue
            pristine.add(rel)
            data = tf.extractfile(m).read()
            dst = ws / rel
            if dst.is_file() and dst.read_bytes() == data:
                continue
            if dst.is_dir():
                shutil.rmtree(dst)
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            restored.append(rel)
        root_file = c.get("root_file")
        added = []
        if root_file:
            want = tf.extractfile(tf.getmember("./" + root_file if "./" + root_file in tf.getnames()
                                               else root_file)).read().decode()
            dst = ws / root_file
            have = dst.read_text(errors="replace") if dst.is_file() else ""
            if dst.is_symlink():
                dst.unlink()
                dst.write_text(have)
            have_mods = {m[1] for m in map(IMPORT_RE.match, have.splitlines()) if m}
            missing = [ln.strip() for ln in want.splitlines()
                       if (m := IMPORT_RE.match(ln)) and m[1] not in have_mods]
            if missing:
                lines = have.splitlines()
                is_module = any(ln.strip().split("--")[0].strip() == "module" for ln in lines[:5])
                if not is_module:
                    missing = [re.sub(r"^public\s+", "", ln) for ln in missing]
                at = next((i + 1 for i, ln in enumerate(lines[:5]) if ln.strip().split("--")[0].strip() == "module"), 0)
                dst.write_text("\n".join(lines[:at] + missing + lines[at:]) + "\n")
                added = missing
    new = sorted(str(p.relative_to(ws)) for d in dirs if (ws / d).exists() for p in (ws / d).rglob("*.lean")
                 if p.is_file() and str(p.relative_to(ws)) not in pristine)
    scanned = new + [k for k in sorted(keep) if (ws / k).is_file()]
    with open(log, "a") as f:
        f.write(f"restored {len(restored)} changed/deleted pristine files: {restored[:200]}\n"
                f"re-added {len(added)} pristine imports to {root_file}: {added[:200]}\n"
                f"kept {len(scanned)} submitted files: {scanned}\n")
    return scanned, restored, added


def values_snippet(imp, body):
    return f"import {imp}\n" + VALUES_LEAN + "\n" + body + "\n"


def parse_values(out):
    vals = {}
    for line in out.splitlines():
        if line.startswith("WDBVAL "):
            _, n, role, fp = line.split(" ", 3)
            vals[n] = {"role": role, "fp": fp.strip()}
    return vals


def cmd_ref_values(a, spec):
    """Reference value fingerprints, run once on the oracle build (reference patch applied and built)."""
    ws = Path(a.workspace)
    names = sorted(json.loads(Path(spec["ref_types_file"]).read_text()))
    patch = Path(a.patch).read_text()
    mods = ["Mathlib"]
    for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)\nnew file mode", patch, re.M):
        if m[2].endswith(".lean"):
            mods.append(m[2][:-5].replace("/", "."))
    probe = ws / "WFSValues.lean"
    probe.write_text(values_snippet(spec["import"], "#eval wfsClosure [{}] [{}]".format(
        ", ".join(json.dumps(n) for n in names), ", ".join(json.dumps(m) for m in mods))))
    code, out, _ = run(["lake", "env", "lean", probe.name], ws, 3600)
    vals = parse_values(out)
    if code != 0 or any(n not in vals for n in names):
        sys.stderr.write(out[-6000:])
        sys.exit("ref-values: probe failed")
    pinned = {n: v for n, v in sorted(vals.items()) if not v["fp"].startswith("thm")}
    Path(a.out).write_text(json.dumps(pinned, indent=2) + "\n")
    print(json.dumps({"new_modules": mods, "pinned": len(pinned),
                      "required_pinned": sum(v["role"] == "req" for v in pinned.values())}))


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
    elif spec.get("restore"):
        scanned, restored, added = restore(spec, ws, log)
        res["submitted_files_kept"] = scanned
        res["pristine_files_restored"] = restored
        res["pristine_imports_readded"] = added
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
    refv = json.loads(Path(spec["ref_values_file"]).read_text()) if spec.get("ref_values_file") else None
    vals_ok = not refv
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
        if refv:
            vp = ws / "WFSValues.lean"
            vp.write_text(values_snippet(spec["import"], "#eval wfsCheck [{}]".format(
                ", ".join(json.dumps(n) for n in refv))))
            _, vout, _ = run(["lake", "env", "lean", vp.name], ws, 3600, log)
            got = {n: v["fp"] for n, v in parse_values(vout).items()}
            if not got:
                sys.stderr.write(vout[-4000:])
                print(json.dumps(res, indent=2))
                sys.exit("grader error: value probe produced no output")
            bad = sorted(n for n in refv if got.get(n) != refv[n]["fp"])
            res["pinned_values"] = {"checked": len(refv), "mismatched": bad[:200],
                                    "mismatched_required": [n for n in bad if refv[n]["role"] == "req"]}
            vals_ok = not bad
            for n in names:
                if n in refv:
                    per[n]["value_matches"] = n not in bad
    else:
        per = {n: {"present": False, "type_matches": False, "axioms": None, "axioms_ok": False} for n in names}
    res["declarations"] = per
    ok = [n for n, v in per.items() if v["present"] and v["type_matches"] and v["axioms_ok"]
          and v.get("value_matches", True)]
    passed = res["build"]["ok"] and not hits and len(ok) == len(names) and len(names) > 0 and vals_ok
    res["passed"] = passed
    (out_dir / "details.json").write_text(json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    reward = 1 if passed else 0
    (out_dir / "reward.json").write_text(json.dumps({
        "reward": reward, "build_ok": int(res["build"]["ok"]), "n_required": len(names), "n_matched": len(ok),
        "fraction": round(len(ok) / max(1, len(names)), 4), "forbidden_hits": len(hits),
        **({"pinned_values_ok": int(vals_ok)} if refv is not None else {})}) + "\n")
    (out_dir / "reward.txt").write_text(f"{reward}\n")
    print(json.dumps({"reward": reward, "build_ok": res["build"]["ok"], "matched": len(ok), "required": len(names),
                      "forbidden_hits": hits}))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["grade", "stub-ref", "ref-values"])
    ap.add_argument("--spec", required=True)
    ap.add_argument("--workspace", default="/workspace")
    ap.add_argument("--out-dir", default="/logs/verifier")
    ap.add_argument("--out", default="/opt/wfs/stub_ref.json")
    ap.add_argument("--patch", help="ref-values: the reference patch (its new .lean files are the new modules)")
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text())
    os.environ.setdefault("LAKE_NO_UPDATE", "1")
    {"stub-ref": cmd_stub_ref, "ref-values": cmd_ref_values, "grade": cmd_grade}[a.cmd](a, spec)


if __name__ == "__main__":
    main()
