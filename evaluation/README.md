# Evaluation materials

`tasks/<task-id>/` contains the original task verifier: `test.sh`, scoring code, acceptance rules, required test data, rubrics and reference answers. Separate verifier environments also include their Dockerfile. `runtime/media/` contains the locked media images and judge configuration.

## Solver and evaluator boundary

The solver-facing package is under `benchmark/tasks/<task-id>/`. Use `scripts/materialize_tasks.py` to assemble a Harbor-compatible task, placing evaluation materials under its `tests/` directory. The solver image build context is only `environment/`; do not mount the repository or evaluator files into the running solver.

139 tasks configure separate verifier environments. Six SWE subsystem tasks use a shared environment: finish the solver process before exposing the verifier files in that environment. Follow each task's artifact paths and verifier configuration. The distribution's assembly checks verify the filesystem layout; the evaluation harness must enforce runtime access restrictions.

## Scores and acceptance

Continuous scores are `100 * reward`. A task is resolved only when all domain-specific acceptance criteria hold. Overall resolved rate and Overall score give equal weight to each of the eight domains.

| Domain | Acceptance criteria |
| --- | --- |
| SWE | Required functionality, build and import checks, expected test coverage and integrity checks pass; subsystem tasks also preserve previously passing behaviors and have no unresolved grader errors. |
| OPS | Business-goal accuracy ≥90%, process accuracy ≥90%, and all constraint checks pass, with each dimension using its own denominator. |
| SCI | Prediction submissions cover the required targets and meet the fixed task-specific reference baseline; reproduction tasks meet every numerical tolerance and provide required code and execution evidence. |
| MATH | Lean builds; required declaration types, permitted axioms, dependencies and pinned definitions satisfy the contract. |
| FIN | Peer-analysis tasks pass every required root check; consolidation tasks meet native full-success, branch, aggregate and consistency checks. |
| LAW | Contract extraction ≥90% and aggregation correctness ≥75%; case adjudication meets required legal, sentencing and consistency criteria. |
| CDN | Document/presentation score ≥75 or video score ≥90, with all critical rubric items satisfied. |
| 3D | Score ≥80 and all critical rubric items satisfied. |

Thresholds use unrounded scores. An incomplete evaluator run is a grading error and must not be treated as a valid failed submission. Required verifier references and runtime health-check fixtures are evaluation dependencies.

Content and 3D rubric grading uses Gemini-3.8-Flash. Configure credentials only in the verifier, following [media runtime setup](runtime/media/README.md).
