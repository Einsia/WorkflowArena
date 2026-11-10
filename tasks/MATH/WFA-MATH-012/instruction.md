> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.35.0`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `Poncelet/Transfer.lean` and newly added `.lean` files under `Poncelet/`, rebuilds `Poncelet.Transfer` in the grader's own clean copy and checks the statement and axioms of `f_add_smul_g`; changes to other existing files are ignored.

# Task: Poncelet's porism via translation on an elliptic curve

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.35.0`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `Poncelet/Transfer.lean`, replace the `sorry` with a complete proof of `f_add_smul_g`:

```lean
theorem f_add_smul_g [DecidableEq K] [CharZero K] (p : (elliptic cf).Point) (n : ℕ) :
    f cf (p + n • g cf) = (next cf)^[n] (f cf p)
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `Poncelet/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms f_add_smul_g`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Griffiths–Harris, On Cayley's explicit solution to Poncelet's porism (1978)

## Checks you may run

```sh
lake build
lake env lean Poncelet/Transfer.lean
```
