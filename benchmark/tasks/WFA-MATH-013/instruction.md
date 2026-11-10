> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.26.0-rc2`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `RiemannHypothesisCurves/RiemannHypothesisHEC.lean` and newly added `.lean` files under `RiemannHypothesisCurves/`, rebuilds `RiemannHypothesisCurves.RiemannHypothesisHEC` in the grader's own clean copy and checks the statement and axioms of `riemann_hypothesis_hec`; changes to other existing files are ignored.

# Task: Riemann hypothesis for hyperelliptic curves over finite fields (Stepanov's method)

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.26.0-rc2`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `RiemannHypothesisCurves/RiemannHypothesisHEC.lean`, replace the `sorry` with a complete proof of `riemann_hypothesis_hec`:

```lean
theorem riemann_hypothesis_hec
    (F : Type*) [Field F] [Fintype F] [DecidableEq F]
    (f : Polynomial F) (q : ℕ)
    (hq : q = Fintype.card F)
    (hm3 : 3 ≤ f.natDegree)
    (hnsq : ¬ ∃ g : Polynomial (AlgebraicClosure F),
        g * g = Polynomial.map (algebraMap F (AlgebraicClosure F)) f)
    (hq6m : q > 6 * f.natDegree) :
    |((q : ℝ) - (Fintype.card {p : F × F // p.2 ^ 2 = Polynomial.eval p.1 f} : ℝ))|
      < (5 : ℝ) * (f.natDegree : ℝ) * Real.sqrt (q : ℝ)
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `RiemannHypothesisCurves/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms riemann_hypothesis_hec`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Stepanov's elementary method; e.g. Iwaniec–Kowalski, Analytic Number Theory, Ch. 11

## Checks you may run

```sh
lake build
lake env lean RiemannHypothesisCurves/RiemannHypothesisHEC.lean
```
