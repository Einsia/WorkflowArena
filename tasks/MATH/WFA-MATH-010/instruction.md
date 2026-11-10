> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.36.0-rc1`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `PFR/WeakPFR.lean` and newly added `.lean` files under `PFR/`, rebuilds `PFR.WeakPFR` in the grader's own clean copy and checks the statement and axioms of `weak_PFR_int_sumset`; changes to other existing files are ignored.

# Task: Weak PFR over the integers

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.36.0-rc1`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `PFR/WeakPFR.lean`, replace the `sorry` with a complete proof of `weak_PFR_int_sumset`:

```lean
theorem weak_PFR_int_sumset
    {G : Type*} [AddCommGroup G] [Module.Free ℤ G] [Module.Finite ℤ G]
    {A : Set G} (hA : A.Finite) (hnA : A.Nonempty) {K : ℝ}
    (hAK : Nat.card (A + A) ≤ K * Nat.card A) :
    ∃ A' ⊆ A, Nat.card A' ≥ K ^ (-34 : ℝ) * Nat.card A ∧
      AffineSpace.finrank ℤ A' ≤ (80 / log 2) * log K
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `PFR/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms weak_PFR_int_sumset`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Gowers–Green–Manners–Tao, On a conjecture of Marton, arXiv:2311.05762, Theorem 1.3

## Checks you may run

```sh
lake build
lake env lean PFR/WeakPFR.lean
```
