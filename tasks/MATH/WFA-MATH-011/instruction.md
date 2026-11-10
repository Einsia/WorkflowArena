> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.35.0`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `PrimeNumberTheoremAnd/StrongPNT.lean` and newly added `.lean` files under `PrimeNumberTheoremAnd/`, rebuilds `PrimeNumberTheoremAnd.StrongPNT` in the grader's own clean copy and checks the statement and axioms of `StrongPNT`; changes to other existing files are ignored.

# Task: Prime number theorem with classical error term

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.35.0`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `PrimeNumberTheoremAnd/StrongPNT.lean`, replace the `sorry` with a complete proof of `StrongPNT`:

```lean
theorem StrongPNT : ∃ c > 0,
    (ψ - id) =O[atTop]
      fun (x : ℝ) ↦ x * Real.exp (-c * (Real.log x) ^ ((1 : ℝ) / 2))
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `PrimeNumberTheoremAnd/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms StrongPNT`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: de la Vallée Poussin zero-free region; Montgomery–Vaughan, Multiplicative Number Theory I, §6

## Checks you may run

```sh
lake build
lake env lean PrimeNumberTheoremAnd/StrongPNT.lean
```
