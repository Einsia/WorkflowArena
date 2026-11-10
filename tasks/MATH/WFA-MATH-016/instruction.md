> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.18.0`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `Zeta3Irrational/Basic.lean` and newly added `.lean` files under `Zeta3Irrational/`, rebuilds `Zeta3Irrational.Basic` in the grader's own clean copy and checks the statement and axioms of `zeta_3_irratoinal`; changes to other existing files are ignored.

# Task: Irrationality of ζ(3)

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.18.0`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `Zeta3Irrational/Basic.lean`, replace the `sorry` with a complete proof of `zeta_3_irratoinal`:

```lean
theorem zeta_3_irratoinal : ¬ ∃ r : ℚ , r = riemannZeta 3
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `Zeta3Irrational/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms zeta_3_irratoinal`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Beukers, A note on the irrationality of ζ(2) and ζ(3), Bull. LMS 11 (1979)

## Checks you may run

```sh
lake build
lake env lean Zeta3Irrational/Basic.lean
```
