"""Harbor adapter for the frozen, deterministic finance-machine-v3 grader."""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import grade, read_json


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--submission', type=Path, default=Path('/workspace/output/submission.json'))
    parser.add_argument('--log-dir', type=Path, default=Path('/logs/verifier'))
    args = parser.parse_args()
    args.log_dir.mkdir(parents=True, exist_ok=True)
    # Broken verifier assets are infrastructure errors, never candidate zeroes.
    spec = read_json(Path(__file__).with_name('spec.json'))
    try:
        submission = read_json(args.submission)
    except (OSError, ValueError, UnicodeError) as exc:
        result = {'status': 'missing_or_invalid_submission', 'score': None,
                  'full_success': False, 'error_type': type(exc).__name__}
    else:
        result = grade(spec, submission)
    graded = result['status'] == 'graded'
    score = result['score'] if graded else 0.0
    rewards = {'reward': score / 100, 'score': score,
               'normalized_score': score / 100, 'partial_score': score / 100,
               'full_success': bool(result.get('full_success', False))}
    for group, data in result.get('groups', {}).items():
        rewards['score_' + group] = data['score']
    result.update(task_id=spec['task_id'], profile_id=spec['profile_id'], llm_judge_used=False)
    (args.log_dir / 'details.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    (args.log_dir / 'reward.json').write_text(json.dumps(rewards, indent=2) + '\n')
    (args.log_dir / 'reward.txt').write_text(str(score / 100) + '\n')
    print(json.dumps(rewards))


if __name__ == '__main__':
    main()
