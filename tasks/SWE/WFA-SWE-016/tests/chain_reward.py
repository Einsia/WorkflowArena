"""Per-milestone reward for a chained SSE task, run after grade.py.

grade.py already produced /logs/verifier/report.json with one verdict per
expected test. This script re-reads that report and replaces the reward with
the SWE-Milestone metric, which is what makes a chain harder than the same
work done as independent targets: fixing this milestone's tests earns recall,
breaking an earlier milestone's tests costs precision.

    required  = this milestone's fail-to-pass set, frozen at construction time
                from an empty-solution run (tests/f2p.json)
    fixed     = required tests passing now
    broken    = tests that passed before this milestone and fail now:
                every earlier milestone's expected set, plus the tests inside
                this milestone's own files that already passed at the base state
    recall    = fixed / |required|
    precision = (fixed + 1) / (fixed + broken + 1)
    score     = harmonic mean of recall and precision
    solved    = 1 only if every required test passes and nothing is broken

Reference: SWE-Milestone (arXiv 2603.13428) Sec 5.1. The +1 smoothing is
theirs; it keeps a no-impact submission from scoring a perfect precision.

Keys are written to /logs/verifier/reward.json. Harbor's
``multi_step_reward_strategy = "mean"`` averages each key across milestones,
so the trial-level ``solved`` is the milestone resolve rate.
"""
from __future__ import annotations

import json
from pathlib import Path

TESTS = Path("/tests")
LOG = Path("/logs/verifier")


def read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text())
    except Exception:
        return default


def main() -> None:
    chain = read_json(TESTS / "chain.json", {}) or {}
    f2p = read_json(TESTS / "f2p.json", {}) or {}
    expected = read_json(TESTS / "expected.json", {}) or {}
    report = read_json(LOG / "report.json", {}) or {}

    if not chain or not f2p or not expected or not report:
        raise ValueError("Missing evaluator contract or report")
    if report.get("errors") and not report.get("tampered"):
        raise ValueError("Incomplete grading: " + str(report["errors"]))
    integrity = LOG / "protected-check.txt"
    if integrity.exists():
        checked = json.loads(integrity.read_text())
        if checked.get("changed") or checked.get("missing"):
            report["tampered"] = True

    step = chain.get("step_id") or ""
    current_group = chain.get("current_group") or ""
    prior_groups = chain.get("prior_groups") or []

    verdicts = report.get("tests") or {}

    def passed(group: str, test: str) -> bool:
        # grade.py keys verdicts as "<group>::<test>" and falls back to the bare
        # test name for runners that cannot be grouped.
        for key in (f"{group}::{test}", test):
            if key in verdicts:
                return verdicts[key] == "passed"
        return False

    required = list(f2p.get(current_group) or [])
    fixed = sum(1 for t in required if passed(current_group, t))

    # Everything that was already green before this milestone ran.
    p2p: list[tuple[str, str]] = []
    own_f2p = set(required)
    for t in expected.get(current_group) or []:
        if t not in own_f2p:
            p2p.append((current_group, t))
    for g in prior_groups:
        for t in expected.get(g) or []:
            p2p.append((g, t))

    broken = sum(1 for g, t in p2p if not passed(g, t))

    recall = fixed / len(required) if required else 0.0
    precision = (fixed + 1) / (fixed + broken + 1)
    score = (
        2 * recall * precision / (recall + precision) if (recall + precision) else 0.0
    )
    solved = 1 if required and fixed == len(required) and broken == 0 else 0

    out = {
        "reward": round(score, 6),
        "score": 100 * score,
        "full_success": bool(solved),
        "recall": round(recall, 6),
        "precision": round(precision, 6),
        "solved": solved,
        "step_id": step,
        "current_group": current_group,
        "prior_groups": prior_groups,
        "required_total": len(required),
        "required_fixed": fixed,
        "p2p_total": len(p2p),
        "p2p_broken": broken,
        "grader_errors": len(report.get("errors") or []),
        "tampered": int(bool(report.get("tampered"))),
    }
    if out["tampered"]:
        out.update({"reward": 0.0, "score": 0.0, "solved": 0, "full_success": False})

    (LOG / "reward.json").write_text(json.dumps(out, indent=1) + "\n")
    (LOG / "reward.txt").write_text(f"{out['reward']}\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
