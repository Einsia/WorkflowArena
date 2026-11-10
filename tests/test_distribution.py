"""Exercise package assembly boundaries without running task or model code."""
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('materialize_tasks', Path(__file__).resolve().parents[1] / 'scripts/materialize_tasks.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DistributionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'dataset'
        self.output = Path(self.temp.name) / 'assembled'
        self.task_id = 'WFA-OPS-001'
        self.task = 'benchmark/tasks/' + self.task_id
        self.evaluator = 'evaluation/tasks/' + self.task_id
        files = {self.task + '/instruction.md': 'Public task', self.task + '/task.toml': 'schema_version = "1.4"\n', self.task + '/environment/input.txt': 'Public input', self.evaluator + '/test.sh': '#!/bin/sh\nexit 0\n', self.evaluator + '/reference.json': '{"gold": 42}'}
        records = []
        for name, value in files.items():
            p = self.root / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(value)
            records.append({'path': name, 'bytes': p.stat().st_size, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest()})
        (self.root / 'benchmark/manifest.jsonl').write_text(json.dumps({'task_id': self.task_id, 'path': self.task, 'evaluation_path': self.evaluator}) + '\n')
        (self.root / 'benchmark/provenance').mkdir()
        (self.root / 'benchmark/provenance/files.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in records))

    def test_assembly_keeps_evaluator_out_of_solver_context(self):
        result = module.materialize(self.root, self.output)
        self.assertEqual(result['tasks'], 1)
        package = self.output / self.task_id
        self.assertTrue((package / 'tests/reference.json').is_file())
        self.assertEqual([p.name for p in (package / 'environment').iterdir()], ['input.txt'])
        (package / 'environment/input.txt').write_text('Changed by caller')
        self.assertEqual((self.root / self.task / 'environment/input.txt').read_text(), 'Public input')

    def test_missing_reference_fails_before_creating_output(self):
        (self.root / self.evaluator / 'reference.json').unlink()
        with self.assertRaises(ValueError):
            module.materialize(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_unmanifested_answer_in_solver_package_is_rejected(self):
        (self.root / self.task / 'environment/answer.json').write_text('{"gold": 42}')
        with self.assertRaises(ValueError):
            module.materialize(self.root, self.output)
        self.assertFalse(self.output.exists())

    def test_rejects_unknown_tasks_and_output_inside_source(self):
        with self.assertRaises(ValueError):
            module.materialize(self.root, self.output, ['WFA-OPS-999'])
        with self.assertRaises(ValueError):
            module.materialize(self.root, self.root / 'output')

    def test_dry_run_and_existing_output(self):
        module.materialize(self.root, self.output, check_only=True)
        self.assertFalse(self.output.exists())
        module.materialize(self.root, self.output)
        with self.assertRaises(FileExistsError):
            module.materialize(self.root, self.output)


if __name__ == '__main__':
    unittest.main()
