"""Deterministic answer grading for the versioned machine contract."""
import json
import math
import re
from collections import defaultdict

from algebra import equivalent, substitute
from certificates import certificate
from compatibility import normalize_submission, period_text, VERSION

GROUPS = {'scope': 10, 'classification': 30, 'bridges': 25,
          'policy': 20, 'counterfactuals': 10, 'evidence': 5}


def numeric(actual, expected, tol):
    return (type(actual) in (float, int) and math.isfinite(actual)
            and abs(actual - expected) <= tol + 1e-12)


def normalize_quote(text):
    return re.sub(r'[\s|]+', '', text).casefold()


def check(q, answer, expected_override=None):
    kind = q['kind']
    expected = q['expected'] if expected_override is None else expected_override
    if kind == 'number':
        return numeric(answer, expected, q['tolerance'])
    if kind == 'expression':
        return equivalent(answer, expected, q['symbols'])
    if kind == 'set':
        return (isinstance(answer, list) and all(isinstance(v, str) for v in answer)
                and len(answer) == len(set(answer)) and set(answer) == set(expected))
    if kind == 'tree':
        def same(a, e):
            if type(e) in (int, float):
                return numeric(a, e, q.get('tolerance', 1e-8))
            if isinstance(e, dict):
                return (isinstance(a, dict) and set(a) == set(e)
                        and all(same(a[k], e[k]) for k in e))
            if isinstance(e, list):
                if all(isinstance(x, str) for x in e):
                    return isinstance(a, list) and all(isinstance(x, str) for x in a) and len(a) == len(set(a)) and set(a) == set(e)
                return isinstance(a, list) and len(a) == len(e) and all(same(x, y) for x, y in zip(a, e))
            return type(a) is type(e) and a == e
        return same(answer, expected)
    if kind == 'evidence':
        if not isinstance(answer, dict) or set(answer) != {'file', 'table', 'row', 'quote'}:
            return False
        if any(answer[k] != expected[k] for k in ['file', 'table', 'row']):
            return False
        quote = answer['quote']
        if not isinstance(quote, str):
            return False
        # Require the entire source row, allowing whitespace and case changes.
        return normalize_quote(quote) == normalize_quote(expected['quote'])
    if kind == 'literal' and q['id'].endswith('/period') and isinstance(answer, str) and isinstance(expected, str):
        return period_text(answer) == period_text(expected)
    # String enums and booleans deliberately use strict JSON types.
    return type(answer) is type(expected) and answer == expected


def grade(spec, submission):
    accepted = {spec['contract_version']} | set(spec.get('accepted_submission_versions', []))
    if not isinstance(submission, dict) or submission.get('contract_version') not in accepted:
        return {'status': 'incompatible_contract', 'score': None, 'full_success': None,
                'reason': 'Use the versioned machine template; legacy free-form answers require an explicit lossless adapter.'}
    if (submission.get('task_id') != spec['task_id'] or not isinstance(submission.get('answers'), dict)
            or submission.get('profile_id','base') != spec.get('profile_id','base')):
        return {'status': 'invalid_submission', 'score': None, 'full_success': None}
    answers = submission['answers']
    known = {q['id'] for q in spec['questions']}
    if set(answers) - known:
        return {'status': 'invalid_submission', 'score': None, 'full_success': None,
                'reason': 'Unknown answer IDs', 'unknown_ids': sorted(set(answers) - known)}
    submission, normalized_ids, normalization_errors = normalize_submission(spec, submission)
    answers = submission['answers']
    diagnostics, root_results = [], defaultdict(list)
    for q in spec['questions']:
        try:
            if q['id'] in normalization_errors:
                raise ValueError(normalization_errors[q['id']])
            # Derived mathematical work is checked against the submitted models;
            # their source correctness is already owned by classification roots.
            # This prevents recharging a source/model error in every downstream pair.
            target = None
            if 'derive_pair' in q and all(isinstance(answers.get(k), str) for k in q['derive_pair']):
                a, b = (answers[k] for k in q['derive_pair'])
                target = '(' + a + ')-(' + b + ')'
            if 'derive_endpoint' in q:
                d=q['derive_endpoint']
                if isinstance(answers.get(d['model_id']),str):
                    target=substitute(answers[d['model_id']],d['point'])
            if 'derive_certificate' in q:
                d = q['derive_certificate']
                model_ids = d['model_ids']
                if all(isinstance(answers.get(k), str) for k in model_ids.values()):
                    expressions = {t: answers[k] for t, k in model_ids.items()}
                    target = certificate(expressions, d['params'], d['scenario'], d['alpha_max'])
            ok = q['id'] in answers and check(q, answers[q['id']], target)
            error = None
        except (ValueError, TypeError, SyntaxError, ZeroDivisionError, OverflowError, RecursionError) as exc:
            ok, error = False, type(exc).__name__
        root_results[q['root']].append(ok)
        if not ok:
            diagnostics.append({'id': q['id'], 'root': q['root'],
                                'reason': 'missing' if q['id'] not in answers else error or 'mismatch'})
    groups, roots = {}, {}
    for group, weight in GROUPS.items():
        group_roots = [r for r in spec['roots'] if r['group'] == group]
        if not group_roots:
            raise ValueError('incomplete spec: empty group ' + group)
        for root in group_roots:
            checks = root_results[root['id']]
            if not checks:
                raise ValueError('empty root')
            roots[root['id']] = {'passed': all(checks), 'group': group,
                                 'checks': len(checks), 'failed': checks.count(False),
                                 'points': weight / len(group_roots) if all(checks) else 0}
        points = sum(roots[r['id']]['points'] for r in group_roots)
        groups[group] = {'score': round(points, 8), 'maximum': weight,
                         'passed_roots': sum(roots[r['id']]['passed'] for r in group_roots),
                         'total_roots': len(group_roots)}
    score = sum(g['score'] for g in groups.values())
    critical = [r['id'] for r in spec['roots'] if r.get('critical') and not roots[r['id']]['passed']]
    return {'status': 'graded', 'task_id': spec['task_id'], 'contract_version': spec['contract_version'],
            'score': round(score, 8), 'full_success': all(root['passed'] for root in roots.values()),
            'groups': groups, 'roots': roots, 'failed_critical_roots': critical,
            'criteria_evaluated': len(spec['questions']), 'criteria_answered': len(answers),
            'diagnostics': diagnostics, 'llm_judge_used': False,
            'scorer_version': VERSION, 'normalized_answer_ids': normalized_ids,
            'normalization_errors': normalization_errors,
            'score_rule': 'Fixed root budgets, all checks within a root required; a root is charged once. No author severity adjustment.'}


def read_json(path):
    def pairs(items):
        out = {}
        for key, val in items:
            if key in out:
                raise ValueError('duplicate JSON key: ' + key)
            out[key] = val
        return out

    def invalid(value):
        raise ValueError('nonfinite JSON constant: ' + value)

    def finite_float(value):
        out=float(value)
        if not math.isfinite(out):
            raise ValueError('nonfinite JSON number')
        return out

    if path.stat().st_size > 30_000_000:
        raise ValueError('submission too large')
    return json.loads(path.read_text(), object_pairs_hook=pairs, parse_constant=invalid,
                      parse_float=finite_float)
