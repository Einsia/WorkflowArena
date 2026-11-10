> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.36.0-rc1`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `FltRegular/SmallNumbers/SmallNumbers.lean` and newly added `.lean` files under `FltRegular/`, rebuilds `FltRegular.SmallNumbers.SmallNumbers` in the grader's own clean copy and checks the statement and axioms of `FLT_small`; changes to other existing files are ignored.

# Task: Fermat's Last Theorem for exponents 3 to 10

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.36.0-rc1`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `FltRegular/SmallNumbers/SmallNumbers.lean`, replace the `sorry` with a complete proof of `FLT_small`:

```lean
theorem FLT_small {n : ℕ} (hn : n ∈ Finset.Icc 3 10) : FermatLastTheoremFor n
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `FltRegular/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms FLT_small`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Regular primes 3, 5, 7 via Kummer; reduction of composite exponents

## Checks you may run

```sh
lake build
lake env lean FltRegular/SmallNumbers/SmallNumbers.lean
```
