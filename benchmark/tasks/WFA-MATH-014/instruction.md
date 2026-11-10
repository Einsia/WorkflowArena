> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.35.0-rc2`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `SNumbers/MaxDifference.lean` and newly added `.lean` files under `BasicResults/`, `SNumbers/`, rebuilds `SNumbers.MaxDifference` in the grader's own clean copy and checks the statement and axioms of `SNumbers.max_gelfandNumber_kolmogorovNumber_le_e_mul_bernsteinNumber`; changes to other existing files are ignored.

# Task: Gelfand and Kolmogorov numbers bounded by Bernstein numbers

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.35.0-rc2`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `SNumbers/MaxDifference.lean`, replace the `sorry` with a complete proof of `SNumbers.max_gelfandNumber_kolmogorovNumber_le_e_mul_bernsteinNumber`:

```lean
theorem max_gelfandNumber_kolmogorovNumber_le_e_mul_bernsteinNumber
    (S : X →L[𝕜] Y) (n : ℕ) :
    max (gelfandNumber S n) (kolmogorovNumber S n)
      ≤ Real.exp 1 * ((n : ℝ) + 1) * bernsteinNumber S n
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `BasicResults/`, `SNumbers/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms SNumbers.max_gelfandNumber_kolmogorovNumber_le_e_mul_bernsteinNumber`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Pietsch, s-numbers of operators; Ullrich et al. (Lean-SNumbers blueprint)

## Checks you may run

```sh
lake build
lake env lean SNumbers/MaxDifference.lean
```
