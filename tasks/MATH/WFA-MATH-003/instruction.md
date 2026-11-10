> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.30.0-rc2`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `ErgodicTheory/TwoSided/SplittingAssembly.lean` and newly added `.lean` files under `ErgodicTheory/`, rebuilds `ErgodicTheory.TwoSided.SplittingAssembly` in the grader's own clean copy and checks the statement and axioms of `ErgodicTheory.oseledets_splitting`; changes to other existing files are ignored.

# Task: Oseledets splitting for invertible ergodic matrix cocycles

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.30.0-rc2`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `ErgodicTheory/TwoSided/SplittingAssembly.lean`, replace the `sorry` with a complete proof of `ErgodicTheory.oseledets_splitting`:

```lean
theorem oseledets_splitting
    {μ : Measure X} [IsProbabilityMeasure μ] {T : X ≃ᵐ X}
    (hT : Ergodic T μ)
    (A : X → Matrix (Fin d) (Fin d) ℝ)
    (hA : ∀ x, (A x).det ≠ 0)
    (hAmeas : Measurable A)
    (hint : IntegrableLogNorm A μ)
    (hint' : IntegrableLogNorm (fun x => (A x)⁻¹) μ) :
    ∃ (k : ℕ) (lam : Fin k → ℝ)
      (E : Fin k → X → Submodule ℝ (EuclideanSpace ℝ (Fin d))),
      StrictAnti lam ∧
      (∀ i, MeasurableSubspace fun x => E i x) ∧
      ∀ᵐ x ∂μ,
        DirectSum.IsInternal (fun i => E i x) ∧
        (∀ i, E i x ≠ ⊥) ∧
        (∀ i, Submodule.map (Matrix.toEuclideanCLM (𝕜 := ℝ) (A x)).toLinearMap (E i x)
          = E i (T x)) ∧
        (∀ i, ∀ v ∈ E i x, v ≠ 0 →
          Tendsto
            (fun n : ℕ => (n : ℝ)⁻¹ *
              Real.log ‖Matrix.toEuclideanCLM (𝕜 := ℝ) (cocycle A T n x) v‖)
            atTop (𝓝 (lam i)) ∧
          Tendsto
            (fun n : ℕ => (n : ℝ)⁻¹ *
              Real.log ‖Matrix.toEuclideanCLM (𝕜 := ℝ)
                (cocycle A T n ((⇑T.symm)^[n] x))⁻¹ v‖)
            atTop (𝓝 (-lam i)))
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `ErgodicTheory/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms ErgodicTheory.oseledets_splitting`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Oseledets multiplicative ergodic theorem (two-sided version); e.g. Viana, Lectures on Lyapunov Exponents, Ch. 4

## Checks you may run

```sh
lake build
lake env lean ErgodicTheory/TwoSided/SplittingAssembly.lean
```
