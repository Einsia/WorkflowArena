"""Paper acceptance rule; display rounding must not change a pass decision."""
import math

THRESHOLDS = {'CDN-DOC': 75, 'CDN-VIDEO': 90, '3D-SCENE': 80, '3D-FILM': 80}


def evaluate_acceptance(rubric, results, numerator, denominator, ungraded):
    form = rubric['release_acceptance']['task_form']
    threshold = THRESHOLDS[form]
    items = next(rubric[k] for k in ('items', 'criteria', 'judgments', 'decisions')
                 if isinstance(rubric.get(k), list) and rubric[k]
                 and isinstance(rubric[k][0], dict) and 'criterion_zh' in rubric[k][0])
    critical_failures = [item['id'] for item in items if item.get('critical')
                         and results.get(item['id'], {}).get('verdict') != 'pass']
    gate = results.get('_task_gate', {}).get('verdict')
    complete = ungraded == 0 and all(results.get(item['id'], {}).get('verdict')
                                     in ('pass', 'fail', 'na') for item in items)
    finite = math.isfinite(numerator) and math.isfinite(denominator) and denominator > 0
    passed = (complete and finite and not critical_failures and gate in (None, 'pass')
              and numerator * 100 >= threshold * denominator)
    return {'resolved': bool(passed), 'full_success': bool(passed),
            'pass_threshold': threshold, 'critical_failures': critical_failures}
