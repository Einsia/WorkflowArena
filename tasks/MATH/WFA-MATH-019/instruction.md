> Your working directory is `/workspace`, i.e. the `workspace/` referred to below: a pinned mathlib4 source checkout, initialised as a git repository (start commit `start`). The Lean toolchain, the dependency packages and the prebuilt Mathlib cache are already installed, and `lake build Mathlib` has already been run; there is no network access at run time, so `lake exe cache get` is neither needed nor possible. Deliver your work by editing `/workspace/Mathlib/` and `/workspace/Mathlib.lean` directly. Grading collects only these two paths into the grader's own clean copy, where every file that already exists under `Mathlib/` in the start state is reset to its start-state content (edits to existing Mathlib files are discarded; only new files under `Mathlib/` and your `Mathlib.lean` are kept, and start-state import lines missing from your `Mathlib.lean` are re-added), then runs `lake build Mathlib` and checks the required declarations; changes to any other file are ignored.

# feat(ModelTheory): Presburger definability and semilinear sets

You are working in a pinned mathlib4 checkout (`workspace/`; Lean toolchain pinned in
`lean-toolchain`, dependencies in `lake-manifest.json`; the prebuilt
Mathlib build is already installed). Develop the mathematics below as mathlib-quality Lean code.

## Goal

This PR formalizes the classical result that Presburger definable sets are the same as semilinear sets. As an application of this result, we show that the graph of multiplication is not Presburger definable.

This is a substantial development: in the original history it took 27 separate
contributions. Everything needed beyond the current library is yours to build.

## Required deliverables

After your work, each of the following constants must exist (anywhere under
`Mathlib/`, imported from `Mathlib.lean`) and have exactly this type, as printed
by `#check @name` (grading compares the elaborated types structurally, so notation
and binder names do not matter, but the statement must be the same):

```lean
FirstOrder.Language.presburger :
  FirstOrder.Language
```

```lean
FirstOrder.Language.presburger.definable_iff_isSemilinearSet :
  ∀ {α : Type u_1} {A : Set ℕ} [Finite α]
  {s : Set (α → ℕ)}, Set.Definable A FirstOrder.Language.presburger s ↔ IsSemilinearSet s
```

```lean
FirstOrder.Language.presburger.definable₁_iff_ultimately_periodic :
  ∀ {A s : Set ℕ},
  Set.Definable₁ A FirstOrder.Language.presburger s ↔ ∃ k, ∃ p > 0, ∀ x ≥ k, x ∈ s ↔ x + p ∈ s
```

```lean
FirstOrder.Language.presburger.instStructure :
  {M : Type u_1} →
  [Zero M] → [One M] → [Add M] → FirstOrder.Language.Structure FirstOrder.Language.presburger M
```

```lean
FirstOrder.Language.presburger.isSemilinearSet_boundedFormula_realize :
  ∀ {α : Type u_1} {A : Set ℕ} [Finite α] {n : ℕ}
  (φ : FirstOrder.Language.BoundedFormula (FirstOrder.Language.withConstants FirstOrder.Language.presburger ↑A) α n),
  IsSemilinearSet {v | FirstOrder.Language.BoundedFormula.Realize φ (v ∘ Sum.inl) (v ∘ Sum.inr)}
```

```lean
FirstOrder.Language.presburger.isSemilinearSet_formula_realize_semilinear :
  ∀ {α : Type u_1} {A : Set ℕ} [Finite α]
  (φ : FirstOrder.Language.Formula (FirstOrder.Language.withConstants FirstOrder.Language.presburger ↑A) α),
  IsSemilinearSet (setOf (FirstOrder.Language.Formula.Realize φ))
```

```lean
FirstOrder.Language.presburger.mul_not_definable :
  ∀ {A : Set ℕ},
  ¬Set.Definable A FirstOrder.Language.presburger {v | v 0 = v 1 * v 2}
```

```lean
FirstOrder.Language.presburger.term_realize_eq_add_dotProduct :
  ∀ {α : Type u_1} {A : Set ℕ} [inst : Fintype α]
  (t : FirstOrder.Language.Term (FirstOrder.Language.withConstants FirstOrder.Language.presburger ↑A) α),
  ∃ k u, ∀ (v : α → ℕ), FirstOrder.Language.Term.realize v t = k + u ⬝ᵥ v
```

```lean
IsLinearSet :
  {M : Type u_1} → [AddCommMonoid M] → Set M → Prop
```

```lean
IsLinearSet.definable :
  ∀ {α : Type u_1} {s : Set (α → ℕ)} {A : Set ℕ} [Finite α],
  IsLinearSet s → Set.Definable A FirstOrder.Language.presburger s
```

```lean
IsProperLinearSet :
  {M : Type u_1} → [AddCommMonoid M] → Set M → Prop
```

```lean
IsProperSemilinearSet :
  {M : Type u_1} → [AddCommMonoid M] → Set M → Prop
```

```lean
IsSemilinearSet :
  {M : Type u_1} → [AddCommMonoid M] → Set M → Prop
```

```lean
IsSemilinearSet.definable :
  ∀ {α : Type u_1} {s : Set (α → ℕ)} {A : Set ℕ} [Finite α],
  IsSemilinearSet s → Set.Definable A FirstOrder.Language.presburger s
```

```lean
Nat.isSemilinearSet_iff_ultimately_periodic :
  ∀ {s : Set ℕ},
  IsSemilinearSet s ↔ ∃ k, ∃ p > 0, ∀ x ≥ k, x ∈ s ↔ x + p ∈ s
```

```lean
isProperSemilinearSet_iff :
  ∀ {M : Type u_1} [inst : AddCommMonoid M] {s : Set M},
  IsProperSemilinearSet s ↔ ∃ S, (∀ t ∈ S, IsProperLinearSet t) ∧ s = ⋃₀ ↑S
```

```lean
isSemilinearSet_iff :
  ∀ {M : Type u_1} [inst : AddCommMonoid M] {s : Set M},
  IsSemilinearSet s ↔ ∃ S, (∀ t ∈ S, IsLinearSet t) ∧ s = ⋃₀ ↑S
```

## Pinned reference definitions

The excerpts below, taken from the reference development, contain every pinned declaration (14
constants including the auxiliary ones Lean generates for them, such as constructors, recursors,
projections and `match_` functions). Reproduce these declarations exactly. Using a file with the same
path, imports and `variable`/`open` context is the safest way to get an identical elaborated value
(for example, instance resolution depends on the imports). `-- ...` marks omitted parts of the
reference file (other declarations and proofs, which you develop yourself).

### `Mathlib/ModelTheory/Arithmetic/Presburger/Basic.lean`

```lean
module
-- ...
public import Mathlib.Algebra.Group.Basic
public import Mathlib.Algebra.Module.NatInt
public import Mathlib.ModelTheory.Semantics
-- ...
@[expose] public section
-- ...
variable {α : Type*}
-- ...
namespace FirstOrder

/-- The type of Presburger arithmetic functions, defined as (0, 1, +). -/
inductive presburgerFunc : ℕ → Type
  | zero : presburgerFunc 0
  | one : presburgerFunc 0
  | add : presburgerFunc 2
  deriving DecidableEq

/-- The language of Presburger arithmetic, defined as (0, 1, +). -/
def Language.presburger : Language :=
  { Functions := presburgerFunc
    Relations := fun _ => Empty }
  deriving IsAlgebraic
-- ...
namespace Language.presburger
-- ...
variable {t t₁ t₂ : presburger.Term α}
-- ...
variable {M : Type*} {v : α → M}
-- ...
section
-- ...
variable [Zero M] [One M] [Add M]

instance : presburger.Structure M where
  funMap
  | .zero, _ => 0
  | .one, v => 1
  | .add, v => v 0 + v 1
```

### `Mathlib/ModelTheory/Arithmetic/Presburger/Semilinear/Defs.lean`

```lean
module
-- ...
public import Mathlib.GroupTheory.Finiteness
public import Mathlib.LinearAlgebra.LinearIndependent.Defs
public import Mathlib.Algebra.Order.Group.Nat
-- ...
import Mathlib.Algebra.GCDMonoid.Finset
import Mathlib.Algebra.GCDMonoid.Nat
import Mathlib.LinearAlgebra.Dimension.Basic
-- ...
@[expose] public section
-- ...
variable {M N ι κ F : Type*} [AddCommMonoid M] [AddCommMonoid N]
  [FunLike F M N] [AddMonoidHomClass F M N] {a : M} {s s₁ s₂ : Set M}
-- ...
open Set Pointwise AddSubmonoid

/-- A set is linear if it is a coset of a finitely generated additive submonoid. -/
def IsLinearSet (s : Set M) : Prop :=
  ∃ (a : M) (t : Set M), t.Finite ∧ s = a +ᵥ (closure t : Set M)
-- ...

/-- A set is semilinear if it is a finite union of linear sets. -/
def IsSemilinearSet (s : Set M) : Prop :=
  ∃ (S : Set (Set M)), S.Finite ∧ (∀ t ∈ S, IsLinearSet t) ∧ s = ⋃₀ S
-- ...

/-- A linear set is proper if its submonoid generators (periods) are linearly independent. -/
def IsProperLinearSet (s : Set M) : Prop :=
  ∃ (a : M) (t : Set M), t.Finite ∧ LinearIndepOn ℕ id t ∧ s = a +ᵥ (closure t : Set M)
-- ...

/-- A semilinear set is proper if it is a finite union of proper linear sets. -/
def IsProperSemilinearSet (s : Set M) : Prop :=
  ∃ (S : Set (Set M)), S.Finite ∧ (∀ t ∈ S, IsProperLinearSet t) ∧ s = ⋃₀ S
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
