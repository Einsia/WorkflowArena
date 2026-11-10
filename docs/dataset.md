# Dataset and repository layout

WorkflowArena contains 145 tasks across eight domains and 17 task forms. Every task has a 14,400-second agent budget. Task IDs are `WFA-<domain>-<number>`, starting at `001` within each domain.

| Directory | Contents |
| --- | --- |
| `benchmark/tasks/<task-id>/` | Task statement, metadata, task configuration, solver Docker context and public inputs |
| `benchmark/manifest.jsonl` | Canonical IDs, domain, task form and solver/evaluator package paths |
| `benchmark/assets.jsonl` | Publisher sources, fetch manifests and prepared input destinations |
| `benchmark/provenance/` | Complete file hashes and source-specific license records |
| `configs/` | Frozen task set, benchmark constants and the paper's 25 model configurations |
| `evaluation/tasks/<task-id>/` | Verifier entry point, evaluator Docker context, tests, rubrics and references |
| `evaluation/runtime/` | Shared media image locks, recovered build recipes and judge setup |
| `results/` | Paper-reported aggregate tables and analysis figures |
| `docs/` | Dataset documentation, original paper figures and figure source hashes |
| `scripts/` | Input preparation, integrity checks and Harbor package assembly |
| `tests/` | Distribution and assembly boundary checks |

A solver package contains `instruction.md`, `task.toml`, `metadata.json` and `environment/`. Its evaluator is identified by `evaluation_path` in the manifest. Evaluator source materials are public in this repository, but must be withheld from the solver during task execution.

## Prepare and assemble

First download the companion assets and run the preparation and verification commands in the root README. To assemble one or more complete Harbor task packages outside this checkout:

```sh
python3 scripts/materialize_tasks.py \
  --tasks WFA-OPS-001 WFA-LAW-001 \
  --output ../WorkflowArena-harbor
```

Omit `--tasks` to assemble all 145 packages. Add `--check-only` to validate the selected packages without copying them. The script verifies every selected file against the SHA-256 manifest before writing, rejects an existing task destination, and copies files so downstream edits cannot modify the source release. Full assembly requires additional disk space for the prepared dataset.

The assembled layout is:

```text
WorkflowArena-harbor/<task-id>/
  instruction.md
  metadata.json
  task.toml
  environment/
  tests/
```

Build each Dockerfile using its own containing directory as the build context. Follow `task.toml` for shared versus separate verifier environments and artifact transfer. Preparation and grading are outside the agent's 14,400-second budget. See [evaluation](../evaluation/README.md) for the separation requirements.

## Versioned data

The frozen `v1.0.0` companion assets are compatible with the current repository layout. Use the commands in the current root README for this checkout. The `v1.0.0` Git tag preserves the original directory layout and its matching commands.

The file manifest describes the fully prepared distribution, including publisher-fetched files omitted from Git. `scripts/prepare_inputs.py` restores these inputs and checks their frozen hashes. `scripts/verify_dataset.py` checks task identities, counts, budgets, package boundaries and all manifested file bytes.

Source-specific licenses and credits accompany the relevant material; see [source notices](../NOTICE.md). The OPS license ledger applies to the OPS sources it identifies. It is not a blanket license for all 145 tasks.
