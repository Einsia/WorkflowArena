"""Shared grader for WorkflowArena SSE tasks.

Contract (same for every task in the batch):
  * every entry in expected.json gets a verdict -- a test that never ran counts as failed
  * one failing test never stops the rest of the run
  * grading-infrastructure errors are recorded as `error`, not silently as capability failures
  * reward = weighted fraction of passed expected tests
  * tampering with the runner or pre-seeding the reward files forces reward 0

Per-task configuration lives in tests/config.json:

  {
    "runner": "cargo" | "pytest" | "gotest" | "jest" | "ctest",
    "groups": [                       # one group per target (roadmapbench) or stage (swe-milestone)
      {"id": "T1", "weight": 3, "command": ["cargo", "test", "--test", "rt_busy_tick"],
       "timeout_sec": 600}
    ],
    "cwd": "/app"
  }

expected.json lists the test identities that must pass, grouped the same way:

  {"T1": ["zero_busy_tick_panics", "multi_thread_busy_tick"], "T2": [...]}

A group whose command exits non-zero still has its individual verdicts parsed, so a build
failure in one target does not erase the evidence from the others.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

TESTS = Path("/tests")
LOG = Path("/logs/verifier")
LOG.mkdir(parents=True, exist_ok=True)

# A grader that trusts files it did not write can be gamed by pre-seeding them.
TAMPER_FILES = ("reward.txt", "reward.json", "results.json", "report.json")


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text())
    except Exception:
        return default


# --- per-runner output parsers -------------------------------------------------------------
# Each returns {test_name: "passed"|"failed"|"skipped"} for one group's output.

def parse_cargo(out):
    # cargo appends a marker to some tests, e.g. "test foo - should panic ... ok", so the
    # name cannot be assumed to run straight into the "..." separator.
    verdict = {}
    for m in re.finditer(r'^test\s+(\S+?)(?:\s+-\s+[\w\s]+?)?\s+\.\.\.\s+(ok|FAILED|ignored)',
                         out, re.M):
        name, res = m.group(1), m.group(2)
        name = name.split('::')[-1]
        verdict[name] = {'ok': 'passed', 'FAILED': 'failed', 'ignored': 'skipped'}[res]
    return verdict


def parse_pytest(out):
    verdict = {}
    for m in re.finditer(r'^(\S+?)::([\w\[\]\-\.]+)\s+(PASSED|FAILED|ERROR|SKIPPED)', out, re.M):
        verdict[m.group(2)] = {'PASSED': 'passed', 'FAILED': 'failed',
                               'ERROR': 'failed', 'SKIPPED': 'skipped'}[m.group(3)]
    return verdict


def parse_gotest(out):
    verdict = {}
    for m in re.finditer(r'^\s*---\s+(PASS|FAIL|SKIP):\s+(\S+)', out, re.M):
        verdict[m.group(2)] = {'PASS': 'passed', 'FAIL': 'failed', 'SKIP': 'skipped'}[m.group(1)]
    return verdict


def parse_jest(out):
    verdict = {}
    for m in re.finditer(r'^\s*(✓|✗|✕|○)\s+(.+?)(?:\s+\(\d+\s*ms\))?$', out, re.M):
        mark, name = m.group(1), m.group(2).strip()
        verdict[name] = {'✓': 'passed', '✗': 'failed', '✕': 'failed', '○': 'skipped'}[mark]
    return verdict


def parse_ctest(out):
    verdict = {}
    for m in re.finditer(r'^\s*\d+/\d+\s+Test\s+#\d+:\s+(\S+)\s+\.+\s*(Passed|\*\*\*Failed|'
                         r'\*\*\*Skipped)', out, re.M):
        verdict[m.group(1)] = {'Passed': 'passed', '***Failed': 'failed',
                               '***Skipped': 'skipped'}[m.group(2)]
    return verdict


PARSERS = {'cargo': parse_cargo, 'pytest': parse_pytest, 'gotest': parse_gotest,
           'jest': parse_jest, 'ctest': parse_ctest}


def main():
    report = {'reward': 0.0, 'groups': {}, 'tests': {}, 'observed_all': {},
              'errors': [], 'tampered': False}

    # Refuse to trust pre-existing reward artifacts.
    for name in TAMPER_FILES:
        p = LOG / name
        if p.exists():
            report['tampered'] = True
            report['errors'].append(f'pre-existing {name} in /logs/verifier')
            try:
                p.unlink()
            except Exception:
                pass

    config = read_json(TESTS / 'config.json')
    expected = read_json(TESTS / 'expected.json')
    if not config or not expected:
        report['errors'].append('missing or unreadable tests/config.json or tests/expected.json')
        finish(report, fatal=True)

    parser = PARSERS.get(config.get('runner'))
    if parser is None:
        report['errors'].append(f"unknown runner {config.get('runner')!r}")
        finish(report, fatal=True)

    cwd = config.get('cwd', '/app')
    env = dict(os.environ, CARGO_TERM_COLOR='never', NO_COLOR='1', FORCE_COLOR='0')

    for group in config['groups']:
        gid = group['id']
        glog = LOG / f'group_{gid}.log'
        entry = {'weight': group.get('weight', 1), 'status': 'unknown', 'returncode': None}
        try:
            proc = subprocess.run(group['command'], cwd=cwd, env=env, capture_output=True,
                                  text=True, timeout=group.get('timeout_sec', 600))
            out = (proc.stdout or '') + '\n' + (proc.stderr or '')
            entry['returncode'] = proc.returncode
        except subprocess.TimeoutExpired as e:
            out = ((e.stdout or b'').decode(errors='replace') if isinstance(e.stdout, bytes)
                   else (e.stdout or '')) + f"\n[grader] group {gid} timed out"
            entry['status'] = 'timeout'
        except Exception as e:                      # infrastructure, not the solution's fault
            out = f'[grader] {type(e).__name__}: {e}'
            entry['status'] = 'error'
            report['errors'].append(f'group {gid}: {type(e).__name__}: {e}')
        glog.write_text(out)

        observed = parser(out)
        want = expected.get(gid, [])
        group_tests = {name: observed.get(name, 'not run') for name in want}
        report['tests'].update({f'{gid}::{k}': v for k, v in group_tests.items()})
        entry['passed'] = sum(v == 'passed' for v in group_tests.values())
        entry['total'] = len(want)
        entry['all_passed'] = bool(want) and entry['passed'] == entry['total']
        if entry['status'] == 'unknown':
            entry['status'] = 'ran'
        # Tests observed but not expected are recorded, never scored. Keep every
        # verdict, not just the names: a test that runs, passes under the oracle
        # and fails on the empty solution is fail-to-pass signal the required set
        # is throwing away, and that is only visible if the verdicts survive.
        # (The old code kept 20 names and no verdicts, which made every group
        # look like it had exactly 20 extras.)
        extra = sorted(set(observed) - set(want))
        if extra:
            entry['observed_not_expected'] = extra[:20]
            entry['observed_not_expected_count'] = len(extra)
        report['observed_all'].update(
            {f'{gid}::{k}': v for k, v in observed.items()})
        report['groups'][gid] = entry

    total_weight = sum(g['weight'] for g in report['groups'].values()) or 1
    earned = sum(g['weight'] for g in report['groups'].values() if g.get('all_passed'))
    report['reward'] = 0.0 if report['tampered'] else round(earned / total_weight, 6)
    report['groups_passed'] = sum(1 for g in report['groups'].values() if g.get('all_passed'))
    report['total_groups'] = len(report['groups'])
    report['expected_total'] = len(report['tests'])
    report['expected_passed'] = sum(1 for v in report['tests'].values() if v == 'passed')
    finish(report)


def finish(report, fatal=False):
    # Harbor parses reward.json and rejects any non-numeric value, so it must be a flat map of
    # numbers. The per-test verdicts, group detail and error list go to report.json instead.
    metrics = {'reward': float(report.get('reward', 0.0))}
    for key in ('groups_passed', 'total_groups', 'expected_passed', 'expected_total'):
        if key in report:
            metrics[key] = int(report[key])
    metrics['tampered'] = int(bool(report.get('tampered')))
    metrics['grader_errors'] = len(report.get('errors', []))

    (LOG / 'reward.txt').write_text(f"{metrics['reward']}\n")
    (LOG / 'reward.json').write_text(json.dumps(metrics, indent=2, sort_keys=True))
    (LOG / 'report.json').write_text(json.dumps(report, indent=2, sort_keys=True))
    print(json.dumps(metrics))
    sys.exit(0)                          # the verifier entry point always exits 0


if __name__ == '__main__':
    main()
