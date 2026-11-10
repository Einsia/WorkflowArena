> The project is at `/workspace` (`/testbed` in the task text below is a symlink to it). The Lean toolchain `leanprover/lean4:v4.36.0-rc1`, the dependency packages and the prebuilt Mathlib cache are installed in the image, and the parts of the project that remain in the start state are already compiled; there is no network access at run time, so `lake` neither needs nor is able to download dependencies. Grading collects only the target file `PFR/TorsionEndgame.lean` and newly added `.lean` files under `PFR/`, rebuilds `PFR.TorsionEndgame` in the grader's own clean copy and checks the statement and axioms of `torsion_PFR`; changes to other existing files are ignored.

# Task: Marton's conjecture for groups of bounded torsion

You are given a Lean 4 project in `/testbed` (toolchain `leanprover/lean4:v4.36.0-rc1`; dependencies pinned in `lake-manifest.json`
and fetched by `lake`, not vendored). Parts of the project that lead to the result below have been removed.

## Goal

In `PFR/TorsionEndgame.lean`, replace the `sorry` with a complete proof of `torsion_PFR`:

```lean
theorem torsion_PFR {G : Type*} [AddCommGroup G] {m : ℕ} (hm : m ≥ 2)
    (htorsion : ∀ x : G, m • x = 0) {A : Set G} (Afin : A.Finite) {K : ℝ} (h₀A : A.Nonempty)
    (hA : Nat.card (A + A) ≤ K * A.ncard) :
    ∃ (H : AddSubgroup G) (c : Set G), c.Finite ∧ (H : Set G).Finite ∧
      Nat.card c < m * K ^ (256 * m ^ 3 + 1) ∧ (H : Set G).ncard ≤ A.ncard ∧ A ⊆ c + H
```

Keep the statement exactly as given (same name, binders, hypotheses and conclusion) and keep the file's existing
context (imports you need may be added).

## Rules

- You may add new Lean files under `PFR/` and import them where needed; grading ignores new files anywhere else.
- Do not modify `lean-toolchain`, `lake-manifest.json`, the lakefile, or existing declarations in other files.
- No `sorry`, `admit`, new `axiom`, `unsafe`, `implemented_by`/`extern`, or kernel-check-skipping options.
  Only `propext`, `Quot.sound`, `Classical.choice` may appear in `#print axioms torsion_PFR`.
- Final grading rebuilds your files in a clean copy of this repository and checks the statement and axioms
  independently; self-reported results are not used.
- Mathematical reference: Gowers–Green–Manners–Tao, Marton's conjecture in abelian groups with bounded torsion, arXiv:2404.02244

## Checks you may run

```sh
lake build
lake env lean PFR/TorsionEndgame.lean
```
