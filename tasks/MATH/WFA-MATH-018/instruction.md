> Your working directory is `/workspace`, i.e. the `workspace/` referred to below: a pinned mathlib4 source checkout, initialised as a git repository (start commit `start`). The Lean toolchain, the dependency packages and the prebuilt Mathlib cache are already installed, and `lake build Mathlib` has already been run; there is no network access at run time, so `lake exe cache get` is neither needed nor possible. Deliver your work by editing `/workspace/Mathlib/` and `/workspace/Mathlib.lean` directly. Grading collects only these two paths into the grader's own clean copy, where every file that already exists under `Mathlib/` in the start state is reset to its start-state content (edits to existing Mathlib files are discarded; only new files under `Mathlib/` and your `Mathlib.lean` are kept, and start-state import lines missing from your `Mathlib.lean` are re-added), then runs `lake build Mathlib` and checks the required declarations; changes to any other file are ignored.

# feat(NumberTheory/NumberField): proof of the Analytic Class Number Formula

You are working in a pinned mathlib4 checkout (`workspace/`; Lean toolchain pinned in
`lean-toolchain`, dependencies in `lake-manifest.json`; the prebuilt
Mathlib build is already installed). Develop the mathematics below as mathlib-quality Lean code.

## Goal

Let `K` be a number field. Define
```lean
def dedekindZeta (s : ℂ) :=
   LSeries (fun n ↦ Nat.card {I : Ideal (𝓞 K) // absNorm I = n}) s
```
and  
```lean
def residue : ℝ :=
   (2 ^ nrRealPlaces K * (2 * π) ^ nrComplexPlaces K * regulator K * classNumber K) /
     (torsionOrder K *  Real.sqrt |discr K|)
```
We prove:
```lean
theorem dedekindZeta_residue :
     Tendsto (fun s : ℝ ↦ (s - 1) * dedekindZeta K s) (𝓝[>] 1) (𝓝 (residue K))
```

This is a substantial development: in the original history it took 11 separate
contributions. Everything needed beyond the current library is yours to build.

## Required deliverables

After your work, each of the following constants must exist (anywhere under
`Mathlib/`, imported from `Mathlib.lean`) and have exactly this type, as printed
by `#check @name` (grading compares the elaborated types structurally, so notation
and binder names do not matter, but the statement must be the same):

```lean
NumberField.dedekindZeta :
  (K : Type u_1) → [inst : Field K] → [NumberField K] → ℂ → ℂ
```

```lean
NumberField.dedekindZeta_residue :
  (K : Type u_1) → [inst : Field K] → [NumberField K] → ℝ
```

```lean
NumberField.dedekindZeta_residue_def :
  ∀ (K : Type u_1) [inst : Field K] [inst_1 : NumberField K],
  NumberField.dedekindZeta_residue K =
    2 ^ NumberField.InfinitePlace.nrRealPlaces K * (2 * Real.pi) ^ NumberField.InfinitePlace.nrComplexPlaces K *
          NumberField.Units.regulator K *
        ↑(NumberField.classNumber K) /
      (↑(NumberField.Units.torsionOrder K) * √|↑(NumberField.discr K)|)
```

```lean
NumberField.dedekindZeta_residue_ne_zero :
  ∀ (K : Type u_1) [inst : Field K] [inst_1 : NumberField K],
  NumberField.dedekindZeta_residue K ≠ 0
```

```lean
NumberField.dedekindZeta_residue_pos :
  ∀ (K : Type u_1) [inst : Field K] [inst_1 : NumberField K],
  0 < NumberField.dedekindZeta_residue K
```

```lean
NumberField.tendsto_sub_one_mul_dedekindZeta_nhdsGT :
  ∀ (K : Type u_1) [inst : Field K] [inst_1 : NumberField K],
  Filter.Tendsto (fun s => (↑s - 1) * NumberField.dedekindZeta K ↑s) (nhdsWithin 1 (Set.Ioi 1))
    (nhds ↑(NumberField.dedekindZeta_residue K))
```

## Pinned reference definitions

The excerpts below, taken from the reference development, contain every pinned declaration (2
constants including the auxiliary ones Lean generates for them, such as constructors, recursors,
projections and `match_` functions). Reproduce these declarations exactly. Using a file with the same
path, imports and `variable`/`open` context is the safest way to get an identical elaborated value
(for example, instance resolution depends on the imports). `-- ...` marks omitted parts of the
reference file (other declarations and proofs, which you develop yourself).

### `Mathlib/NumberTheory/NumberField/DedekindZeta.lean`

```lean
import Mathlib.NumberTheory.LSeries.SumCoeff
import Mathlib.NumberTheory.NumberField.Ideal
import Mathlib.Algebra.BigOperators.Ring.Nat
-- ...
variable (K : Type*) [Field K] [NumberField K]
-- ...
noncomputable section
-- ...
open Filter Ideal NumberField.InfinitePlace NumberField.Units Topology nonZeroDivisors
-- ...
namespace NumberField
-- ...
open scoped Real

/--
The Dedekind zeta function of a number field. It is defined as the `L`-series with coefficients
the number of integral ideals of norm `n`.
-/
def dedekindZeta (s : ℂ) :=
  LSeries (fun n ↦ Nat.card {I : Ideal (𝓞 K) // absNorm I = n}) s

/--
The value of the residue at `s = 1` of the Dedekind zeta function, see
`NumberField.tendsto_sub_one_mul_dedekindZeta_nhdsGT`.
-/
def dedekindZeta_residue : ℝ :=
  (2 ^ nrRealPlaces K * (2 * π) ^ nrComplexPlaces K * regulator K * classNumber K) /
    (torsionOrder K *  Real.sqrt |discr K|)
```

## Rules

- No `sorry`, no new `axiom`/`opaque` tricks; standard axioms (`propext`,
  `Classical.choice`, `Quot.sound`) are fine.
- Existing library files are read-only: grading resets every start-state file under `Mathlib/` to
  its original content and keeps only your new files under `Mathlib/` plus your `Mathlib.lean`
  (start-state import lines missing from it are re-added). Put all of your work in new files and
  import them from `Mathlib.lean`; the whole library must build.
- Definitions are pinned: each required declaration that is not a theorem (definition, abbrev,
  instance, structure, class or inductive type), and each non-theorem declaration of the reference
  development that these or the required statements depend on, must exist under the same name with
  the same elaborated value as in the reference; they are shown under "Pinned reference definitions".
  Values are compared structurally (binder names ignored; proof subterms are not compared, so any
  proof works; for structures and inductive types the type, constructors and field types are compared).
- Apart from that, organise files, auxiliary definitions and lemmas, and the order of work as you
  see fit; the original file layout is not required.
