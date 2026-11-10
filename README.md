# WorkflowArena

**Benchmarking Executable Workflow Orchestration in LLM-Based Multi-Agent Systems**

WorkflowArena evaluates how agents organize and execute realistic, long-horizon work. It contains **145 tasks across eight domains and 17 task forms**, each with a **14,400-second shared agent budget**.

![WorkflowArena task coverage and representative deliverables](docs/assets/overview.png)

[Paper](https://arxiv.org/abs/2611.12856) · [Citation](#citation) · [Task index](benchmark/manifest.jsonl) · [Data and setup](#prepare-and-verify) · [Paper results](results/README.md) · [Paper figures](docs/figures.md) · [Evaluation](evaluation/README.md)

## Benchmark

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

Task IDs follow `WFA-<domain>-<number>`, starting at `001` in each domain. [Dataset documentation](docs/dataset.md) describes the task packages and their source records.

## Paper results

The paper evaluates nine models in 25 model-effort configurations. **Resolved rate** requires every task acceptance criterion to hold; **continuous score** credits partial progress on a 0-100 scale. Both Overall measures are the equal-weight mean across the eight domains.

The best Overall resolved rate is **36.95%**, attained by Claude Opus 5.5 at max effort. The best Overall continuous score is **80.21**, attained by Opus at high effort.

### Main experiment

The values below reproduce Overall from paper Tables 1 and 6. [Full domain tables and machine-readable results](results/main/README.md) preserve all 25 configurations.

| Model | Harness | Effort | Resolved (%) | Score |
| --- | --- | --- | ---: | ---: |
| Claude Opus 5.5 | Claude Code | max | **36.95** | 79.94 |
| Claude Opus 5.5 | Claude Code | high | 34.11 | **80.21** |
| Claude Opus 5.5 | Claude Code | xhigh | 33.23 | 78.77 |
| Claude Sonnet 5.5 | Claude Code | max | 33.21 | 73.11 |
| GPT-6 Astra | Codex | xhigh | 30.80 | 77.69 |
| GPT-6 Astra | Codex | high | 29.82 | 76.47 |
| GPT-6.1 Sol | Codex | xhigh | 29.50 | 77.52 |
| Claude Opus 5.5 | Claude Code | medium | 29.14 | 74.39 |
| GPT-6 Astra | Codex | medium | 28.11 | 76.12 |
| GPT-6.1 Sol | Codex | max | 28.04 | 76.50 |
| GPT-6 Astra | Codex | low | 27.80 | 74.02 |
| GPT-6.1 Sol | Codex | low | 27.59 | 76.32 |
| GPT-6 Astra | Codex | max | 27.34 | 77.29 |
| GPT-6.1 Sol | Codex | medium | 27.30 | 74.87 |
| GPT-6.1 Sol | Codex | high | 25.63 | 76.11 |
| Claude Sonnet 5.5 | Claude Code | high | 25.26 | 70.15 |
| Claude Sonnet 5.5 | Claude Code | xhigh | 23.24 | 70.00 |
| Claude Opus 5.5 | Claude Code | low | 22.02 | 72.44 |
| Claude Sonnet 5.5 | Claude Code | medium | 19.78 | 63.90 |
| Claude Sonnet 5.5 | Claude Code | low | 16.88 | 63.71 |
| Kimi K3.1 Pro | Claude Code | max | 16.48 | 62.73 |
| GPT-6 Luna | Codex | max | 13.32 | 55.44 |
| Doubao-Seed-Evolving | Claude Code | high | 10.84 | 48.66 |
| DeepSeek V4.1 Flash | Claude Code | max | 6.08 | 34.48 |
| GLM-5.3 Flash | Claude Code | max | 4.43 | 39.03 |

### Workflow transfer

On 32 challenging tasks, a source model authors the workflow and an execution model performs all task work. The source cannot edit the workspace. Scores below reproduce paper Table 2; Astra and Opus use max effort.

| Execution model | Self dynamic | Astra static | Astra dynamic | Opus static | Opus dynamic |
| --- | ---: | ---: | ---: | ---: | ---: |
| Kimi K3.1 Pro | 35.75 | 29.69 | 33.80 | 45.04 | **46.61** |
| GPT-6 Luna | 25.08 | 24.87 | 29.22 | **30.37** | 25.35 |
| Doubao-Seed-Evolving | 20.39 | 22.07 | 24.25 | **28.04** | 27.46 |
| DeepSeek V4.1 Flash | 18.37 | 12.85 | 17.69 | 21.79 | **25.24** |

[Transfer setup and results](results/transfer/README.md) · [Delegation, token use and cost figures](results/behavior/README.md)

![Resolved rate versus mean token consumption](docs/assets/resolved-vs-tokens.png)

## Repository structure

```text
benchmark/
  tasks/<task-id>/          # Task statements, metadata and solver environments
  manifest.jsonl           # 145 canonical tasks and evaluator locations
  assets.jsonl             # Publisher sources and materialization manifests
  provenance/              # Complete file hashes and source-specific notices
configs/                   # Task set, benchmark constants and paper configurations
evaluation/
  tasks/<task-id>/          # Scorers, acceptance rules, rubrics and references
  runtime/                 # Media image locks, build recipes and judge setup
results/                   # Paper-reported aggregate tables and analysis figures
docs/                      # Dataset documentation and paper figures
scripts/                   # Preparation, integrity checks and task assembly
tests/                     # Distribution and assembly checks
```

Each solver package contains `instruction.md`, `task.toml`, `metadata.json` and `environment/`. Its evaluator lives at the `evaluation_path` recorded in the task index. The [assembly script](scripts/materialize_tasks.py) combines them into the standard Harbor task layout, with evaluator files under `tests/`.

## Prepare and verify

Use Python 3.11 or newer, Git, and the [GitHub CLI](https://cli.github.com/). The frozen scientific inputs and Linux/amd64 media image archives in [release v1.0.0](https://github.com/Einsia/WorkflowArena/releases/tag/v1.0.0) work with the current repository layout:

```sh
git clone https://github.com/Einsia/WorkflowArena.git
cd WorkflowArena
mkdir -p ../WorkflowArena-assets/sci016-data
gh release download v1.0.0 --repo Einsia/WorkflowArena \
  --pattern '*.mat' --pattern SOURCE.json \
  --dir ../WorkflowArena-assets/sci016-data
gh release download v1.0.0 --repo Einsia/WorkflowArena \
  --pattern '*.tar.gz' --pattern SHA256SUMS --pattern README.md \
  --dir ../WorkflowArena-assets
(cd ../WorkflowArena-assets && shasum -a 256 -c SHA256SUMS)
python3 scripts/prepare_inputs.py
python3 scripts/verify_dataset.py
```

WFA-SCI-016 uses 33 frozen scientific input files in `WorkflowArena-assets/sci016-data/`. The preparation script verifies their hashes and links or copies them into the solver package. Other publisher-sourced inputs are reconstructed by their task-specific `environment/fetch/` or evaluator `fetch/` scripts. The first preparation requires network access. Large scientific CSV inputs are stored as deterministic gzip files and restored inside the task images.

To check prepared inputs without downloading:

```sh
python3 scripts/prepare_inputs.py --check-only
```

The [complete file manifest](benchmark/provenance/files.jsonl) records sizes and SHA-256 digests for the fully prepared distribution. The verifier rejects missing, changed and unmanifested files.

Load the frozen media images before building content and 3D task images:

```sh
python3 evaluation/runtime/media/images/load_images.py \
  --archive-dir ../WorkflowArena-assets
```

See [media runtime setup](evaluation/runtime/media/README.md) for image locks, recovered recipes and verifier-only judge configuration.

To assemble selected tasks for a Harbor-compatible runner:

```sh
python3 scripts/materialize_tasks.py \
  --tasks WFA-OPS-001 WFA-LAW-001 \
  --output ../WorkflowArena-harbor
```

Omit `--tasks` to assemble all 145 tasks. [Assembly documentation](docs/dataset.md#prepare-and-assemble) covers file verification, disk use and the resulting layout. Build each Dockerfile with its containing directory as the context.

## Evaluation and sources

Keep evaluator files separate from solver-visible inputs and follow each task's shared or separate verifier configuration. Absolute paths such as `/workspace` and `/tests` refer to task containers. [Evaluation documentation](evaluation/README.md) describes acceptance criteria and the solver/evaluator boundary.

Task source records distinguish original acquisition hashes from source-identity checks. Finance packages include `environment/public/SOURCE.json` records for all 154 supplied reports. Source-specific licenses and attribution accompany the inputs; see [source notices](NOTICE.md).

This repository contains task data, evaluation materials and paper-reported aggregates. Execution frameworks, per-task experimental records, participant submissions and development logs are outside this release.

## Citation

If you use WorkflowArena in your research, please cite [our paper](https://arxiv.org/abs/2611.12856):

```bibtex
@misc{jiang2026workflowarena,
  title = {WorkflowArena: Benchmarking Executable Workflow Orchestration in {LLM}-Based Multi-Agent Systems},
  author = {Zheng Jiang and Fang Niu and Bo Peng and Houde Qian and Wenyi Li and Deyao Hong and Mingju Gao and Yizhe Chi and Youjie Zheng and Kaisen Yang and Calvin Xiao and Lifeng Sun and Huan-ang Gao},
  year = {2026},
  eprint = {2611.12856},
  archivePrefix = {arXiv},
  url = {https://arxiv.org/abs/2611.12856}
}
```
