#!/usr/bin/env python3
"""Assemble selected solver and evaluator packages into Harbor task directories."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def materialize(root, output, task_ids=None, check_only=False):
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.is_relative_to(root) or root.is_relative_to(output):
        raise ValueError('Use an output directory outside the dataset checkout.')
    rows = [json.loads(line) for line in (root / 'benchmark/manifest.jsonl').read_text().splitlines()]
    known = {row['task_id'] for row in rows}
    if task_ids is not None and set(task_ids) - known:
        raise ValueError('Unknown task IDs: ' + ', '.join(sorted(set(task_ids) - known)))
    selected = [row for row in rows if task_ids is None or row['task_id'] in task_ids]
    records = [json.loads(line) for line in (root / 'benchmark/provenance/files.jsonl').read_text().splitlines()]
    checks = []
    for row in selected:
        task, evaluation = root / row['path'], root / row['evaluation_path']
        if not task.resolve().is_relative_to(root) or not evaluation.resolve().is_relative_to(root):
            raise ValueError('Package path escapes dataset.')
        if task.name != row['task_id'] or evaluation.name != row['task_id']:
            raise ValueError('Package directory and task identity differ.')
        if (task / 'tests').exists():
            raise ValueError('Evaluator files must be separate from the solver package.')
        if not (evaluation / 'test.sh').is_file():
            raise ValueError('Missing verifier entry point: ' + row['task_id'])
        if (output / row['task_id']).exists():
            raise FileExistsError('Destination already exists: ' + str(output / row['task_id']))
        prefixes = (row['path'] + '/', row['evaluation_path'] + '/')
        files = [r for r in records if r['path'].startswith(prefixes)]
        if not files:
            raise ValueError('Package is absent from the file manifest.')
        for record in files:
            p = root / record['path']
            if not p.resolve().is_relative_to(root) or not p.is_file() or p.stat().st_size != record['bytes'] or digest(p) != record['sha256']:
                raise ValueError('Missing or changed input; run prepare_inputs.py and verify_dataset.py: ' + record['path'])
        expected = {r['path'] for r in files}
        actual = {str(p.relative_to(root)) for folder in (task, evaluation) for p in folder.rglob('*') if p.is_file()}
        if actual != expected:
            raise ValueError('Unmanifested package files: ' + row['task_id'])
        checks.append({'task_id': row['task_id'], 'files': len(files), 'passed': True})
    # Validate the whole selection before creating any output. Copying prevents
    # downstream edits to an assembled package from changing the source release.
    if not check_only:
        output.mkdir(parents=True, exist_ok=True)
        for row in selected:
            destination = output / row['task_id']
            shutil.copytree(root / row['path'], destination)
            shutil.copytree(root / row['evaluation_path'], destination / 'tests')
    return {'tasks': len(selected), 'check_only': check_only, 'checks': checks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tasks', nargs='+')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    print(json.dumps(materialize(args.root, args.output, args.tasks, args.check_only), indent=2))
