> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.36.0-rc1`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `PFR/ApproxHomPFR.lean` and newly added `.lean` files under `PFR/`, rebuilds `PFR.ApproxHomPFR` in the grader's own clean copy and checks the statement and axioms of `approx_hom_pfr'`; changes to other existing files are ignored.

# Task: Approximate homomorphisms on F_2^n are close to homomorphisms

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.36.0-rc1`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `PFR/ApproxHomPFR.lean`, replace the `sorry` with a complete proof of `approx_hom_pfr'`:

```lean
theorem approx_hom_pfr' [Finite G] (f : G → G') (K : ℝ) (hK : K > 0)
    (hf : K⁻¹ ≤ Finset.dens {x : G × G | f (x.1 + x.2) = f x.1 + f x.2}) :
    ∃ (φ'' : G →+ G'), Nat.card {x | f x = φ'' x} ≥ (Nat.card G / (2 ^ 144 * K ^ 122) - 1)/2
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `PFR/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms approx_hom_pfr'`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Gowers–Green–Manners–Tao, On a conjecture of Marton, arXiv:2311.05762, Corollary 1.5

## Checks you may run

```sh
lake build
lake env lean PFR/ApproxHomPFR.lean
```
