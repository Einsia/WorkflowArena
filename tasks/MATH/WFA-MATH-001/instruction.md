> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.35.0-rc2`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `Discretization/Infinite/NormDiscretization.lean` and newly added `.lean` files under `BasicResults/`, `Discretization/`, rebuilds `Discretization.Infinite.NormDiscretization` in the grader's own clean copy and checks the statement and axioms of `Discretization.Infinite.exists_discretization`; changes to other existing files are ignored.

# Task: Norm discretization in infinite dimensions via generalized BSS sparsification

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.35.0-rc2`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `Discretization/Infinite/NormDiscretization.lean`, replace the `sorry` with a complete proof of `Discretization.Infinite.exists_discretization`:

```lean
theorem exists_discretization [Nonempty ι] [TopologicalSpace.SeparableSpace H]
    [Nontrivial H] {Λ : ℝ} (hΛ : 0 < Λ) (hJΛ : J ≤ Λ • (1 : H →L[ℂ] H))
    (hJinj : ∀ v, J v = 0 → v = 0) {a : Ω → ι → ℂ} {b : Ω → H}
    (ha : ∀ k, MemLp (fun x => a x k) 2 μ) (hb : MemLp b 2 μ) (hI : (gram a μ).PosDef)
    (hgramb : ∫ x, rankOne ℂ (b x) (b x) ∂μ = J)
    {n : ℕ} (hmn : Fintype.card ι ≤ n) :
    ∃ (x : Fin n → Ω) (w : Fin n → ℝ), (∀ i, 0 < w i) ∧
      (∀ c : ι → ℂ, (1 - Real.sqrt ((Fintype.card ι - 1) / n)) ^ 2
            * ∫ y, ‖star c ⬝ᵥ a y‖ ^ 2 ∂μ
          ≤ ∑ i, w i * ‖star c ⬝ᵥ a (x i)‖ ^ 2) ∧
      (∀ u : H, ∑ i, w i * ‖⟪u, b (x i)⟫_ℂ‖ ^ 2
          ≤ (1 + Real.sqrt (((∫ y, ‖b y‖ ^ 2 ∂μ) / Λ - 1) / n)) ^ 2 * Λ * ‖u‖ ^ 2)
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `BasicResults/`, `Discretization/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms Discretization.Infinite.exists_discretization`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Batson–Spielman–Srivastava, Twice-Ramanujan sparsifiers (2012)

## Checks you may run

```sh
lake build
lake env lean Discretization/Infinite/NormDiscretization.lean
```
