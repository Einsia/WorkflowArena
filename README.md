# WorkflowArena

WorkflowArena contains 145 tasks across eight domains and 17 task forms. Each task has a 14,400-second agent budget.

| Domain | Tasks |
| --- | ---: |
| Software engineering (SWE) | 17 |
| Enterprise operations (OPS) | 18 |
| Scientific research (SCI) | 16 |
| Formal mathematics (MATH) | 24 |
| Finance and accounting (FIN) | 16 |
| Legal practice (LAW) | 22 |
| Content design (CDN) | 14 |
| 3D modeling and animation (3D) | 18 |

Task IDs follow `WFA-<domain>-<number>`, starting at `001` in each domain. The index is [tasks/manifest.jsonl](tasks/manifest.jsonl).

Each package under `tasks/<domain>/<task-id>/` contains:

- `instruction.md`: the task statement and required deliverables.
- `task.toml`: resource limits and environment/verifier configuration.
- `metadata.json`: canonical identity, domain, task form, title and source metadata.
- `environment/`: solver build context and supplied inputs.
- `tests/`: evaluator code, acceptance rules, rubrics and reference data.

Keep evaluator files separate from solver-visible inputs. Follow each task's configured shared or separate verifier environment. Absolute paths such as `/workspace` and `/tests` refer to the task container, not the dataset checkout.

## Prepare and verify

Use Python 3.11 or newer, Git, and the [GitHub CLI](https://cli.github.com/) for the commands below. Download the frozen scientific inputs and Linux/amd64 media image archives from [release v1.0.0](https://github.com/Einsia/WorkflowArena/releases/tag/v1.0.0):

```sh
git clone https://github.com/Einsia/WorkflowArena.git
cd WorkflowArena
git checkout v1.0.0
mkdir -p ../WorkflowArena-assets/sci016-data
gh release download v1.0.0 --repo Einsia/WorkflowArena \
  --pattern '*.mat' --pattern SOURCE.json \
  --dir ../WorkflowArena-assets/sci016-data
gh release download v1.0.0 --repo Einsia/WorkflowArena \
  --pattern '*.tar.gz' --pattern SHA256SUMS --pattern README.md \
  --dir ../WorkflowArena-assets
(cd ../WorkflowArena-assets && shasum -a 256 -c SHA256SUMS)
python3 tools/prepare_inputs.py
python3 tools/verify_dataset.py
```

WFA-SCI-016 has 33 original data files under `../WorkflowArena-assets/sci016-data/`; preparation verifies their hashes and links or copies them into the task. Keep this companion directory alongside the dataset for offline reuse. Other source files requiring direct publisher acquisition are excluded from Git and reconstructed by task-specific `environment/fetch/` scripts. The first preparation needs network access and downloads these sources; the final verifier checks their exact prepared bytes.

To check already prepared inputs without downloading:

```sh
python3 tools/prepare_inputs.py --check-only
```

The file manifest [provenance/files.jsonl](provenance/files.jsonl) records the complete prepared dataset, including SHA-256 digests and sizes. The verifier rejects missing, changed and unmanifested files. Large scientific CSV inputs are stored as deterministic gzip files and restored inside their task images.

Build each task's Dockerfile with its containing directory as the context. Use Linux/amd64 for the supplied media runtime. The two locked media image archives accompany this delivery in `../WorkflowArena-assets/`:

```sh
python3 runtime/media/images/load_images.py --archive-dir ../WorkflowArena-assets
```

The image locks, recovered recipes and judge setup are described in [runtime/media/README.md](runtime/media/README.md).

## Evaluation

Continuous scores are `100 * reward`; resolved rates use the paper's acceptance criteria. Scientific prediction tasks include fixed baseline contracts and coverage checks. Financial analysis requires every required root check. Media acceptance uses unrounded scores and all critical rubric items. An incomplete evaluator run is a grading error and must not be counted as a valid failed submission.

Task source records distinguish original acquisition hashes from source-identity checks. Finance packages contain `environment/public/SOURCE.json` records for all 154 supplied reports. Source-specific notices and credits accompany the corresponding inputs; see [NOTICE.md](NOTICE.md).

This delivery contains task data and evaluation tooling. Experimental runs, participant submissions, development logs and model-result summaries are outside the dataset. No GitHub publication is performed by the preparation tools.
