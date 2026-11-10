#!/usr/bin/env python3
"""WorkflowArena sci-pr (C1) verifier helper. Runs inside the verifier image (python>=3.9, stdlib only).

  wfs_sci_pr.py pre     REPO TESTS_DIR LOG_DIR   clean agent build products, tamper checks -> LOG_DIR/tamper.json
  wfs_sci_pr.py overlay REPO TESTS_DIR           put hidden tests in place (hidden-test-files.txt; absent => delete)
  wfs_sci_pr.py result  TESTS_DIR LOG_DIR        parse logs -> reward.txt (0/1), reward.json (numbers only), details.json

Start-tree inventory (/opt/wfs/start-files.txt, start-links.txt) is produced inside the verifier image build
from the pinned upstream tarball, never from the agent artifact.
Parsing logic follows the original task verification logic (summary line, junit, ctest).
"""
import fnmatch
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import xml.etree.ElementTree as ET

FORBIDDEN_NEW = ["conftest.py", "pytest.ini", "tox.ini", "sitecustomize.py", "usercustomize.py", "*.pth"]
BUILD_DIR_NAMES = {"build", "__pycache__", ".pytest_cache", "dist", ".eggs", ".tox", "_skbuild"}
BUILD_FILE_GLOBS = ["*.so", "*.so.*", "*.o", "*.a", "*.pyc", "*.pyo", "*.dylib", "*.mod"]
ANSI = re.compile(r"\x1b\[[0-9;]*m")
INV = "/opt/wfs"


def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def lines(p):
    if not os.path.exists(p):
        return []
    out = []
    for l in open(p, encoding="utf-8", errors="surrogateescape"):
        l = l.rstrip("\n")
        if l:
            out.append(l[2:] if l.startswith("./") else l)
    return out


def conf(tests):
    c = {}
    for l in open(os.path.join(tests, "wfs.conf")):
        m = re.match(r"^([A-Z_]+)=['\"]?(.*?)['\"]?$", l.strip())
        if m:
            c[m.group(1)] = m.group(2)
    return c


def cmd_pre(repo, tests, logd):
    c = conf(tests)
    start = set(lines(os.path.join(INV, "start-files.txt")))
    start_links = set(lines(os.path.join(INV, "start-links.txt")))
    start_dirs = set()
    for p in start | start_links:
        d = os.path.dirname(p)
        while d:
            start_dirs.add(d)
            d = os.path.dirname(d)
    extra_dirs = set(c.get("CLEAN_EXTRA_DIRS", "").split())
    allowed_new = set(lines(os.path.join(tests, "allowed-new.txt")))
    viol, cleaned = [], []
    if not os.path.isdir(repo) or os.path.islink(repo):
        viol.append({"kind": "repo_missing", "path": repo})
    else:
        # 1. remove agent build products that are not part of the start tree (the verifier rebuilds from source)
        for d, dirs, files in os.walk(repo, topdown=True):
            rd = os.path.relpath(d, repo)
            rd = "" if rd == "." else rd
            keep = []
            for x in dirs:
                rel = os.path.join(rd, x) if rd else x
                full = os.path.join(d, x)
                if os.path.islink(full):
                    files.append(x)
                    continue
                if rel not in start_dirs and (x in BUILD_DIR_NAMES or x.endswith(".egg-info") or rel in extra_dirs):
                    shutil.rmtree(full, ignore_errors=True)
                    cleaned.append(rel + "/")
                else:
                    keep.append(x)
            dirs[:] = keep
            for x in files:
                rel = os.path.join(rd, x) if rd else x
                full = os.path.join(d, x)
                if rel in start or rel in start_links:
                    continue
                gen = False
                if any(fnmatch.fnmatch(x, g) for g in BUILD_FILE_GLOBS):
                    gen = True
                else:
                    stem, ext = os.path.splitext(x)
                    if ext in (".c", ".cpp", ".h") and (os.path.exists(os.path.join(d, stem + ".pyx"))
                                                       or os.path.exists(os.path.join(d, stem.replace("_api", "") + ".pyx"))):
                        gen = True
                if gen:
                    try:
                        os.unlink(full)
                        cleaned.append(rel)
                    except OSError:
                        pass
        # 2. tamper checks
        for d, dirs, files in os.walk(repo):
            for x in dirs + files:
                full = os.path.join(d, x)
                rel = os.path.relpath(full, repo)
                if os.path.islink(full) and rel not in start_links:
                    viol.append({"kind": "symlink_created", "path": rel})
                elif x in files and rel not in start and rel not in allowed_new and \
                        any(fnmatch.fnmatch(x, g) for g in FORBIDDEN_NEW):
                    viol.append({"kind": "forbidden_new_file", "path": rel})
        man = json.load(open(os.path.join(tests, "protected-files.json")))
        for rel, h in sorted(man["files"].items()):
            fp = os.path.join(repo, rel)
            if not os.path.lexists(fp):
                viol.append({"kind": "protected_missing", "path": rel})
            elif os.path.islink(fp) or not os.path.isfile(fp) or sha_file(fp) != h:
                viol.append({"kind": "protected_modified", "path": rel})
    rep = {"tampered": bool(viol), "n_violations": len(viol), "violations": viol[:200],
           "n_cleaned": len(cleaned), "cleaned_sample": cleaned[:100]}
    json.dump(rep, open(os.path.join(logd, "tamper.json"), "w"), indent=1)
    print("pre: cleaned %d build products, %d violations" % (len(cleaned), len(viol)))
    for v in viol[:20]:
        print("  VIOLATION", v["kind"], v["path"])


def cmd_overlay(repo, tests):
    n = 0
    for f in lines(os.path.join(tests, "hidden-test-files.txt")):
        src, dst = os.path.join(tests, "hidden_tests", f), os.path.join(repo, f)
        if os.path.lexists(dst) and (os.path.islink(dst) or os.path.isdir(dst)):
            shutil.rmtree(dst) if os.path.isdir(dst) and not os.path.islink(dst) else os.unlink(dst)
        if os.path.exists(src):
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(src, dst)
            n += 1
        elif os.path.lexists(dst):
            os.unlink(dst)
    print("overlay: %d hidden test files" % n)


def read(p):
    return ANSI.sub("", open(p, errors="replace").read()) if os.path.exists(p) else ""


def parse_summary(txt):
    line = None
    for l in txt.splitlines():
        l2 = l.strip().strip("=").strip()
        if re.search(r"\d+ (passed|failed|errors?|error|skipped|xfailed|xpassed|deselected)\b", l2) and re.search(r" in [\d.]+s", l2):
            line = l2
    if line is None:
        for l in txt.splitlines():
            if re.search(r"(no tests ran|\d+ errors? in)", l):
                line = l.strip().strip("=").strip()
    c = {"passed": 0, "failed": 0, "errors": 0, "skipped": 0, "xfailed": 0, "xpassed": 0}
    if line:
        for n, k in re.findall(r"(\d+) (passed|failed|errors?|skipped|xfailed|xpassed)", line):
            k = "errors" if k.startswith("error") else k
            c[k] += int(n)
    return line, c


def parse_junit(paths):
    res = {}
    rank = {"passed": 0, "skipped": 1, "failed": 2, "error": 3}
    for p in paths:
        try:
            root = ET.parse(p).getroot()
        except Exception:
            continue
        for tc in root.iter("testcase"):
            tid = "%s::%s" % (tc.get("classname", ""), tc.get("name", ""))
            st = "passed"
            for ch in tc:
                if ch.tag == "error":
                    st = "error"
                elif ch.tag == "failure":
                    st = "failed" if st != "error" else st
                elif ch.tag == "skipped" and st == "passed":
                    st = "skipped"
            if tid not in res or rank[st] > rank[res[tid]]:
                res[tid] = st
    return res


def kv(txt, key):
    m = re.findall(r"^%s=(-?\d+)" % key, txt, re.M)
    return int(m[-1]) if m else None


def cmd_result(tests, logd):
    tam = json.load(open(os.path.join(logd, "tamper.json")))
    status = read(os.path.join(logd, "status.txt"))
    b, i, t = kv(status, "BUILD_EXIT"), kv(status, "IMPORT_EXIT"), kv(status, "TEST_EXIT")
    test_txt = read(os.path.join(logd, "test.log"))
    line, counts = parse_summary(test_txt)
    junit = parse_junit(sorted(glob.glob(os.path.join(logd, "junit*.xml"))))
    jc = {"passed": 0, "failed": 0, "error": 0, "skipped": 0}
    for v in junit.values():
        jc[v] += 1
    if line is None and junit:
        counts.update(passed=jc["passed"], failed=jc["failed"], errors=jc["error"], skipped=jc["skipped"])
    ctest = None
    m = re.findall(r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", test_txt)
    if m:
        _, f, n = map(int, m[-1])
        ctest = {"passed": n - f, "failed": f, "total": n}
        counts["passed"] += n - f
        counts["failed"] += f
    tampered = bool(tam["tampered"])
    built = b == 0 and i == 0
    ran = t is not None
    if tampered:
        counts = {k: 0 for k in counts}
    tot = counts["passed"] + counts["failed"] + counts["errors"]
    full = bool(not tampered and built and ran and t == 0 and counts["failed"] == 0
                and counts["errors"] == 0 and counts["passed"] > 0)
    # denominator: tests observed, but at least the reference run's test count (a module that fails to import
    # is reported by pytest as a single error, which would otherwise inflate the fraction)
    try:
        expected = int(conf(tests).get("EXPECTED_TESTS") or 0)
    except ValueError:
        expected = 0
    denom = max(tot, expected)
    frac = (counts["passed"] / denom) if denom else 0.0
    out = {"reward": 1.0 if full else 0.0, "pass_fraction": round(frac, 6), "expected_tests": expected,
           "passed": counts["passed"], "failed": counts["failed"], "errors": counts["errors"],
           "skipped": counts["skipped"], "tampered": float(tampered), "build_ok": float(built)}
    det = {"summary_line": line, "status": status.split(), "ctest": ctest, "junit_counts": jc, "tamper": tam,
           "failed_ids": sorted(k for k, v in junit.items() if v in ("failed", "error"))[:200]}
    cp = os.path.join(tests, "core.json")
    if os.path.exists(cp):
        core = json.load(open(cp))
        matched = {k: v for k, v in junit.items() if any(fnmatch.fnmatch(k, p) for p in core["tests"])}
        npass = 0 if tampered else sum(1 for v in matched.values() if v == "passed")
        exp = core.get("expected_count") or len(matched)
        out["core_pass_fraction"] = round(npass / exp, 6) if exp else 0.0
        out["core_all_passed"] = float(bool(not tampered and built and matched and npass == len(matched)
                                            and len(matched) == exp))
        det["core"] = {"expected_count": exp, "found": len(matched), "passed": npass}
    json.dump(det, open(os.path.join(logd, "details.json"), "w"), indent=1)
    json.dump(out, open(os.path.join(logd, "reward.json"), "w"))
    open(os.path.join(logd, "reward.txt"), "w").write("%s\n" % out["reward"])
    print(json.dumps(out))


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "pre":
        cmd_pre(*sys.argv[2:5])
    elif c == "overlay":
        cmd_overlay(*sys.argv[2:4])
    elif c == "result":
        cmd_result(*sys.argv[2:4])
    else:
        sys.exit("unknown subcommand " + c)
