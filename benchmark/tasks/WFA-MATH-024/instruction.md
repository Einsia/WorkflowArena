> Your working directory is `/workspace`, i.e. the `workspace/` referred to below: a pinned mathlib4 source checkout, initialised as a git repository (start commit `start`). The Lean toolchain, the dependency packages and the prebuilt Mathlib cache are already installed, and `lake build Mathlib` has already been run; there is no network access at run time, so `lake exe cache get` is neither needed nor possible. Deliver your work by editing `/workspace/Mathlib/` and `/workspace/Mathlib.lean` directly. Grading collects only these two paths into the grader's own clean copy, where every file that already exists under `Mathlib/` in the start state is reset to its start-state content (edits to existing Mathlib files are discarded; only new files under `Mathlib/` and your `Mathlib.lean` are kept, and start-state import lines missing from your `Mathlib.lean` are re-added), then runs `lake build Mathlib` and checks the required declarations; changes to any other file are ignored.

# feat: symmetric monoidal structure on graded objects

You are working in a pinned mathlib4 checkout (`workspace/`; Lean toolchain pinned in
`lean-toolchain`, dependencies in `lake-manifest.json`; the prebuilt
Mathlib build is already installed). Develop the mathematics below as mathlib-quality Lean code.

## Goal

Formalize in mathlib: symmetric monoidal structure on graded objects. The required deliverables below pin down the exact statements.

This is a substantial development: in the original history it took 6 separate
contributions. Everything needed beyond the current library is yours to build.

## Required deliverables

After your work, each of the following constants must exist (anywhere under
`Mathlib/`, imported from `Mathlib.lean`) and have exactly this type, as printed
by `#check @name` (grading compares the elaborated types structurally, so notation
and binder names do not matter, but the statement must be the same):

```lean
CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst : CategoryTheory.Category C] →
        [inst : CategoryTheory.MonoidalCategory C] →
          CategoryTheory.GradedObject I C →
            CategoryTheory.GradedObject I C → CategoryTheory.GradedObject I C → Type (max (max (max u_1 u_2) u_3) u_1)
```

```lean
CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst : CategoryTheory.Category C] →
        [inst : CategoryTheory.MonoidalCategory C] →
          CategoryTheory.GradedObject I C →
            CategoryTheory.GradedObject I C → CategoryTheory.GradedObject I C → Type (max (max (max u_1 u_2) u_3) u_1)
```

```lean
CategoryTheory.GradedObject.HasTensor :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst : CategoryTheory.Category C] →
        [inst : CategoryTheory.MonoidalCategory C] →
          CategoryTheory.GradedObject I C → CategoryTheory.GradedObject I C → Prop
```

```lean
CategoryTheory.GradedObject.HasTensor₄ObjExt :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst : CategoryTheory.Category C] →
        [inst : CategoryTheory.MonoidalCategory C] →
          CategoryTheory.GradedObject I C →
            CategoryTheory.GradedObject I C →
              CategoryTheory.GradedObject I C → CategoryTheory.GradedObject I C → Type (max (max (max u_1 u_3) u_2) u_1)
```

```lean
CategoryTheory.GradedObject.Monoidal.associator :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst_1 : CategoryTheory.Category C] →
        [inst_2 : CategoryTheory.MonoidalCategory C] →
          (X₁ X₂ X₃ : CategoryTheory.GradedObject I C) →
            [inst_3 : CategoryTheory.GradedObject.HasTensor X₁ X₂] →
              [inst_4 :
                  CategoryTheory.GradedObject.HasTensor (CategoryTheory.GradedObject.Monoidal.tensorObj X₁ X₂) X₃] →
                [inst_5 : CategoryTheory.GradedObject.HasTensor X₂ X₃] →
                  [inst_6 :
                      CategoryTheory.GradedObject.HasTensor X₁ (CategoryTheory.GradedObject.Monoidal.tensorObj X₂ X₃)] →
                    [inst_7 : CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor X₁ X₂ X₃] →
                      [inst_8 : CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ X₁ X₂ X₃] →
                        CategoryTheory.GradedObject.Monoidal.tensorObj
                            (CategoryTheory.GradedObject.Monoidal.tensorObj X₁ X₂) X₃ ≅
                          CategoryTheory.GradedObject.Monoidal.tensorObj X₁
                            (CategoryTheory.GradedObject.Monoidal.tensorObj X₂ X₃)
```

```lean
CategoryTheory.GradedObject.Monoidal.braiding :
  {I : Type u_1} →
  [inst : AddCommMonoid I] →
    {C : Type u_2} →
      [inst_1 : CategoryTheory.Category C] →
        [inst_2 : CategoryTheory.MonoidalCategory C] →
          (X Y : CategoryTheory.GradedObject I C) →
            [inst_3 : CategoryTheory.BraidedCategory C] →
              [inst_4 : CategoryTheory.GradedObject.HasTensor X Y] →
                [inst_5 : CategoryTheory.GradedObject.HasTensor Y X] →
                  CategoryTheory.GradedObject.Monoidal.tensorObj X Y ≅
                    CategoryTheory.GradedObject.Monoidal.tensorObj Y X
```

```lean
CategoryTheory.GradedObject.Monoidal.braiding_naturality_left :
  ∀ {I : Type u_1} [inst : AddCommMonoid I]
  {C : Type u_2} [inst_1 : CategoryTheory.Category C] [inst_2 : CategoryTheory.MonoidalCategory C]
  {X Y : CategoryTheory.GradedObject I C} (Z : CategoryTheory.GradedObject I C)
  [inst_3 : CategoryTheory.BraidedCategory C] [inst_4 : CategoryTheory.GradedObject.HasTensor Y Z]
  [inst_5 : CategoryTheory.GradedObject.HasTensor Z Y] [inst_6 : CategoryTheory.GradedObject.HasTensor X Z]
  [inst_7 : CategoryTheory.GradedObject.HasTensor Z X] (f : X ⟶ Y),
  CategoryTheory.CategoryStruct.comp (CategoryTheory.GradedObject.Monoidal.whiskerRight f Z)
      (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding Y Z)) =
    CategoryTheory.CategoryStruct.comp (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding X Z))
      (CategoryTheory.GradedObject.Monoidal.whiskerLeft Z f)
```

```lean
CategoryTheory.GradedObject.Monoidal.braiding_naturality_right :
  ∀ {I : Type u_1} [inst : AddCommMonoid I]
  {C : Type u_2} [inst_1 : CategoryTheory.Category C] [inst_2 : CategoryTheory.MonoidalCategory C]
  (X : CategoryTheory.GradedObject I C) {Y Z : CategoryTheory.GradedObject I C}
  [inst_3 : CategoryTheory.BraidedCategory C] [inst_4 : CategoryTheory.GradedObject.HasTensor X Y]
  [inst_5 : CategoryTheory.GradedObject.HasTensor Y X] [inst_6 : CategoryTheory.GradedObject.HasTensor X Z]
  [inst_7 : CategoryTheory.GradedObject.HasTensor Z X] (f : Y ⟶ Z),
  CategoryTheory.CategoryStruct.comp (CategoryTheory.GradedObject.Monoidal.whiskerLeft X f)
      (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding X Z)) =
    CategoryTheory.CategoryStruct.comp (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding X Y))
      (CategoryTheory.GradedObject.Monoidal.whiskerRight f X)
```

```lean
CategoryTheory.GradedObject.Monoidal.hexagon_forward :
  ∀ {I : Type u_1} [inst : AddCommMonoid I] {C : Type u_2}
  [inst_1 : CategoryTheory.Category C] [inst_2 : CategoryTheory.MonoidalCategory C]
  (X Y Z : CategoryTheory.GradedObject I C) [inst_3 : CategoryTheory.BraidedCategory C]
  [inst_4 : CategoryTheory.GradedObject.HasTensor X Y] [inst_5 : CategoryTheory.GradedObject.HasTensor Y X]
  [inst_6 : CategoryTheory.GradedObject.HasTensor Y Z] [inst_7 : CategoryTheory.GradedObject.HasTensor Z X]
  [inst_8 : CategoryTheory.GradedObject.HasTensor X Z]
  [inst_9 : CategoryTheory.GradedObject.HasTensor (CategoryTheory.GradedObject.Monoidal.tensorObj X Y) Z]
  [inst_10 : CategoryTheory.GradedObject.HasTensor X (CategoryTheory.GradedObject.Monoidal.tensorObj Y Z)]
  [inst_11 : CategoryTheory.GradedObject.HasTensor (CategoryTheory.GradedObject.Monoidal.tensorObj Y Z) X]
  [inst_12 : CategoryTheory.GradedObject.HasTensor Y (CategoryTheory.GradedObject.Monoidal.tensorObj Z X)]
  [inst_13 : CategoryTheory.GradedObject.HasTensor (CategoryTheory.GradedObject.Monoidal.tensorObj Y X) Z]
  [inst_14 : CategoryTheory.GradedObject.HasTensor Y (CategoryTheory.GradedObject.Monoidal.tensorObj X Z)]
  [inst_15 : CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor X Y Z]
  [inst_16 : CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ X Y Z]
  [inst_17 : CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor Y Z X]
  [inst_18 : CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ Y Z X]
  [inst_19 : CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor Y X Z]
  [inst_20 : CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ Y X Z],
  CategoryTheory.CategoryStruct.comp (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.associator X Y Z))
      (CategoryTheory.CategoryStruct.comp
        (CategoryTheory.Iso.hom
          (CategoryTheory.GradedObject.Monoidal.braiding X (CategoryTheory.GradedObject.Monoidal.tensorObj Y Z)))
        (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.associator Y Z X))) =
    CategoryTheory.CategoryStruct.comp
      (CategoryTheory.GradedObject.Monoidal.whiskerRight
        (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding X Y)) Z)
      (CategoryTheory.CategoryStruct.comp
        (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.associator Y X Z))
        (CategoryTheory.GradedObject.Monoidal.whiskerLeft Y
          (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding X Z))))
```

```lean
CategoryTheory.GradedObject.Monoidal.hexagon_reverse :
  ∀ {I : Type u_1} [inst : AddCommMonoid I] {C : Type u_2}
  [inst_1 : CategoryTheory.Category C] [inst_2 : CategoryTheory.MonoidalCategory C]
  (X Y Z : CategoryTheory.GradedObject I C) [inst_3 : CategoryTheory.BraidedCategory C]
  [inst_4 : CategoryTheory.GradedObject.HasTensor X Y] [inst_5 : CategoryTheory.GradedObject.HasTensor Y Z]
  [inst_6 : CategoryTheory.GradedObject.HasTensor Z X] [inst_7 : CategoryTheory.GradedObject.HasTensor Z Y]
  [inst_8 : CategoryTheory.GradedObject.HasTensor X Z]
  [inst_9 : CategoryTheory.GradedObject.HasTensor (CategoryTheory.GradedObject.Monoidal.tensorObj X Y) Z]
  [inst_10 : CategoryTheory.GradedObject.HasTensor X (CategoryTheory.GradedObject.Monoidal.tensorObj Y Z)]
  [inst_11 : CategoryTheory.GradedObject.HasTensor Z (CategoryTheory.GradedObject.Monoidal.tensorObj X Y)]
  [inst_12 : CategoryTheory.GradedObject.HasTensor (CategoryTheory.GradedObject.Monoidal.tensorObj Z X) Y]
  [inst_13 : CategoryTheory.GradedObject.HasTensor X (CategoryTheory.GradedObject.Monoidal.tensorObj Z Y)]
  [inst_14 : CategoryTheory.GradedObject.HasTensor (CategoryTheory.GradedObject.Monoidal.tensorObj X Z) Y]
  [inst_15 : CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor X Y Z]
  [inst_16 : CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ X Y Z]
  [inst_17 : CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor Z X Y]
  [inst_18 : CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ Z X Y]
  [inst_19 : CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor X Z Y]
  [inst_20 : CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ X Z Y],
  CategoryTheory.CategoryStruct.comp (CategoryTheory.Iso.inv (CategoryTheory.GradedObject.Monoidal.associator X Y Z))
      (CategoryTheory.CategoryStruct.comp
        (CategoryTheory.Iso.hom
          (CategoryTheory.GradedObject.Monoidal.braiding (CategoryTheory.GradedObject.Monoidal.tensorObj X Y) Z))
        (CategoryTheory.Iso.inv (CategoryTheory.GradedObject.Monoidal.associator Z X Y))) =
    CategoryTheory.CategoryStruct.comp
      (CategoryTheory.GradedObject.Monoidal.whiskerLeft X
        (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding Y Z)))
      (CategoryTheory.CategoryStruct.comp
        (CategoryTheory.Iso.inv (CategoryTheory.GradedObject.Monoidal.associator X Z Y))
        (CategoryTheory.GradedObject.Monoidal.whiskerRight
          (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding X Z)) Y))
```

```lean
CategoryTheory.GradedObject.Monoidal.symmetry :
  ∀ {I : Type u_1} [inst : AddCommMonoid I] {C : Type u_2}
  [inst_1 : CategoryTheory.Category C] [inst_2 : CategoryTheory.MonoidalCategory C]
  (X Y : CategoryTheory.GradedObject I C) [inst_3 : CategoryTheory.SymmetricCategory C]
  [inst_4 : CategoryTheory.GradedObject.HasTensor X Y] [inst_5 : CategoryTheory.GradedObject.HasTensor Y X],
  CategoryTheory.CategoryStruct.comp (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding X Y))
      (CategoryTheory.Iso.hom (CategoryTheory.GradedObject.Monoidal.braiding Y X)) =
    CategoryTheory.CategoryStruct.id (CategoryTheory.GradedObject.Monoidal.tensorObj X Y)
```

```lean
CategoryTheory.GradedObject.Monoidal.tensorObj :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst_1 : CategoryTheory.Category C] →
        [inst_2 : CategoryTheory.MonoidalCategory C] →
          (X₁ X₂ : CategoryTheory.GradedObject I C) →
            [inst : CategoryTheory.GradedObject.HasTensor X₁ X₂] → CategoryTheory.GradedObject I C
```

```lean
CategoryTheory.GradedObject.Monoidal.whiskerLeft :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst_1 : CategoryTheory.Category C] →
        [inst_2 : CategoryTheory.MonoidalCategory C] →
          (X : CategoryTheory.GradedObject I C) →
            {Y₁ Y₂ : CategoryTheory.GradedObject I C} →
              (Y₁ ⟶ Y₂) →
                [inst_3 : CategoryTheory.GradedObject.HasTensor X Y₁] →
                  [inst_4 : CategoryTheory.GradedObject.HasTensor X Y₂] →
                    CategoryTheory.GradedObject.Monoidal.tensorObj X Y₁ ⟶
                      CategoryTheory.GradedObject.Monoidal.tensorObj X Y₂
```

```lean
CategoryTheory.GradedObject.Monoidal.whiskerRight :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst_1 : CategoryTheory.Category C] →
        [inst_2 : CategoryTheory.MonoidalCategory C] →
          {X₁ X₂ : CategoryTheory.GradedObject I C} →
            (X₁ ⟶ X₂) →
              (Y : CategoryTheory.GradedObject I C) →
                [inst_3 : CategoryTheory.GradedObject.HasTensor X₁ Y] →
                  [inst_4 : CategoryTheory.GradedObject.HasTensor X₂ Y] →
                    CategoryTheory.GradedObject.Monoidal.tensorObj X₁ Y ⟶
                      CategoryTheory.GradedObject.Monoidal.tensorObj X₂ Y
```

```lean
CategoryTheory.GradedObject.braidedCategory :
  {I : Type u_1} →
  [inst : AddCommMonoid I] →
    {C : Type u_2} →
      [inst_1 : CategoryTheory.Category C] →
        [inst_2 : CategoryTheory.MonoidalCategory C] →
          [inst_3 : ∀ (X₁ X₂ : CategoryTheory.GradedObject I C), CategoryTheory.GradedObject.HasTensor X₁ X₂] →
            [inst_4 :
                (X₁ X₂ X₃ : CategoryTheory.GradedObject I C) →
                  CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor X₁ X₂ X₃] →
              [inst_5 :
                  (X₁ X₂ X₃ : CategoryTheory.GradedObject I C) →
                    CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ X₁ X₂ X₃] →
                [inst_6 : DecidableEq I] →
                  [inst_7 : CategoryTheory.Limits.HasInitial C] →
                    [inst_8 :
                        (X₁ : C) →
                          CategoryTheory.Limits.PreservesColimit (CategoryTheory.Functor.empty C)
                            (Prefunctor.obj
                              (CategoryTheory.Functor.toPrefunctor (CategoryTheory.MonoidalCategory.curriedTensor C))
                              X₁)] →
                      [inst_9 :
                          (X₂ : C) →
                            CategoryTheory.Limits.PreservesColimit (CategoryTheory.Functor.empty C)
                              (Prefunctor.obj
                                (CategoryTheory.Functor.toPrefunctor
                                  (CategoryTheory.Functor.flip (CategoryTheory.MonoidalCategory.curriedTensor C)))
                                X₂)] →
                        [inst_10 :
                            (X₁ X₂ X₃ X₄ : CategoryTheory.GradedObject I C) →
                              CategoryTheory.GradedObject.HasTensor₄ObjExt X₁ X₂ X₃ X₄] →
                          [inst_11 : CategoryTheory.BraidedCategory C] →
                            CategoryTheory.BraidedCategory (CategoryTheory.GradedObject I C)
```

```lean
CategoryTheory.GradedObject.monoidalCategory :
  {I : Type u_1} →
  [inst : AddMonoid I] →
    {C : Type u_2} →
      [inst_1 : CategoryTheory.Category C] →
        [inst_2 : CategoryTheory.MonoidalCategory C] →
          [inst_3 : ∀ (X₁ X₂ : CategoryTheory.GradedObject I C), CategoryTheory.GradedObject.HasTensor X₁ X₂] →
            [inst_4 :
                (X₁ X₂ X₃ : CategoryTheory.GradedObject I C) →
                  CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor X₁ X₂ X₃] →
              [inst_5 :
                  (X₁ X₂ X₃ : CategoryTheory.GradedObject I C) →
                    CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ X₁ X₂ X₃] →
                [inst_6 : DecidableEq I] →
                  [inst_7 : CategoryTheory.Limits.HasInitial C] →
                    [inst_8 :
                        (X₁ : C) →
                          CategoryTheory.Limits.PreservesColimit (CategoryTheory.Functor.empty C)
                            (Prefunctor.obj
                              (CategoryTheory.Functor.toPrefunctor (CategoryTheory.MonoidalCategory.curriedTensor C))
                              X₁)] →
                      [inst_9 :
                          (X₂ : C) →
                            CategoryTheory.Limits.PreservesColimit (CategoryTheory.Functor.empty C)
                              (Prefunctor.obj
                                (CategoryTheory.Functor.toPrefunctor
                                  (CategoryTheory.Functor.flip (CategoryTheory.MonoidalCategory.curriedTensor C)))
                                X₂)] →
                        [inst :
                            (X₁ X₂ X₃ X₄ : CategoryTheory.GradedObject I C) →
                              CategoryTheory.GradedObject.HasTensor₄ObjExt X₁ X₂ X₃ X₄] →
                          CategoryTheory.MonoidalCategory (CategoryTheory.GradedObject I C)
```

```lean
CategoryTheory.GradedObject.symmetricCategory :
  {I : Type u_1} →
  [inst : AddCommMonoid I] →
    {C : Type u_2} →
      [inst_1 : CategoryTheory.Category C] →
        [inst_2 : CategoryTheory.MonoidalCategory C] →
          [inst_3 : ∀ (X₁ X₂ : CategoryTheory.GradedObject I C), CategoryTheory.GradedObject.HasTensor X₁ X₂] →
            [inst_4 :
                (X₁ X₂ X₃ : CategoryTheory.GradedObject I C) →
                  CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor X₁ X₂ X₃] →
              [inst_5 :
                  (X₁ X₂ X₃ : CategoryTheory.GradedObject I C) →
                    CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ X₁ X₂ X₃] →
                [inst_6 : DecidableEq I] →
                  [inst_7 : CategoryTheory.Limits.HasInitial C] →
                    [inst_8 :
                        (X₁ : C) →
                          CategoryTheory.Limits.PreservesColimit (CategoryTheory.Functor.empty C)
                            (Prefunctor.obj
                              (CategoryTheory.Functor.toPrefunctor (CategoryTheory.MonoidalCategory.curriedTensor C))
                              X₁)] →
                      [inst_9 :
                          (X₂ : C) →
                            CategoryTheory.Limits.PreservesColimit (CategoryTheory.Functor.empty C)
                              (Prefunctor.obj
                                (CategoryTheory.Functor.toPrefunctor
                                  (CategoryTheory.Functor.flip (CategoryTheory.MonoidalCategory.curriedTensor C)))
                                X₂)] →
                        [inst_10 :
                            (X₁ X₂ X₃ X₄ : CategoryTheory.GradedObject I C) →
                              CategoryTheory.GradedObject.HasTensor₄ObjExt X₁ X₂ X₃ X₄] →
                          [inst_11 : CategoryTheory.SymmetricCategory C] →
                            CategoryTheory.SymmetricCategory (CategoryTheory.GradedObject I C)
```

## Pinned reference definitions

The excerpts below, taken from the reference development, contain every pinned declaration (44
constants including the auxiliary ones Lean generates for them, such as constructors, recursors,
projections and `match_` functions). Reproduce these declarations exactly. Using a file with the same
path, imports and `variable`/`open` context is the safest way to get an identical elaborated value
(for example, instance resolution depends on the imports). `-- ...` marks omitted parts of the
reference file (other declarations and proofs, which you develop yourself).

### `Mathlib/CategoryTheory/GradedObject/Associator.lean`

```lean
import Mathlib.CategoryTheory.GradedObject.Trifunctor
-- ...
namespace CategoryTheory
-- ...
open Category
-- ...
namespace GradedObject
-- ...
variable {C₁ C₂ C₁₂ C₂₃ C₃ C₄ : Type*}
  [Category C₁] [Category C₂] [Category C₃] [Category C₄] [Category C₁₂] [Category C₂₃]
  {F₁₂ : C₁ ⥤ C₂ ⥤ C₁₂} {G : C₁₂ ⥤ C₃ ⥤ C₄}
  {F : C₁ ⥤ C₂₃ ⥤ C₄} {G₂₃ : C₂ ⥤ C₃ ⥤ C₂₃}
  (associator : bifunctorComp₁₂ F₁₂ G ≅ bifunctorComp₂₃ F G₂₃)
  {I₁ I₂ I₃ J : Type*} {r : I₁ × I₂ × I₃ → J}
  (ρ₁₂ : BifunctorComp₁₂IndexData r) (ρ₂₃ : BifunctorComp₂₃IndexData r)
  (X₁ : GradedObject I₁ C₁) (X₂ : GradedObject I₂ C₂) (X₃ : GradedObject I₃ C₃)
  [HasMap (((mapBifunctor F₁₂ I₁ I₂).obj X₁).obj X₂) ρ₁₂.p]
  [HasMap (((mapBifunctor G ρ₁₂.I₁₂ I₃).obj (mapBifunctorMapObj F₁₂ ρ₁₂.p X₁ X₂)).obj X₃) ρ₁₂.q]
  [HasMap (((mapBifunctor G₂₃ I₂ I₃).obj X₂).obj X₃) ρ₂₃.p]
  [HasMap (((mapBifunctor F I₁ ρ₂₃.I₂₃).obj X₁).obj (mapBifunctorMapObj G₂₃ ρ₂₃.p X₂ X₃)) ρ₂₃.q]
  [H₁₂ : HasGoodTrifunctor₁₂Obj F₁₂ G ρ₁₂ X₁ X₂ X₃]
  [H₂₃ : HasGoodTrifunctor₂₃Obj F G₂₃ ρ₂₃ X₁ X₂ X₃]
-- ...
/-- Associator isomorphism for the action of bifunctors on graded objects. -/
noncomputable def mapBifunctorAssociator :
    mapBifunctorMapObj G ρ₁₂.q (mapBifunctorMapObj F₁₂ ρ₁₂.p X₁ X₂) X₃ ≅
      mapBifunctorMapObj F ρ₂₃.q X₁ (mapBifunctorMapObj G₂₃ ρ₂₃.p X₂ X₃) :=
  have := H₁₂.hasMap
  have := H₂₃.hasMap
  (mapBifunctorComp₁₂MapObjIso F₁₂ G ρ₁₂ X₁ X₂ X₃).symm ≪≫
    mapIso ((((mapTrifunctorMapIso associator I₁ I₂ I₃).app X₁).app X₂).app X₃) r ≪≫
    mapBifunctorComp₂₃MapObjIso F G₂₃ ρ₂₃ X₁ X₂ X₃
```

### `Mathlib/CategoryTheory/GradedObject/Braiding.lean`

```lean
import Mathlib.CategoryTheory.GradedObject.Monoidal
import Mathlib.CategoryTheory.Monoidal.Braided.Basic
-- ...
namespace CategoryTheory
-- ...
open Category Limits
-- ...
variable {I : Type*} [AddCommMonoid I] {C : Type*} [Category C] [MonoidalCategory C]
-- ...
namespace GradedObject
-- ...
namespace Monoidal
-- ...
variable (X Y Z : GradedObject I C)
-- ...
section Braided
-- ...
variable [BraidedCategory C]
-- ...
/-- The braiding `tensorObj X Y ≅ tensorObj Y X` when `X` and `Y` are graded objects
indexed by a commutative additive monoid. -/
noncomputable def braiding [HasTensor X Y] [HasTensor Y X] : tensorObj X Y ≅ tensorObj Y X where
  hom k := tensorObjDesc (fun i j hij => (β_ _ _).hom ≫
    ιTensorObj Y X j i k (by simpa only [add_comm j i] using hij))
  inv k := tensorObjDesc (fun i j hij => (β_ _ _).inv ≫
    ιTensorObj X Y j i k (by simpa only [add_comm j i] using hij))
-- ...
end Braided
-- ...
end Monoidal
-- ...
section Instances
-- ...
variable
  [∀ (X₁ X₂ : GradedObject I C), HasTensor X₁ X₂]
  [∀ (X₁ X₂ X₃ : GradedObject I C), HasGoodTensor₁₂Tensor X₁ X₂ X₃]
  [∀ (X₁ X₂ X₃ : GradedObject I C), HasGoodTensorTensor₂₃ X₁ X₂ X₃]
  [DecidableEq I] [HasInitial C]
  [∀ X₁, PreservesColimit (Functor.empty.{0} C)
    ((MonoidalCategory.curriedTensor C).obj X₁)]
  [∀ X₂, PreservesColimit (Functor.empty.{0} C)
    ((MonoidalCategory.curriedTensor C).flip.obj X₂)]
  [∀ (X₁ X₂ X₃ X₄ : GradedObject I C), HasTensor₄ObjExt X₁ X₂ X₃ X₄]

noncomputable instance braidedCategory [BraidedCategory C] :
    BraidedCategory (GradedObject I C) where
  braiding X Y := Monoidal.braiding X Y
  braiding_naturality_left _ _:= Monoidal.braiding_naturality_left _ _
  braiding_naturality_right _ _ _ _  := Monoidal.braiding_naturality_right _ _
  hexagon_forward _ _ _ := Monoidal.hexagon_forward _ _ _
  hexagon_reverse _ _ _ := Monoidal.hexagon_reverse _ _ _

noncomputable instance symmetricCategory [SymmetricCategory C] :
    SymmetricCategory (GradedObject I C) where
  symmetry _ _ := Monoidal.symmetry _ _
```

### `Mathlib/CategoryTheory/GradedObject/Monoidal.lean`

```lean
import Mathlib.CategoryTheory.GradedObject.Unitor
import Mathlib.Data.Fintype.Prod
-- ...
universe u
-- ...
namespace CategoryTheory
-- ...
open Limits MonoidalCategory Category
-- ...
variable {I : Type u} [AddMonoid I] {C : Type*} [Category C] [MonoidalCategory C]
-- ...
namespace GradedObject
-- ...
/-- The tensor product of two graded objects `X₁` and `X₂` exists if for any `n`,
the coproduct of the objects `X₁ i ⊗ X₂ j` for `i + j = n` exists. -/
abbrev HasTensor (X₁ X₂ : GradedObject I C) : Prop :=
  HasMap (((mapBifunctor (curriedTensor C) I I).obj X₁).obj X₂) (fun ⟨i, j⟩ => i + j)
-- ...
namespace Monoidal
-- ...
/-- The tensor product of two graded objects. -/
noncomputable abbrev tensorObj (X₁ X₂ : GradedObject I C) [HasTensor X₁ X₂] :
    GradedObject I C :=
  mapBifunctorMapObj (curriedTensor C) (fun ⟨i, j⟩ => i + j) X₁ X₂
-- ...
section
-- ...
variable (X₁ X₂ : GradedObject I C) [HasTensor X₁ X₂]
-- ...
/-- The inclusion of a summand in a tensor product of two graded objects. -/
noncomputable def ιTensorObj (i₁ i₂ i₁₂ : I) (h : i₁ + i₂ = i₁₂) :
  X₁ i₁ ⊗ X₂ i₂ ⟶ tensorObj X₁ X₂ i₁₂ :=
    ιMapBifunctorMapObj (curriedTensor C) _ _ _ _ _ _ h
-- ...
variable {X₁ X₂}
-- ...
/-- Constructor for morphisms from a tensor product of two graded objects. -/
noncomputable def tensorObjDesc {A : C} {k : I}
    (f : ∀ (i₁ i₂ : I) (_ : i₁ + i₂ = k), X₁ i₁ ⊗ X₂ i₂ ⟶ A) : tensorObj X₁ X₂ k ⟶ A :=
  mapBifunctorMapObjDesc f
-- ...
end
-- ...
/-- The morphism `tensorObj X₁ Y₁ ⟶ tensorObj X₂ Y₂` induced by morphisms of graded
objects `f : X₁ ⟶ X₂` and `g : Y₁ ⟶ Y₂`. -/
noncomputable def tensorHom {X₁ X₂ Y₁ Y₂ : GradedObject I C} (f : X₁ ⟶ X₂) (g : Y₁ ⟶ Y₂)
    [HasTensor X₁ Y₁] [HasTensor X₂ Y₂] :
    tensorObj X₁ Y₁ ⟶ tensorObj X₂ Y₂ :=
  mapBifunctorMapMap _ _ f g
-- ...
/-- The morphism `tensorObj X Y₁ ⟶ tensorObj X Y₂` induced by a morphism of graded objects
`φ : Y₁ ⟶ Y₂`. -/
noncomputable abbrev whiskerLeft (X : GradedObject I C) {Y₁ Y₂ : GradedObject I C} (φ : Y₁ ⟶ Y₂)
    [HasTensor X Y₁] [HasTensor X Y₂] : tensorObj X Y₁ ⟶ tensorObj X Y₂ :=
  tensorHom (𝟙 X) φ
-- ...
/-- The morphism `tensorObj X₁ Y ⟶ tensorObj X₂ Y` induced by a morphism of graded objects
`φ : X₁ ⟶ X₂`. -/
noncomputable abbrev whiskerRight {X₁ X₂ : GradedObject I C} (φ : X₁ ⟶ X₂) (Y : GradedObject I C)
    [HasTensor X₁ Y] [HasTensor X₂ Y] : tensorObj X₁ Y ⟶ tensorObj X₂ Y :=
  tensorHom φ (𝟙 Y)
-- ...
/-- This is the addition map `I × I × I → I` for an additive monoid `I`. -/
def r₁₂₃ : I × I × I → I := fun ⟨i, j, k⟩ => i + j + k
-- ...
/-- Auxiliary definition for `associator`. -/
@[reducible] def ρ₁₂ : BifunctorComp₁₂IndexData (r₁₂₃ : _ → I) where
  I₁₂ := I
  p := fun ⟨i₁, i₂⟩ => i₁ + i₂
  q := fun ⟨i₁₂, i₃⟩ => i₁₂ + i₃
  hpq := fun _ => rfl
-- ...
/-- Auxiliary definition for `associator`. -/
@[reducible] def ρ₂₃ : BifunctorComp₂₃IndexData (r₁₂₃ : _ → I) where
  I₂₃ := I
  p := fun ⟨i₂, i₃⟩ => i₂ + i₃
  q := fun ⟨i₁₂, i₃⟩ => i₁₂ + i₃
  hpq _ := (add_assoc _ _ _).symm
-- ...
commutes with the coproduct of the objects `X₁ i₁ ⊗ X₂ i₂` such that `i₁ + i₂ = i₁₂`. -/
abbrev _root_.CategoryTheory.GradedObject.HasGoodTensor₁₂Tensor (X₁ X₂ X₃ : GradedObject I C) :=
  HasGoodTrifunctor₁₂Obj (curriedTensor C) (curriedTensor C) ρ₁₂ X₁ X₂ X₃
commutes with the coproduct of the objects `X₂ i₂ ⊗ X₃ i₃` such that `i₂ + i₃ = i₂₃`. -/
abbrev _root_.CategoryTheory.GradedObject.HasGoodTensorTensor₂₃ (X₁ X₂ X₃ : GradedObject I C) :=
  HasGoodTrifunctor₂₃Obj (curriedTensor C) (curriedTensor C) ρ₂₃ X₁ X₂ X₃
-- ...
variable {X₁ X₂ X₃}
-- ...
end
-- ...
section
variable [HasTensor X₁ X₂] [HasTensor (tensorObj X₁ X₂) X₃] [HasTensor Y₁ Y₂]
  [HasTensor (tensorObj Y₁ Y₂) Y₃]
-- ...
variable {X₁ X₂ X₃}
-- ...
end
-- ...
section
variable [HasTensor X₁ X₂] [HasTensor (tensorObj X₁ X₂) X₃] [HasTensor X₂ X₃]
  [HasTensor X₁ (tensorObj X₂ X₃)]
-- ...
/-- The associator isomorphism for graded objects. -/
noncomputable def associator [HasGoodTensor₁₂Tensor X₁ X₂ X₃] [HasGoodTensorTensor₂₃ X₁ X₂ X₃] :
  tensorObj (tensorObj X₁ X₂) X₃ ≅ tensorObj X₁ (tensorObj X₂ X₃) :=
    mapBifunctorAssociator (MonoidalCategory.curriedAssociatorNatIso C) ρ₁₂ ρ₂₃ X₁ X₂ X₃
-- ...
variable {X₁ X₂ X₃}
-- ...
variable [HasTensor Y₁ Y₂] [HasTensor (tensorObj Y₁ Y₂) Y₃] [HasTensor Y₂ Y₃]
  [HasTensor Y₁ (tensorObj Y₂ Y₃)] in
-- ...
end
-- ...
See lemma `left_tensor_tensorObj₃_ext`. -/
abbrev _root_.CategoryTheory.GradedObject.HasLeftTensor₃ObjExt (j : I) := PreservesColimit
  (Discrete.functor fun (i : { i : (I × I × I) | i.1 + i.2.1 + i.2.2 = j }) ↦
    (((mapTrifunctor (bifunctorComp₂₃ (curriedTensor C)
      (curriedTensor C)) I I I).obj X₁).obj X₂).obj X₃ i)
   ((curriedTensor C).obj Z)
-- ...
see the lemma `tensorObj₄_ext`. -/
abbrev _root_.CategoryTheory.GradedObject.HasTensor₄ObjExt :=
  ∀ (i₁ i₂₃₄ : I), HasLeftTensor₃ObjExt (X₁ i₁) X₂ X₃ X₄ i₂₃₄
/-- The unit of the tensor product on graded objects is `(single₀ I).obj (𝟙_ C)`. -/
noncomputable def tensorUnit : GradedObject I C := (single₀ I).obj (𝟙_ C)
-- ...
end TensorUnit
-- ...
section LeftUnitor
-- ...
variable [DecidableEq I] [HasInitial C]
  [∀ X₂, PreservesColimit (Functor.empty.{0} C) ((curriedTensor C).flip.obj X₂)]
  (X X' : GradedObject I C)

instance : HasTensor tensorUnit X :=
  mapBifunctorLeftUnitor_hasMap _ _ (leftUnitorNatIso C) _ zero_add _

instance : HasMap (((mapBifunctor (curriedTensor C) I I).obj
    ((single₀ I).obj (𝟙_ C))).obj X) (fun ⟨i₁, i₂⟩ => i₁ + i₂) :=
  (inferInstance : HasTensor tensorUnit X)
-- ...
/-- The left unitor isomorphism for graded objects. -/
noncomputable def leftUnitor : tensorObj tensorUnit X ≅ X :=
    mapBifunctorLeftUnitor (curriedTensor C) (𝟙_ C)
      (leftUnitorNatIso C) (fun (⟨i₁, i₂⟩ : I × I) => i₁ + i₂) zero_add X
-- ...
variable {X X'}
-- ...
end LeftUnitor
-- ...
section RightUnitor
-- ...
variable [DecidableEq I] [HasInitial C]
  [∀ X₁, PreservesColimit (Functor.empty.{0} C) ((curriedTensor C).obj X₁)]
  (X X' : GradedObject I C)

instance : HasTensor X tensorUnit :=
  mapBifunctorRightUnitor_hasMap (curriedTensor C) _
    (rightUnitorNatIso C) _ add_zero _

instance : HasMap (((mapBifunctor (curriedTensor C) I I).obj X).obj
    ((single₀ I).obj (𝟙_ C))) (fun ⟨i₁, i₂⟩ => i₁ + i₂) :=
  (inferInstance : HasTensor X tensorUnit)
-- ...
/-- The right unitor isomorphism for graded objects. -/
noncomputable def rightUnitor : tensorObj X tensorUnit ≅ X :=
    mapBifunctorRightUnitor (curriedTensor C) (𝟙_ C)
      (rightUnitorNatIso C) (fun (⟨i₁, i₂⟩ : I × I) => i₁ + i₂) add_zero X
-- ...
variable {X X'}
-- ...
end RightUnitor
-- ...
section Triangle
-- ...
variable [DecidableEq I] [HasInitial C]
  [∀ X₁, PreservesColimit (Functor.empty.{0} C) ((curriedTensor C).obj X₁)]
  [∀ X₂, PreservesColimit (Functor.empty.{0} C)
    ((curriedTensor C).flip.obj X₂)]
  (X₁ X₃ : GradedObject I C) [HasTensor X₁ X₃]
  [HasTensor (tensorObj X₁ tensorUnit) X₃] [HasTensor X₁ (tensorObj tensorUnit X₃)]
  [HasGoodTensor₁₂Tensor X₁ tensorUnit X₃] [HasGoodTensorTensor₂₃ X₁ tensorUnit X₃]
-- ...
end Triangle
-- ...
end Monoidal
-- ...
section
-- ...
variable
  [∀ (X₁ X₂ : GradedObject I C), HasTensor X₁ X₂]
  [∀ (X₁ X₂ X₃ : GradedObject I C), HasGoodTensor₁₂Tensor X₁ X₂ X₃]
  [∀ (X₁ X₂ X₃ : GradedObject I C), HasGoodTensorTensor₂₃ X₁ X₂ X₃]
  [DecidableEq I] [HasInitial C]
  [∀ X₁, PreservesColimit (Functor.empty.{0} C) ((curriedTensor C).obj X₁)]
  [∀ X₂, PreservesColimit (Functor.empty.{0} C) ((curriedTensor C).flip.obj X₂)]
  [∀ (X₁ X₂ X₃ X₄ : GradedObject I C), HasTensor₄ObjExt X₁ X₂ X₃ X₄]

noncomputable instance monoidalCategory : MonoidalCategory (GradedObject I C) where
  tensorObj X Y := Monoidal.tensorObj X Y
  tensorHom f g := Monoidal.tensorHom f g
  tensorHom_def f g := Monoidal.tensorHom_def f g
  whiskerLeft X _ _ φ := Monoidal.whiskerLeft X φ
  whiskerRight {_ _ φ Y} := Monoidal.whiskerRight φ Y
  tensorUnit := Monoidal.tensorUnit
  associator X₁ X₂ X₃ := Monoidal.associator X₁ X₂ X₃
  associator_naturality f₁ f₂ f₃ := Monoidal.associator_naturality f₁ f₂ f₃
  leftUnitor X := Monoidal.leftUnitor X
  leftUnitor_naturality := Monoidal.leftUnitor_naturality
  rightUnitor X := Monoidal.rightUnitor X
  rightUnitor_naturality := Monoidal.rightUnitor_naturality
  tensor_comp f₁ f₂ g₁ g₂ := Monoidal.tensor_comp f₁ g₁ f₂ g₂
  pentagon X₁ X₂ X₃ X₄ := Monoidal.pentagon X₁ X₂ X₃ X₄
  triangle X₁ X₂ := Monoidal.triangle X₁ X₂
```

### `Mathlib/CategoryTheory/GradedObject/Single.lean`

```lean
import Mathlib.CategoryTheory.GradedObject
-- ...
namespace CategoryTheory
-- ...
open Limits
-- ...
namespace GradedObject
-- ...
variable {J : Type*} {C : Type*} [Category C] [HasInitial C] [DecidableEq J]
-- ...
/-- The functor which sends `X : C` to the graded object which is `X` in degree `j`
and the initial object in other degrees. -/
noncomputable def single (j : J) : C ⥤ GradedObject J C where
  obj X i := if i = j then X else ⊥_ C
  map {X₁ X₂} f i :=
    if h : i = j then eqToHom (if_pos h) ≫ f ≫ eqToHom (if_pos h).symm
    else eqToHom (by dsimp; rw [if_neg h, if_neg h])
-- ...
variable (J) in
/-- The functor which sends `X : C` to the graded object which is `X` in degree `0`
and the initial object in nonzero degrees. -/
noncomputable abbrev single₀ [Zero J] : C ⥤ GradedObject J C := single 0
-- ...
/-- The canonical isomorphism `(single j).obj X i ≅ X` when `i = j`. -/
noncomputable def singleObjApplyIsoOfEq (j : J) (X : C) (i : J) (h : i = j) :
    (single j).obj X i ≅ X := eqToIso (if_pos h)
-- ...
/-- The canonical isomorphism `(single j).obj X j ≅ X`. -/
noncomputable abbrev singleObjApplyIso (j : J) (X : C) :
    (single j).obj X j ≅ X := singleObjApplyIsoOfEq j X j rfl
-- ...
/-- The object `(single j).obj X i` is initial when `i ≠ j`. -/
noncomputable def isInitialSingleObjApply (j : J) (X : C) (i : J) (h : i ≠ j) :
    IsInitial ((single j).obj X i) := by
  dsimp [single]
  rw [if_neg h]
  exact initialIsInitial
```

### `Mathlib/CategoryTheory/GradedObject/Unitor.lean`

```lean
import Mathlib.CategoryTheory.GradedObject.Associator
import Mathlib.CategoryTheory.GradedObject.Single
-- ...
namespace CategoryTheory
-- ...
open Category Limits
-- ...
namespace GradedObject
-- ...
section LeftUnitor
-- ...
variable {C D I J : Type*} [Category C] [Category D]
  [Zero I] [DecidableEq I] [HasInitial C]
  (F : C ⥤ D ⥤ D) (X : C) (e : F.obj X ≅ 𝟭 D)
  [∀ (Y : D), PreservesColimit (Functor.empty.{0} C) (F.flip.obj Y)]
  (p : I × J → J) (hp : ∀ (j : J), p ⟨0, j⟩ = j)
  (Y Y' : GradedObject J D) (φ : Y ⟶ Y')
-- ...
when `a : I × J` is such that `a.1 = 0`. -/
@[simps!]
noncomputable def mapBifunctorObjSingle₀ObjIso (a : I × J) (ha : a.1 = 0) :
    ((mapBifunctor F I J).obj ((single₀ I).obj X)).obj Y a ≅ Y a.2 :=
  (F.mapIso (singleObjApplyIsoOfEq _ X _ ha)).app _ ≪≫ e.app (Y a.2)
when `a : I × J` is such that `a.1 ≠ 0`. -/
noncomputable def mapBifunctorObjSingle₀ObjIsInitial (a : I × J) (ha : a.1 ≠ 0) :
    IsInitial (((mapBifunctor F I J).obj ((single₀ I).obj X)).obj Y a) :=
  IsInitial.isInitialObj (F.flip.obj (Y a.2)) _ (isInitialSingleObjApply _ _ _ ha)
`mapBifunctorMapObj F p ((single₀ I).obj X) Y ≅ Y`, see `mapBifunctorLeftUnitor`. -/
noncomputable def mapBifunctorLeftUnitorCofan (hp : ∀ (j : J), p ⟨0, j⟩ = j) (Y) (j : J) :
    (((mapBifunctor F I J).obj ((single₀ I).obj X)).obj Y).CofanMapObjFun p j :=
  CofanMapObjFun.mk _ _ _ (Y j) (fun a ha =>
    if ha : a.1 = 0 then
      (mapBifunctorObjSingle₀ObjIso F X e Y a ha).hom ≫ eqToHom (by aesop)
    else
      (mapBifunctorObjSingle₀ObjIsInitial F X Y a ha).to _)
/-- The cofan `mapBifunctorLeftUnitorCofan F X e p hp Y j` is a colimit. -/
noncomputable def mapBifunctorLeftUnitorCofanIsColimit (j : J) :
    IsColimit (mapBifunctorLeftUnitorCofan F X e p hp Y j) :=
  mkCofanColimit _
    (fun s => e.inv.app (Y j) ≫
      (F.map (singleObjApplyIso (0 : I) X).inv).app (Y j) ≫ s.inj ⟨⟨0, j⟩, hp j⟩)
    (fun s => by
      rintro ⟨⟨i, j'⟩, h⟩
      by_cases hi : i = 0
      · subst hi
        simp only [Set.mem_preimage, hp, Set.mem_singleton_iff] at h
        subst h
        simp
      · apply IsInitial.hom_ext
        exact mapBifunctorObjSingle₀ObjIsInitial _ _ _ _ hi)
    (fun s m hm => by simp [← hm ⟨⟨0, j⟩, hp j⟩])
this is the left unitor isomorphism `mapBifunctorMapObj F p ((single₀ I).obj X) Y ≅ Y`. -/
noncomputable def mapBifunctorLeftUnitor : mapBifunctorMapObj F p ((single₀ I).obj X) Y ≅ Y :=
  isoMk _ _ (fun j => (CofanMapObjFun.iso
    (mapBifunctorLeftUnitorCofanIsColimit F X e p hp Y j)).symm)
when `a : J × I` is such that `a.2 = 0`. -/
@[simps!]
noncomputable def mapBifunctorObjObjSingle₀Iso (a : J × I) (ha : a.2 = 0) :
    ((mapBifunctor F J I).obj X).obj ((single₀ I).obj Y) a ≅ X a.1 :=
  Functor.mapIso _ (singleObjApplyIsoOfEq _ Y _ ha) ≪≫ e.app (X a.1)
is such that `a.2 ≠ 0`. -/
noncomputable def mapBifunctorObjObjSingle₀IsInitial (a : J × I) (ha : a.2 ≠ 0) :
    IsInitial (((mapBifunctor F J I).obj X).obj ((single₀ I).obj Y) a) :=
  IsInitial.isInitialObj (F.obj (X a.1)) _ (isInitialSingleObjApply _ _ _ ha)
`mapBifunctorMapObj F p X ((single₀ I).obj Y) ≅ X`, see `mapBifunctorRightUnitor`. -/
noncomputable def mapBifunctorRightUnitorCofan (hp : ∀ (j : J), p ⟨j, 0⟩ = j) (X) (j : J) :
    (((mapBifunctor F J I).obj X).obj ((single₀ I).obj Y)).CofanMapObjFun p j :=
  CofanMapObjFun.mk _ _ _ (X j) (fun a ha =>
    if ha : a.2 = 0 then
      (mapBifunctorObjObjSingle₀Iso F Y e X a ha).hom ≫ eqToHom (by aesop)
    else
      (mapBifunctorObjObjSingle₀IsInitial F Y X a ha).to _)
/-- The cofan `mapBifunctorRightUnitorCofan F Y e p hp X j` is a colimit. -/
noncomputable def mapBifunctorRightUnitorCofanIsColimit (j : J) :
    IsColimit (mapBifunctorRightUnitorCofan F Y e p hp X j) :=
  mkCofanColimit _
    (fun s => e.inv.app (X j) ≫
      (F.obj (X j)).map (singleObjApplyIso (0 : I) Y).inv ≫ s.inj ⟨⟨j, 0⟩, hp j⟩)
    (fun s => by
      rintro ⟨⟨j', i⟩, h⟩
      by_cases hi : i = 0
      · subst hi
        simp only [Set.mem_preimage, hp, Set.mem_singleton_iff] at h
        subst h
        dsimp
        rw [mapBifunctorRightUnitorCofan_inj, assoc, Iso.hom_inv_id_app_assoc,
          ← Functor.map_comp_assoc, Iso.hom_inv_id, Functor.map_id, id_comp]
      · apply IsInitial.hom_ext
        exact mapBifunctorObjObjSingle₀IsInitial _ _ _ _ hi)
    (fun s m hm => by
      dsimp
      rw [← hm ⟨⟨j, 0⟩, hp j⟩, mapBifunctorRightUnitorCofan_inj, assoc, ← Functor.map_comp_assoc,
        Iso.inv_hom_id, Functor.map_id, id_comp, Iso.inv_hom_id_app_assoc])
this is the right unitor isomorphism `mapBifunctorMapObj F p X ((single₀ I).obj Y) ≅ X`. -/
noncomputable def mapBifunctorRightUnitor : mapBifunctorMapObj F p X ((single₀ I).obj Y) ≅ X :=
  isoMk _ _ (fun j => (CofanMapObjFun.iso
    (mapBifunctorRightUnitorCofanIsColimit F Y e p hp X j)).symm)
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
