> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.36.0-rc1`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `PFR/RhoFunctional.lean` and newly added `.lean` files under `PFR/`, rebuilds `PFR.RhoFunctional` in the grader's own clean copy and checks the statement and axioms of `better_PFR_conjecture`; changes to other existing files are ignored.

# Task: Improved polynomial Freiman–Ruzsa constant via the rho functional

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.36.0-rc1`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `PFR/RhoFunctional.lean`, replace the `sorry` with a complete proof of `better_PFR_conjecture`:

```lean
theorem better_PFR_conjecture {G : Type*} [AddCommGroup G] [Module (ZMod 2) G]
    {A : Set G} {K : ℝ} (h₀A : A.Nonempty) (Afin : A.Finite)
    (hA : Nat.card (A + A) ≤ K * Nat.card A) :
    ∃ (H : Submodule (ZMod 2) G) (c : Set G), c.Finite ∧ (H : Set G).Finite ∧
      Nat.card c < 2 * K ^ 9 ∧ (H : Set G).ncard ≤ Nat.card A ∧ A ⊆ c + H
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `PFR/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms better_PFR_conjecture`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Jyun-Jie Liao, Improved exponent for Marton's conjecture in F_2^n, arXiv:2404.09639

## Checks you may run

```sh
lake build
lake env lean PFR/RhoFunctional.lean
```
