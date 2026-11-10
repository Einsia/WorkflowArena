> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.35.0-rc2`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `BasicResults/John.lean` and newly added `.lean` files under `BasicResults/`, rebuilds `BasicResults.John` in the grader's own clean copy and checks the statement and axioms of `John.exists_projection_ker`; changes to other existing files are ignored.

# Task: Bounded projections onto finite-codimensional closed subspaces

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.35.0-rc2`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `BasicResults/John.lean`, replace the `sorry` with a complete proof of `John.exists_projection_ker`:

```lean
theorem exists_projection_ker {X : Type u} [NormedAddCommGroup X] [NormedSpace 𝕜 X]
    (M : Submodule 𝕜 X) [IsClosed (M : Set X)] [FiniteDimensional 𝕜 (X ⧸ M)]
    {ε : ℝ} (hε : 0 < ε) :
    ∃ P : X →L[𝕜] X, P.comp P = P ∧ LinearMap.ker (P : X →ₗ[𝕜] X) = M ∧
      ‖P‖ ≤ Real.sqrt (Module.finrank 𝕜 (X ⧸ M)) + ε
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `BasicResults/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms John.exists_projection_ker`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: John's theorem / Kadec–Snobar-type projection bounds; Pietsch, Operator Ideals

## Checks you may run

```sh
lake build
lake env lean BasicResults/John.lean
```
