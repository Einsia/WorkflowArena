> Your working directory is `/workspace`, i.e. the `workspace/` referred to below: a pinned mathlib4 source checkout, initialised as a git repository (start commit `start`). The Lean toolchain, the dependency packages and the prebuilt Mathlib cache are already installed, and `lake build Mathlib` has already been run; there is no network access at run time, so `lake exe cache get` is neither needed nor possible. Deliver your work by editing `/workspace/Mathlib/` and `/workspace/Mathlib.lean` directly. Grading collects only these two paths into the grader's own clean copy, where every file that already exists under `Mathlib/` in the start state is reset to its start-state content (edits to existing Mathlib files are discarded; only new files under `Mathlib/` and your `Mathlib.lean` are kept, and start-state import lines missing from your `Mathlib.lean` are re-added), then runs `lake build Mathlib` and checks the required declarations; changes to any other file are ignored.

# feat(AlgebraicTopology/SimplicialSet): the pushout-product of a mono and an inner anodyne extension is an inner anodyne extension

You are working in a pinned mathlib4 checkout (`workspace/`; Lean toolchain pinned in
`lean-toolchain`, dependencies in `lake-manifest.json`; the prebuilt
Mathlib build is already installed). Develop the mathematics below as mathlib-quality Lean code.

## Goal

Formalize in mathlib: the pushout-product of a mono and an inner anodyne extension is an inner anodyne extension. The required deliverables below pin down the exact statements.

This is a substantial development: in the original history it took 5 separate
contributions. Everything needed beyond the current library is yours to build.

## Required deliverables

After your work, each of the following constants must exist (anywhere under
`Mathlib/`, imported from `Mathlib.lean`) and have exactly this type, as printed
by `#check @name` (grading compares the elaborated types structurally, so notation
and binder names do not matter, but the statement must be the same):

```lean
SSet.InnerFibration :
  {X Y : SSet} → (X ⟶ Y) → Prop
```

```lean
SSet.innerAnodyneExtensions :
  CategoryTheory.MorphismProperty SSet
```

```lean
SSet.innerAnodyneExtensions.whiskerLeft :
  ∀ {X Y : SSet} {f : X ⟶ Y},
  SSet.innerAnodyneExtensions f →
    ∀ (Z : SSet), SSet.innerAnodyneExtensions (CategoryTheory.MonoidalCategoryStruct.whiskerLeft Z f)
```

```lean
SSet.innerAnodyneExtensions.whiskerRight :
  ∀ {X Y : SSet} {f : X ⟶ Y},
  SSet.innerAnodyneExtensions f →
    ∀ (Z : SSet), SSet.innerAnodyneExtensions (CategoryTheory.MonoidalCategoryStruct.whiskerRight f Z)
```

```lean
SSet.innerAnodyneExtensions_pushoutObjObjι :
  ∀ {X₁ X₂ Y₁ Y₂ : SSet} {i : X₁ ⟶ Y₁} {j : X₂ ⟶ Y₂}
  (sq₁₂ : CategoryTheory.Functor.PushoutObjObj (CategoryTheory.MonoidalCategory.curriedTensor SSet) i j)
  [CategoryTheory.Mono i],
  SSet.innerAnodyneExtensions j → SSet.innerAnodyneExtensions (CategoryTheory.Functor.PushoutObjObj.ι sq₁₂)
```

```lean
SSet.innerAnodyneExtensions_pushoutObjObjι' :
  ∀ {X₁ X₂ Y₁ Y₂ : SSet} {i : X₁ ⟶ Y₁} {j : X₂ ⟶ Y₂}
  (sq₁₂ : CategoryTheory.Functor.PushoutObjObj (CategoryTheory.MonoidalCategory.curriedTensor SSet) i j)
  [CategoryTheory.Mono j],
  SSet.innerAnodyneExtensions i → SSet.innerAnodyneExtensions (CategoryTheory.Functor.PushoutObjObj.ι sq₁₂)
```

```lean
SSet.innerAnodyneExtensions_unionProd_ι :
  ∀ {X Y : SSet} (A : SSet.Subcomplex X) (B : SSet.Subcomplex Y),
  SSet.innerAnodyneExtensions (SSet.Subcomplex.ι B) →
    SSet.innerAnodyneExtensions (SSet.Subcomplex.ι (SSet.Subcomplex.unionProd A B))
```

```lean
SSet.innerAnodyneExtensions_unionProd_ι' :
  ∀ {X Y : SSet} (A : SSet.Subcomplex X) (B : SSet.Subcomplex Y),
  SSet.innerAnodyneExtensions (SSet.Subcomplex.ι A) →
    SSet.innerAnodyneExtensions (SSet.Subcomplex.ι (SSet.Subcomplex.unionProd A B))
```

```lean
SSet.innerFibration_pullbackObjObjπ :
  ∀ {X₁ Y₁ E B : SSet} {i : X₁ ⟶ Y₁} {p : E ⟶ B} [CategoryTheory.Mono i]
  [SSet.InnerFibration p] (sq₁₃ : CategoryTheory.Functor.PullbackObjObj CategoryTheory.MonoidalClosed.internalHom i p),
  SSet.InnerFibration (CategoryTheory.Functor.PullbackObjObj.π sq₁₃)
```

```lean
SSet.prodStdSimplex.innerAnodyneExtensions_unionProd_ι :
  ∀ {m : ℕ} (k : Fin (m + 2)),
  0 < k →
    k < Fin.last (m + 1) →
      ∀ (n : ℕ),
        SSet.innerAnodyneExtensions
          (SSet.Subcomplex.ι (SSet.Subcomplex.unionProd (SSet.horn (m + 1) k) (SSet.boundary n)))
```

## Pinned reference definitions

The excerpts below, taken from the reference development, contain every pinned declaration (6
constants including the auxiliary ones Lean generates for them, such as constructors, recursors,
projections and `match_` functions). Reproduce these declarations exactly. Using a file with the same
path, imports and `variable`/`open` context is the safest way to get an identical elaborated value
(for example, instance resolution depends on the imports). `-- ...` marks omitted parts of the
reference file (other declarations and proofs, which you develop yourself).

### `Mathlib/AlgebraicTopology/Quasicategory/InnerFibration.lean`

```lean
module
-- ...
public import Mathlib.AlgebraicTopology.Quasicategory.Basic
-- ...
public section
-- ...
open CategoryTheory MorphismProperty Simplicial Limits
-- ...
universe u
-- ...
namespace SSet

/-- The family of morphisms in `SSet` which consists of inner horn inclusions
`Λ[n, i].ι : Λ[n, i] ⟶ Δ[n]` (for `0 < i < n`). -/
inductive innerHornInclusions : MorphismProperty SSet.{u} where
  | intro {n : ℕ} (i : Fin (n + 3)) (h0 : 0 < i) (hn : i < Fin.last (n + 2)) :
    innerHornInclusions Λ[n + 2, i].ι
-- ...

/-- The inner fibrations are the morphisms which have the right lifting property
with respect to inner horn inclusions. -/
@[expose, kerodon 01BA]
def innerFibrations : MorphismProperty SSet.{u} := innerHornInclusions.rlp
deriving IsMultiplicative, RespectsIso, IsStableUnderBaseChange,
  IsStableUnderRetracts

/-- A morphism `q` satisfies `[InnerFibration q]` if it belongs to `innerFibrations`. -/
@[mk_iff]
class InnerFibration {X Y : SSet} (q : X ⟶ Y) : Prop where
  mem : innerFibrations q
```

### `Mathlib/AlgebraicTopology/SimplicialSet/AnodyneExtensions/Inner/Basic.lean`

```lean
module
-- ...
public import Mathlib.AlgebraicTopology.Quasicategory.InnerFibration
public import Mathlib.AlgebraicTopology.SimplicialSet.AnodyneExtensions.Basic
public import Mathlib.AlgebraicTopology.SimplicialSet.Presentable
public import Mathlib.CategoryTheory.SmallObject.Basic
-- ...
public section
-- ...
universe u
-- ...
open CategoryTheory HomotopicalAlgebra Simplicial
-- ...
namespace SSet
-- ...
open MorphismProperty

/-- In the category of simplicial sets, an *inner* anodyne extension is a morphism
that has the left lifting property with respect to *inner* fibrations, where
an inner fibration is a morphism that has the right lifting property with respect
to inner horn inclusions. -/
@[expose, kerodon 01BR]
def innerAnodyneExtensions : MorphismProperty SSet.{u} := innerFibrations.llp
deriving IsMultiplicative, RespectsIso, IsStableUnderCobaseChange,
  IsStableUnderRetracts, IsStableUnderTransfiniteComposition,
  IsStableUnderCoproducts
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
