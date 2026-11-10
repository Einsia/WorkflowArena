"""Public v3.1 representation rules; never reads expected answer values."""
import copy
import math
import re
from pathlib import PurePosixPath

VERSION = 'finance-machine-v3.1'
RULES = {
    'unknown_answer_ids': 'Reject the entire submission as in v3.0. Known-ID-only scoring is a separately labeled diagnostic, never the revision score.',
    'units': 'USD million, USD millions, USD_million, USD_millions: case/space/underscore insensitive; no rescaling.',
    'periods': 'Case and whitespace/underscore formatting only; no missing date, quarter, year or current/prior inference.',
    'evidence': 'Require file/table/row/full quote; text is an alias for quote if no conflicting quote. Accept unique manifest basename or workspace-relative path. Ignore extra metadata; conflicting core aliases fail. Pipes are table separators, not content.',
    'certificate_endpoints': 'Canonical {ranks,top_two}, or a complete issuer->numeric score map, or ordered nonempty tie groups. Derive ranks/top_two solely from submitted values/groups. A flat top-two list is incomplete and is not expanded.',
    'certificate_crossings': 'A/B and B/A denote the same equality root; conflicting duplicate pairs fail.',
    'certificate_extensions': 'Keep exact required certificate keys and issuer maps; never fill missing ranks, robust pairs, leave-one-out entries or dates. Optional endpoint values may be omitted only after they independently reproduce the supplied ranks/top_two.',
    'algebra': 'Exact polynomial cancellation after original denominator-domain checks; never cancel a policy-domain pole. Use reduced forms for derived endpoints and certificates.',
    'score': 'Original group weights and all-checks-per-root budgets retained. Missing or incorrect substantive answers still fail their roots.',
}


def period_text(value):
    return re.sub(r'[\s_]+', '', value).casefold() if isinstance(value, str) else value


def endpoint(value):
    if isinstance(value, dict) and {'ranks', 'top_two'} <= set(value):
        if set(value) == {'ranks', 'top_two', 'values'}:
            derived = endpoint(value['values'])
            if not isinstance(derived, dict) or derived.get('ranks') != value['ranks'] or set(derived.get('top_two', [])) != set(value['top_two']):
                raise ValueError('endpoint values disagree with ranks/top_two')
            return {k: value[k] for k in ('ranks', 'top_two')}
        return value
    if isinstance(value, dict) and value and all(type(v) in (int, float) and math.isfinite(v) for v in value.values()):
        ranks = {t: 1 + sum(x > y + 1e-10 for x in value.values()) for t, y in value.items()}
        return {'ranks': ranks, 'top_two': sorted(t for t in ranks if ranks[t] <= 2)}
    if isinstance(value, list) and value and all(isinstance(g, list) and g and all(isinstance(t, str) for t in g) for g in value):
        names = [t for g in value for t in g]
        if len(names) != len(set(names)):
            raise ValueError('duplicate issuer in endpoint tie groups')
        ranks, rank = {}, 1
        for group in value:
            ranks.update({t: rank for t in group})
            rank += len(group)
        return {'ranks': ranks, 'top_two': sorted(t for t in ranks if ranks[t] <= 2)}
    return value


def normalize_certificate(value):
    if not isinstance(value, dict):
        return value
    out = copy.deepcopy(value)
    if isinstance(out.get('endpoints'), dict):
        out['endpoints'] = {k: endpoint(v) for k, v in out['endpoints'].items()}
    if isinstance(out.get('crossings'), dict):
        pairs = {}
        for key, val in out['crossings'].items():
            names = key.split('/')
            canonical = '/'.join(sorted(names)) if len(names) == 2 else key
            if canonical in pairs and pairs[canonical] != val:
                raise ValueError('conflicting crossing pair aliases')
            pairs[canonical] = val
        out['crossings'] = pairs
    return out


def evidence_path(value, files):
    if not isinstance(value, str):
        return value
    candidate = value.removeprefix('/workspace/').removeprefix('./')
    if candidate in files:
        return candidate
    # Only a bare filename is an alias; arbitrary/wrong directory paths fail.
    if '/' not in candidate:
        matches = [p for p in files if PurePosixPath(p).name == candidate]
        if len(matches) == 1:
            return matches[0]
    return value


def normalize_answer(q, value, files):
    if q['id'] == 'scope/units' and isinstance(value, str):
        if period_text(value) in {'usdmillion', 'usdmillions'}:
            return 'USD million'
    if q['kind'] == 'evidence' and isinstance(value, dict):
        out = copy.deepcopy(value)
        for alias, canonical in [('text', 'quote'), ('table_index', 'table'), ('row_index', 'row')]:
            if alias in out:
                if canonical in out and out[canonical] != out[alias]:
                    raise ValueError('conflicting evidence aliases')
                out[canonical] = out[alias]
        if 'file' in out:
            out['file'] = evidence_path(out['file'], files)
        return {k: out[k] for k in ('file', 'table', 'row', 'quote') if k in out}
    if 'derive_certificate' in q:
        return normalize_certificate(value)
    return value


def normalize_submission(spec, submission):
    out = copy.deepcopy(submission)
    changes, errors = [], {}
    answers = out['answers']
    files = spec.get('input_files', [])
    for q in spec['questions']:
        key = q['id']
        if key not in answers:
            continue
        try:
            value = normalize_answer(q, answers[key], files)
        except (ValueError, TypeError, AttributeError) as exc:
            errors[key] = str(exc)
            continue
        if value != answers[key]:
            changes.append(key)
            answers[key] = value
    return out, changes, errors
