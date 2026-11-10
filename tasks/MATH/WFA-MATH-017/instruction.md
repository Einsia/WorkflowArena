> Your working directory is `/workspace`, i.e. the `workspace/` referred to below: a pinned mathlib4 source checkout, initialised as a git repository (start commit `start`). The Lean toolchain, the dependency packages and the prebuilt Mathlib cache are already installed, and `lake build Mathlib` has already been run; there is no network access at run time, so `lake exe cache get` is neither needed nor possible. Deliver your work by editing `/workspace/Mathlib/` and `/workspace/Mathlib.lean` directly. Grading collects only these two paths into the grader's own clean copy, where every file that already exists under `Mathlib/` in the start state is reset to its start-state content (edits to existing Mathlib files are discarded; only new files under `Mathlib/` and your `Mathlib.lean` are kept, and start-state import lines missing from your `Mathlib.lean` are re-added), then runs `lake build Mathlib` and checks the required declarations; changes to any other file are ignored.

# feat(Condensed): characterisation of discrete (light) condensed sets and modules

You are working in a pinned mathlib4 checkout (`workspace/`; Lean toolchain pinned in
`lean-toolchain`, dependencies in `lake-manifest.json`; the prebuilt
Mathlib build is already installed). Develop the mathematics below as mathlib-quality Lean code.

## Goal

This PR provides a characterization of discrete condensed sets and modules, both in the light setting and the classical one. 

* Six equivalent conditions on a condensed set X to be discrete
  1. The counit of the discrete-underlying adjunction applied to X is an isomorphism
  2. X is in the essential image of the constant sheaf functor `Type (u+1) ⥤ CondensedSet.{u}`
  3. X is in the essential image of the functor `Type (u+1) ⥤ CondensedSet.{u}` which takes a set to the sheaf of locally             constant maps into it.
  4. The counit of the locally-constant-underlying adjunction applied to X is an isomorphism.
  5. X restricted to the coherent site of profinite sets is discrete as a sheaf
  6. For every profinite set S written as a limit of finite sets, X maps S to the corresponding colimit.
* A condensed module over a ring is discrete if and only if its underlying condensed set is, and therefore the analogues of the equivalent conditions above also characterize condensed modules as discrete
* The analogues for the above for light condensed sets and modules

This is a substantial development: in the original history it took 34 separate
contributions. Everything needed beyond the current library is yours to build.

## Required deliverables

After your work, each of the following constants must exist (anywhere under
`Mathlib/`, imported from `Mathlib.lean`) and have exactly this type, as printed
by `#check @name` (grading compares the elaborated types structurally, so notation
and binder names do not matter, but the statement must be the same):

```lean
Condensed.IsDiscrete :
  {C : Type u_2} →
  [inst : CategoryTheory.Category C] →
    [inst_1 : CategoryTheory.HasWeakSheafify (CategoryTheory.coherentTopology CompHaus) C] → Condensed C → Prop
```

```lean
Condensed.discrete :
  (C : Type u_2) →
  [inst : CategoryTheory.Category C] →
    [inst_1 : CategoryTheory.HasWeakSheafify (CategoryTheory.coherentTopology CompHaus) C] →
      CategoryTheory.Functor C (Condensed C)
```

```lean
Condensed.discreteUnderlyingAdj :
  (C : Type u_2) →
  [inst : CategoryTheory.Category C] →
    [inst_1 : CategoryTheory.HasWeakSheafify (CategoryTheory.coherentTopology CompHaus) C] →
      Condensed.discrete C ⊣ Condensed.underlying C
```

```lean
Condensed.underlying :
  (C : Type u_2) → [inst : CategoryTheory.Category C] → CategoryTheory.Functor (Condensed C) C
```

```lean
CondensedMod.LocallyConstant.adjunction :
  (R : Type (u_1 + 1)) →
  [inst : Ring R] → CondensedMod.LocallyConstant.functor R ⊣ Condensed.underlying (ModuleCat R)
```

```lean
CondensedMod.LocallyConstant.functor :
  (R : Type (u_1 + 1)) →
  [inst : Ring R] → CategoryTheory.Functor (ModuleCat R) (CondensedMod R)
```

```lean
CondensedMod.instHasLimitsOfSizeModuleCat :
  ∀ (R : Type (u_1 + 1)) [inst : Ring R],
  CategoryTheory.Limits.HasLimitsOfSize (ModuleCat R)
```

```lean
CondensedMod.isDiscrete_iff_isDiscrete_forget :
  ∀ (R : Type (u_1 + 1)) [inst : Ring R] (M : CondensedMod R),
  Condensed.IsDiscrete M ↔
    Condensed.IsDiscrete (Prefunctor.obj (CategoryTheory.Functor.toPrefunctor (Condensed.forget R)) M)
```

```lean
CondensedMod.isDiscrete_tfae :
  ∀ (R : Type (u_1 + 1)) [inst : Ring R] (M : CondensedMod R),
  List.TFAE
    [Condensed.IsDiscrete M,
      CategoryTheory.IsIso
        (CategoryTheory.NatTrans.app (CategoryTheory.Adjunction.counit (Condensed.discreteUnderlyingAdj (ModuleCat R)))
          M),
      M ∈ CategoryTheory.Functor.essImage (Condensed.discrete (ModuleCat R)),
      M ∈ CategoryTheory.Functor.essImage (CondensedMod.LocallyConstant.functor R),
      CategoryTheory.IsIso
        (CategoryTheory.NatTrans.app (CategoryTheory.Adjunction.counit (CondensedMod.LocallyConstant.adjunction R)) M),
      CategoryTheory.Sheaf.IsConstant (CategoryTheory.coherentTopology Profinite)
        (Prefunctor.obj
          (CategoryTheory.Functor.toPrefunctor
            (CategoryTheory.Equivalence.inverse (Condensed.ProfiniteCompHaus.equivalence (ModuleCat R))))
          M),
      ∀ (S : Profinite),
        Nonempty
          (CategoryTheory.Limits.IsColimit
            (CategoryTheory.Functor.mapCocone
              (CategoryTheory.Functor.comp (CategoryTheory.Functor.op profiniteToCompHaus) (CategoryTheory.Sheaf.val M))
              (CategoryTheory.Limits.Cone.op (Profinite.asLimitCone S))))]
```

```lean
CondensedSet.LocallyConstant.adjunction :
  CondensedSet.LocallyConstant.functor ⊣ Condensed.underlying (Type (u_1 + 1))
```

```lean
CondensedSet.LocallyConstant.functor :
  CategoryTheory.Functor (Type (u_1 + 1)) CondensedSet
```

```lean
CondensedSet.isDiscrete_tfae :
  ∀ (X : CondensedSet),
  List.TFAE
    [Condensed.IsDiscrete X,
      CategoryTheory.IsIso
        (CategoryTheory.NatTrans.app
          (CategoryTheory.Adjunction.counit (Condensed.discreteUnderlyingAdj (Type (u_1 + 1)))) X),
      X ∈ CategoryTheory.Functor.essImage (Condensed.discrete (Type (u_1 + 1))),
      X ∈ CategoryTheory.Functor.essImage CondensedSet.LocallyConstant.functor,
      CategoryTheory.IsIso
        (CategoryTheory.NatTrans.app (CategoryTheory.Adjunction.counit CondensedSet.LocallyConstant.adjunction) X),
      CategoryTheory.Sheaf.IsConstant (CategoryTheory.coherentTopology Profinite)
        (Prefunctor.obj
          (CategoryTheory.Functor.toPrefunctor
            (CategoryTheory.Equivalence.inverse (Condensed.ProfiniteCompHaus.equivalence (Type (u_1 + 1)))))
          X),
      ∀ (S : Profinite),
        Nonempty
          (CategoryTheory.Limits.IsColimit
            (CategoryTheory.Functor.mapCocone
              (CategoryTheory.Functor.comp (CategoryTheory.Functor.op profiniteToCompHaus) (CategoryTheory.Sheaf.val X))
              (CategoryTheory.Limits.Cone.op (Profinite.asLimitCone S))))]
```

```lean
CondensedSet.mem_locallyContant_essImage_of_isColimit_mapCocone :
  ∀ (X : CondensedSet),
  ((S : Profinite) →
      CategoryTheory.Limits.IsColimit
        (CategoryTheory.Functor.mapCocone
          (CategoryTheory.Functor.comp (CategoryTheory.Functor.op profiniteToCompHaus) (CategoryTheory.Sheaf.val X))
          (CategoryTheory.Limits.Cone.op (Profinite.asLimitCone S)))) →
    X ∈ CategoryTheory.Functor.essImage CondensedSet.LocallyConstant.functor
```

```lean
LightCondMod.LocallyConstant.adjunction :
  (R : Type u_1) →
  [inst : Ring R] → LightCondMod.LocallyConstant.functor R ⊣ LightCondensed.underlying (ModuleCat R)
```

```lean
LightCondMod.LocallyConstant.functor :
  (R : Type u_1) →
  [inst : Ring R] → CategoryTheory.Functor (ModuleCat R) (LightCondMod R)
```

```lean
LightCondMod.LocallyConstant.instHasSheafifyLightProfiniteCoherentTopologyModuleCat :
  ∀ (R : Type u_1) [inst : Ring R],
  CategoryTheory.HasSheafify (CategoryTheory.coherentTopology LightProfinite) (ModuleCat R)
```

```lean
LightCondMod.isDiscrete_iff_isDiscrete_forget :
  ∀ (R : Type u_1) [inst : Ring R] (M : LightCondMod R),
  LightCondensed.IsDiscrete M ↔
    LightCondensed.IsDiscrete (Prefunctor.obj (CategoryTheory.Functor.toPrefunctor (LightCondensed.forget R)) M)
```

```lean
LightCondMod.isDiscrete_tfae :
  ∀ (R : Type u_1) [inst : Ring R] (M : LightCondMod R),
  List.TFAE
    [LightCondensed.IsDiscrete M,
      CategoryTheory.IsIso
        (CategoryTheory.NatTrans.app
          (CategoryTheory.Adjunction.counit (LightCondensed.discreteUnderlyingAdj (ModuleCat R))) M),
      M ∈ CategoryTheory.Functor.essImage (LightCondensed.discrete (ModuleCat R)),
      M ∈ CategoryTheory.Functor.essImage (LightCondMod.LocallyConstant.functor R),
      CategoryTheory.IsIso
        (CategoryTheory.NatTrans.app (CategoryTheory.Adjunction.counit (LightCondMod.LocallyConstant.adjunction R)) M),
      ∀ (S : LightProfinite),
        Nonempty
          (CategoryTheory.Limits.IsColimit
            (CategoryTheory.Functor.mapCocone (CategoryTheory.Sheaf.val M)
              (CategoryTheory.Limits.coconeRightOpOfCone (LightProfinite.asLimitCone S))))]
```

```lean
LightCondSet.LocallyConstant.adjunction :
  LightCondSet.LocallyConstant.functor ⊣ LightCondensed.underlying (Type u_1)
```

```lean
LightCondSet.LocallyConstant.functor :
  CategoryTheory.Functor (Type u_1) LightCondSet
```

```lean
LightCondSet.isDiscrete_tfae :
  ∀ (X : LightCondSet),
  List.TFAE
    [LightCondensed.IsDiscrete X,
      CategoryTheory.IsIso
        (CategoryTheory.NatTrans.app
          (CategoryTheory.Adjunction.counit (LightCondensed.discreteUnderlyingAdj (Type u_1))) X),
      X ∈ CategoryTheory.Functor.essImage (LightCondensed.discrete (Type u_1)),
      X ∈ CategoryTheory.Functor.essImage LightCondSet.LocallyConstant.functor,
      CategoryTheory.IsIso
        (CategoryTheory.NatTrans.app (CategoryTheory.Adjunction.counit LightCondSet.LocallyConstant.adjunction) X),
      ∀ (S : LightProfinite),
        Nonempty
          (CategoryTheory.Limits.IsColimit
            (CategoryTheory.Functor.mapCocone (CategoryTheory.Sheaf.val X)
              (CategoryTheory.Limits.coconeRightOpOfCone (LightProfinite.asLimitCone S))))]
```

```lean
LightCondSet.mem_locallyContant_essImage_of_isColimit_mapCocone :
  ∀ (X : LightCondSet),
  ((S : LightProfinite) →
      CategoryTheory.Limits.IsColimit
        (CategoryTheory.Functor.mapCocone (CategoryTheory.Sheaf.val X)
          (CategoryTheory.Limits.coconeRightOpOfCone (LightProfinite.asLimitCone S)))) →
    X ∈ CategoryTheory.Functor.essImage LightCondSet.LocallyConstant.functor
```

```lean
LightCondensed.IsDiscrete :
  {C : Type u_2} →
  [inst : CategoryTheory.Category C] →
    [inst_1 : CategoryTheory.HasWeakSheafify (CategoryTheory.coherentTopology LightProfinite) C] →
      LightCondensed C → Prop
```

```lean
LightCondensed.discrete :
  (C : Type u_2) →
  [inst : CategoryTheory.Category C] →
    [inst_1 : CategoryTheory.HasSheafify (CategoryTheory.coherentTopology LightProfinite) C] →
      CategoryTheory.Functor C (LightCondensed C)
```

```lean
LightCondensed.discreteUnderlyingAdj :
  (C : Type u_2) →
  [inst : CategoryTheory.Category C] →
    [inst_1 : CategoryTheory.HasSheafify (CategoryTheory.coherentTopology LightProfinite) C] →
      LightCondensed.discrete C ⊣ LightCondensed.underlying C
```

```lean
LightCondensed.underlying :
  (C : Type u_2) →
  [inst : CategoryTheory.Category C] → CategoryTheory.Functor (LightCondensed C) C
```

```lean
LightProfinite.asLimitCone :
  (S : LightProfinite) → CategoryTheory.Limits.Cone (LightProfinite.diagram S)
```

```lean
LightProfinite.diagram :
  LightProfinite → CategoryTheory.Functor ℕᵒᵖ LightProfinite
```

## Pinned reference definitions

The excerpts below, taken from the reference development, contain every pinned declaration (53
constants including the auxiliary ones Lean generates for them, such as constructors, recursors,
projections and `match_` functions). Reproduce these declarations exactly. Using a file with the same
path, imports and `variable`/`open` context is the safest way to get an identical elaborated value
(for example, instance resolution depends on the imports). `-- ...` marks omitted parts of the
reference file (other declarations and proofs, which you develop yourself).

### `Mathlib/Condensed/Discrete/Basic.lean`

```lean
import Mathlib.CategoryTheory.Sites.ConstantSheaf
import Mathlib.CategoryTheory.Sites.Equivalence
import Mathlib.Condensed.Basic
import Mathlib.Condensed.Light.Basic
-- ...
universe u v w
-- ...
open CategoryTheory Limits Opposite GrothendieckTopology
-- ...
namespace Condensed
-- ...
variable (C : Type w) [Category.{u+1} C] [HasWeakSheafify (coherentTopology CompHaus.{u}) C]
-- ...
-/
@[simps!]
noncomputable def discrete : C ⥤ Condensed.{u} C := constantSheaf _ C
-/
@[simps!]
noncomputable def underlying : Condensed.{u} C ⥤ C :=
  (sheafSections _ _).obj ⟨CompHaus.of PUnit.{u+1}⟩
-/
noncomputable def discreteUnderlyingAdj : discrete C ⊣ underlying C :=
  constantSheafAdj _ _ CompHaus.isTerminalPUnit
-/
@[simps!]
noncomputable def discrete : C ⥤ LightCondensed.{u} C := constantSheaf _ C
-/
@[simps!]
noncomputable def underlying : LightCondensed.{u} C ⥤ C :=
  (sheafSections _ _).obj (op (LightProfinite.of PUnit))
-/
noncomputable def discreteUnderlyingAdj : discrete C ⊣ underlying C :=
  constantSheafAdj _ _ CompHausLike.isTerminalPUnit
```

### `Mathlib/Condensed/Discrete/Characterization.lean`

```lean
import Mathlib.Condensed.Discrete.Colimit
import Mathlib.Condensed.Discrete.Module
-- ...
universe u
-- ...
open CategoryTheory Limits Functor FintypeCat
-- ...
attribute [local instance] ConcreteCategory.instFunLike
-- ...
namespace Condensed
-- ...
variable {C : Type*} [Category C] [HasWeakSheafify (coherentTopology CompHaus.{u}) C]
-- ...
-/
abbrev IsDiscrete (X : Condensed.{u} C) := X.IsConstant (coherentTopology CompHaus)
-/
noncomputable abbrev LocallyConstant.adjunction :
    CondensedSet.LocallyConstant.functor ⊣ Condensed.underlying (Type (u+1)) :=
  CompHausLike.LocallyConstant.adjunction _ _

instance : HasLimitsOfSize.{u, u+1} (ModuleCat.{u+1} R) :=
  hasLimitsOfSizeShrink.{u, u+1, u+1, u+1} _
-/
abbrev IsDiscrete (X : LightCondensed.{u} C) := X.IsConstant (coherentTopology LightProfinite)
-/
noncomputable abbrev LocallyConstant.adjunction :
    LightCondSet.LocallyConstant.functor ⊣ LightCondensed.underlying (Type u) :=
  CompHausLike.LocallyConstant.adjunction _ _
```

### `Mathlib/Condensed/Discrete/LocallyConstant.lean`

```lean
import Mathlib.Condensed.Discrete.Basic
import Mathlib.Condensed.TopComparison
import Mathlib.Topology.Category.CompHausLike.SigmaComparison
import Mathlib.Topology.FiberPartition
-- ...
universe u w
-- ...
open CategoryTheory Limits LocallyConstant TopologicalSpace.Fiber Opposite Function Fiber
-- ...
attribute [local instance] ConcreteCategory.instFunLike
-- ...
variable {P : TopCat.{u} → Prop}
-- ...
namespace CompHausLike.LocallyConstant
-- ...
-/
@[simps]
def functorToPresheaves : Type (max u w) ⥤ ((CompHausLike.{u} P)ᵒᵖ ⥤ Type max u w) where
  obj X := {
    obj := fun ⟨S⟩ ↦ LocallyConstant S X
    map := fun f g ↦ g.comap f.unop }
  map f := { app := fun _ t ↦ t.map f }
-- ...
section Adjunction
-- ...
variable [∀ (S : CompHausLike.{u} P) (p : S → Prop), HasProp P (Subtype p)]
-- ...
section
-- ...
variable {Q : CompHausLike.{u} P} {Z : Type max u w} (r : LocallyConstant Q Z) (a : Fiber r)
-- ...
/-- A fiber of a locally constant map as a `CompHausLike P`. -/
def fiber : CompHausLike.{u} P := CompHausLike.of P a.val
-- ...
/-- The canonical map from the coproduct induced by `f` to `S` as an isomorphism in
`CompHausLike P`. -/
noncomputable def sigmaIso [HasExplicitFiniteCoproducts.{u} P] : (finiteCoproduct (fiber r)) ≅ Q :=
  isoOfBijective (sigmaIsoHom r) ⟨sigmaIsoHom_inj r, sigmaIsoHom_surj r⟩
-- ...
end
-- ...
variable {S : CompHausLike.{u} P} {Y : (CompHausLike.{u} P)ᵒᵖ ⥤ Type max u w}
  [HasProp P PUnit.{u+1}] (f : LocallyConstant S (Y.obj (op (CompHausLike.of P PUnit.{u+1}))))
-- ...
/-- The projection of the counit. -/
noncomputable def counitAppAppImage : (a : Fiber f) → Y.obj ⟨fiber f a⟩ :=
  fun a ↦ Y.map (CompHausLike.isTerminalPUnit.from _).op a.image
-- ...
-/
noncomputable def counitAppApp (S : CompHausLike.{u} P) (Y : (CompHausLike.{u} P)ᵒᵖ ⥤ Type max u w)
    [PreservesFiniteProducts Y] [HasExplicitFiniteCoproducts.{u} P] :
    LocallyConstant S (Y.obj (op (CompHausLike.of P PUnit.{u+1}))) ⟶ Y.obj ⟨S⟩ :=
  fun r ↦ ((inv (sigmaComparison Y (fun a ↦ (fiber r a).1))) ≫
    (Y.mapIso (sigmaIso r).op).inv) (counitAppAppImage r)
-- ...
variable {T : CompHausLike.{u} P} (g : T ⟶ S)
-- ...
/-- The counit is natural in `S : CompHausLike P` -/
@[simps!]
noncomputable def counitApp [HasExplicitFiniteCoproducts.{u} P]
    (Y : (CompHausLike.{u} P)ᵒᵖ ⥤ Type max u w) [PreservesFiniteProducts Y] :
    (functorToPresheaves.obj (Y.obj (op (CompHausLike.of P PUnit.{u+1})))) ⟶ Y where
  app := fun ⟨S⟩ ↦ counitAppApp S Y
  naturality := by
    intro S T g
    ext f
    apply presheaf_ext (f.comap g.unop)
    intro a
    simp only [op_unop, functorToPresheaves_obj_obj, types_comp_apply, functorToPresheaves_obj_map,
      incl_of_counitAppApp, ← FunctorToTypes.map_comp_apply, incl_comap]
    simp only [FunctorToTypes.map_comp_apply, incl_of_counitAppApp]
    simp only [counitAppAppImage, ← FunctorToTypes.map_comp_apply, ← op_comp,
      terminal.comp_from]
    apply congrArg
    exact image_eq_image_mk (g := g.unop) (a := a)
-- ...
variable (P) (X : TopCat.{max u w})
    [HasExplicitFiniteCoproducts.{0} P] [HasExplicitPullbacks P]
    (hs : ∀ ⦃X Y : CompHausLike P⦄ (f : X ⟶ Y), EffectiveEpi f → Function.Surjective f)
-- ...
/-- `CompHausLike.LocallyConstant.functorToPresheaves` lands in sheaves. -/
@[simps]
def functor :
    haveI := CompHausLike.preregular hs
    Type (max u w) ⥤ Sheaf (coherentTopology (CompHausLike.{u} P)) (Type (max u w)) where
  obj X := {
    val := functorToPresheaves.{u, w}.obj X
    cond := by
      rw [Presheaf.isSheaf_of_iso_iff (functorToPresheavesIso P hs X)]
      exact ((TopCat.discrete.obj X).toSheafCompHausLike P hs).cond }
  map f := ⟨functorToPresheaves.{u, w}.map f⟩
-- ...
/-- The counit is natural in both `S : CompHausLike P` and
`Y : Sheaf (coherentTopology (CompHausLike P)) (Type (max u w))` -/
@[simps]
noncomputable def counit [HasExplicitFiniteCoproducts.{u} P] : haveI := CompHausLike.preregular hs
    (sheafSections _ _).obj ⟨CompHausLike.of P PUnit.{u+1}⟩ ⋙ functor.{u, w} P hs ⟶
        𝟭 (Sheaf (coherentTopology (CompHausLike.{u} P)) (Type (max u w))) where
  app X := haveI := CompHausLike.preregular hs
    ⟨counitApp X.val⟩
  naturality X Y g := by
    have := CompHausLike.preregular hs
    apply Sheaf.hom_ext
    simp only [functor, id_eq, eq_mpr_eq_cast, Functor.comp_obj, Functor.flip_obj_obj,
      sheafToPresheaf_obj, Functor.id_obj, Functor.comp_map, Functor.flip_obj_map,
      sheafToPresheaf_map, Sheaf.instCategorySheaf_comp_val, Functor.id_map]
    ext S (f : LocallyConstant _ _)
    simp only [FunctorToTypes.comp, counitApp_app]
    apply presheaf_ext (f.map (g.val.app (op (CompHausLike.of P PUnit.{u+1}))))
    intro a
    simp only [op_unop, functorToPresheaves_map_app, incl_of_counitAppApp]
    apply presheaf_ext (f.comap (sigmaIncl _ _))
    intro b
    simp only [counitAppAppImage, ← FunctorToTypes.map_comp_apply, ← op_comp, CompHausLike.coe_of,
      map_apply, IsTerminal.comp_from, ← map_preimage_eq_image_map]
    change (_ ≫ Y.val.map _) _ = (_ ≫ Y.val.map _) _
    simp only [← g.val.naturality,
      show sigmaIncl (f.comap (sigmaIncl (f.map _) a)) b ≫ sigmaIncl (f.map _) a =
        (sigmaInclIncl f _ a b) ≫ sigmaIncl f (Fiber.mk f _) from rfl]
    simp only [op_comp, Functor.map_comp, types_comp_apply, incl_of_counitAppApp]
    simp only [counitAppAppImage, ← FunctorToTypes.map_comp_apply, ← op_comp, terminal.comp_from]
    rw [mk_image]
    change (X.val.map _ ≫ _) _ = (X.val.map _ ≫ _) _
    simp only [g.val.naturality]
    simp only [types_comp_apply]
    have := map_preimage_eq_image (f := g.val.app _ ∘ f) (a := a)
    simp only [Function.comp_apply] at this
    rw [this]
    apply congrArg
    symm
    convert (b.preimage).prop
    exact (mem_iff_eq_image (g.val.app _ ∘ f) _ _).symm
-- ...
-/
@[simps]
def unit : 𝟭 _ ⟶ functor P hs ⋙ (sheafSections _ _).obj ⟨CompHausLike.of P PUnit.{u+1}⟩ where
  app _ x := LocallyConstant.const _ x
-- ...
-/
@[simps]
noncomputable def adjunction [HasExplicitFiniteCoproducts.{u} P] :
    functor.{u, w} P hs ⊣ (sheafSections _ _).obj ⟨CompHausLike.of P PUnit.{u+1}⟩ where
  unit := unit P hs
  counit := counit P hs
  left_triangle_components := by
    intro X
    simp only [Functor.comp_obj, Functor.id_obj, NatTrans.comp_app, Functor.flip_obj_obj,
      sheafToPresheaf_obj, functor_obj_val, functorToPresheaves_obj_obj, coe_of, whiskerRight_app,
      Functor.associator_hom_app, whiskerLeft_app, Category.id_comp, NatTrans.id_app']
    apply Sheaf.hom_ext
    rw [Sheaf.instCategorySheaf_comp_val, Sheaf.instCategorySheaf_id_val]
    exact adjunction_left_triangle P hs X
  right_triangle_components := by
    intro X
    ext (x : X.val.obj _)
    simp only [Functor.comp_obj, Functor.id_obj, Functor.flip_obj_obj, sheafToPresheaf_obj,
      FunctorToTypes.comp, whiskerLeft_app, unit_app, coe_of, Functor.associator_inv_app,
      functor_obj_val, functorToPresheaves_obj_obj, types_id_apply, whiskerRight_app,
      Functor.flip_obj_map, sheafToPresheaf_map, counit_app_val, counitApp_app, NatTrans.id_app']
    have := CompHausLike.preregular hs
    letI : PreservesFiniteProducts ((sheafToPresheaf (coherentTopology _) _).obj X) :=
      inferInstanceAs (PreservesFiniteProducts (Sheaf.val _))
    apply presheaf_ext ((unit P hs).app _ x)
    intro a
    erw [incl_of_counitAppApp]
    simp only [sheafToPresheaf_obj, unit_app, coe_of, counitAppAppImage, coe_const]
    erw [← map_eq_image _ a ⟨PUnit.unit, by simp [mem_iff_eq_image, ← map_preimage_eq_image]⟩]
    rfl
/-- The functor from sets to condensed sets given by locally constant maps into the set. -/
abbrev functor : Type (u+1) ⥤ CondensedSet.{u} :=
  CompHausLike.LocallyConstant.functor.{u, u+1} (P := fun _ ↦ True)
    (hs := fun _ _ _ ↦ ((CompHaus.effectiveEpi_tfae _).out 0 2).mp)
-- ...
end CondensedSet.LocallyConstant
-- ...
namespace LightCondSet.LocallyConstant
-- ...
/-- The functor from sets to light condensed sets given by locally constant maps into the set. -/
abbrev functor : Type u ⥤ LightCondSet.{u} :=
  CompHausLike.LocallyConstant.functor.{u, u}
    (P := fun X ↦ TotallyDisconnectedSpace X ∧ SecondCountableTopology X)
    (hs := fun _ _ _ ↦ (LightProfinite.effectiveEpi_iff_surjective _).mp)

instance (S : LightProfinite.{u}) (p : S → Prop) :
    HasProp (fun X ↦ TotallyDisconnectedSpace X ∧ SecondCountableTopology X) (Subtype p) :=
  ⟨⟨(inferInstance : TotallyDisconnectedSpace (Subtype p)),
    (inferInstance : SecondCountableTopology {s | p s})⟩⟩
```

### `Mathlib/Condensed/Discrete/Module.lean`

```lean
import Mathlib.CategoryTheory.Sites.ConstantSheaf
import Mathlib.Condensed.Discrete.LocallyConstant
import Mathlib.Condensed.Light.Module
import Mathlib.Condensed.Module
import Mathlib.Topology.LocallyConstant.Algebra
-- ...
universe w u
-- ...
open CategoryTheory LocallyConstant CompHausLike Functor Category Functor Opposite
-- ...
attribute [local instance] ConcreteCategory.instFunLike
-- ...
variable {P : TopCat.{u} → Prop}
-- ...
namespace CompHausLike.LocallyConstantModule
-- ...
variable (R : Type (max u w)) [Ring R]
-- ...
-/
@[simps]
def functorToPresheaves : ModuleCat.{max u w} R ⥤ ((CompHausLike.{u} P)ᵒᵖ ⥤ ModuleCat R) where
  obj X := {
    obj := fun ⟨S⟩ ↦ ModuleCat.of R (LocallyConstant S X)
    map := fun f ↦ comapₗ R f.unop }
  map f := { app := fun S ↦ mapₗ R f }
/-- `CompHausLike.LocallyConstantModule.functorToPresheaves` lands in sheaves. -/
@[simps]
def functor : haveI := CompHausLike.preregular hs
    ModuleCat R ⥤ Sheaf (coherentTopology (CompHausLike.{u} P)) (ModuleCat R) where
  obj X := {
    val := (functorToPresheaves.{w, u} R).obj X
    cond := by
      have := CompHausLike.preregular hs
      apply Presheaf.isSheaf_coherent_of_hasPullbacks_of_comp
        (s := CategoryTheory.forget (ModuleCat R))
      exact ((CompHausLike.LocallyConstant.functor P hs).obj _).cond }
  map f := ⟨(functorToPresheaves.{w, u} R).map f⟩
-- ...
/-- `functorToPresheaves` as a functor to condensed modules. -/
abbrev functor : ModuleCat R ⥤ CondensedMod.{u} R :=
  CompHausLike.LocallyConstantModule.functor.{u+1, u} R
    (fun _ _ _ ↦ ((CompHaus.effectiveEpi_tfae _).out 0 2).mp)
-- ...
/-- Auxiliary definition for `functorIsoDiscrete`. -/
noncomputable def functorIsoDiscreteAux₁ (M : ModuleCat.{u+1} R) :
    M ≅ (ModuleCat.of R (LocallyConstant (CompHaus.of PUnit.{u+1}) M)) where
  hom := constₗ R
  inv := evalₗ R PUnit.unit
-- ...
/-- Auxiliary definition for `functorIsoDiscrete`. -/
noncomputable def functorIsoDiscreteAux₂ (M : ModuleCat R) :
    (discrete _).obj M ≅ (discrete _).obj
      (ModuleCat.of R (LocallyConstant (CompHaus.of PUnit.{u+1}) M)) :=
  (discrete _).mapIso (functorIsoDiscreteAux₁ R M)
-- ...
/-- Auxiliary definition for `functorIsoDiscrete`. -/
noncomputable def functorIsoDiscreteComponents (M : ModuleCat R) :
    (discrete _).obj M ≅ (functor R).obj M :=
  have : (Condensed.forget R).ReflectsIsomorphisms :=
    inferInstanceAs (sheafCompose _ _).ReflectsIsomorphisms
  have : IsIso ((discreteUnderlyingAdj (ModuleCat R)).counit.app ((functor R).obj M)) :=
    isIso_of_reflects_iso _ (Condensed.forget R)
  functorIsoDiscreteAux₂ R M ≪≫ asIso ((discreteUnderlyingAdj _).counit.app ((functor R).obj M))
-- ...
 -/
noncomputable def functorIsoDiscrete : functor R ≅ discrete _ :=
  NatIso.ofComponents (fun M ↦ (functorIsoDiscreteComponents R M).symm) fun f ↦ by
    dsimp
    rw [Iso.eq_inv_comp, ← Category.assoc, Iso.comp_inv_eq]
    dsimp [functorIsoDiscreteComponents]
    rw [assoc, ← Iso.eq_inv_comp,
      ← (discreteUnderlyingAdj (ModuleCat R)).counit_naturality]
    simp only [← assoc]
    congr 1
    rw [← Iso.comp_inv_eq]
    apply Sheaf.hom_ext
    simp [functorIsoDiscreteAux₂, ← Functor.map_comp]
    rfl
-/
noncomputable def adjunction : functor R ⊣ underlying (ModuleCat R) :=
  Adjunction.ofNatIsoLeft (discreteUnderlyingAdj _) (functorIsoDiscrete R).symm
-- ...
end CondensedMod.LocallyConstant
-- ...
namespace LightCondMod.LocallyConstant
-- ...
open LightCondensed
-- ...
variable (R : Type u) [Ring R]
-- ...
/-- `functorToPresheaves` as a functor to light condensed modules. -/
abbrev functor : ModuleCat R ⥤ LightCondMod.{u} R :=
  CompHausLike.LocallyConstantModule.functor.{u, u} R
    (fun _ _ _ ↦ (LightProfinite.effectiveEpi_iff_surjective _).mp)
-- ...
/-- Auxiliary definition for `functorIsoDiscrete`. -/
noncomputable def functorIsoDiscreteAux₁ (M : ModuleCat.{u} R) :
    M ≅ (ModuleCat.of R (LocallyConstant (LightProfinite.of PUnit.{u+1}) M)) where
  hom := constₗ R
  inv := evalₗ R PUnit.unit
-- ...
/-- Auxiliary definition for `functorIsoDiscrete`. -/
noncomputable def functorIsoDiscreteAux₂ (M : ModuleCat.{u} R) :
    (discrete _).obj M ≅ (discrete _).obj
      (ModuleCat.of R (LocallyConstant (LightProfinite.of PUnit.{u+1}) M)) :=
  (discrete _).mapIso (functorIsoDiscreteAux₁ R M)
-- ...
-- Not stating this explicitly causes timeouts below.
instance : HasSheafify (coherentTopology LightProfinite.{u}) (ModuleCat.{u} R) :=
  inferInstance
-- ...
/-- Auxiliary definition for `functorIsoDiscrete`. -/
noncomputable def functorIsoDiscreteComponents (M : ModuleCat R) :
    (discrete _).obj M ≅ (functor R).obj M :=
  have : (LightCondensed.forget R).ReflectsIsomorphisms :=
    inferInstanceAs (sheafCompose _ _).ReflectsIsomorphisms
  have : IsIso ((discreteUnderlyingAdj (ModuleCat R)).counit.app ((functor R).obj M)) :=
    isIso_of_reflects_iso _ (LightCondensed.forget R)
  functorIsoDiscreteAux₂ R M ≪≫ asIso ((discreteUnderlyingAdj _).counit.app ((functor R).obj M))
-- ...
 -/
noncomputable def functorIsoDiscrete : functor R ≅ discrete _ :=
  NatIso.ofComponents (fun M ↦ (functorIsoDiscreteComponents R M).symm) fun f ↦ by
    dsimp
    rw [Iso.eq_inv_comp, ← Category.assoc, Iso.comp_inv_eq]
    dsimp [functorIsoDiscreteComponents]
    rw [Category.assoc, ← Iso.eq_inv_comp,
      ← (discreteUnderlyingAdj (ModuleCat R)).counit_naturality]
    simp only [← assoc]
    congr 1
    rw [← Iso.comp_inv_eq]
    apply Sheaf.hom_ext
    simp [functorIsoDiscreteAux₂, ← Functor.map_comp]
    rfl
 -/
noncomputable def adjunction : functor R ⊣ underlying (ModuleCat R) :=
  Adjunction.ofNatIsoLeft (discreteUnderlyingAdj _) (functorIsoDiscrete R).symm
```

### `Mathlib/Logic/Function/FiberPartition.lean`

```lean
import Mathlib.Data.Set.Basic
-- ...
variable {X Y Z : Type*}
-- ...
namespace Function
-- ...
/-- The indexing set of the partition. -/
def Fiber (f : Y → Z) : Type _ := Set.range (fun (x : Set.range f) ↦ f ⁻¹' {x.val})
-- ...
namespace Fiber
-- ...
-/
noncomputable def image (f : Y → Z) (a : Fiber f) : Z := a.2.choose.1
```

### `Mathlib/Topology/Category/CompHausLike/SigmaComparison.lean`

```lean
import Mathlib.Topology.Category.CompHausLike.Limits
-- ...
universe u w
-- ...
open CategoryTheory Limits
-- ...
namespace CompHausLike
-- ...
variable {P : TopCat.{u} → Prop} [HasExplicitFiniteCoproducts.{u} P]
  (X : (CompHausLike.{u} P)ᵒᵖ ⥤ Type max u w) [PreservesFiniteProducts X]
  {α : Type u} [Finite α] (σ : α → Type u)
  [∀ a, TopologicalSpace (σ a)] [∀ a, CompactSpace (σ a)] [∀ a, T2Space (σ a)]
  [∀ a, HasProp P (σ a)]

instance : HasProp P (Σ (a : α), (σ a)) := HasExplicitFiniteCoproducts.hasProp (fun a ↦ of P (σ a))
-- ...
-/
def sigmaComparison : X.obj ⟨(of P ((a : α) × σ a))⟩ ⟶ ((a : α) → X.obj ⟨of P (σ a)⟩) :=
  fun x a ↦ X.map ⟨Sigma.mk a, continuous_sigmaMk⟩ x
```

### `Mathlib/Topology/Category/LightProfinite/AsLimit.lean`

```lean
import Mathlib.Topology.Category.LightProfinite.Basic
-- ...
noncomputable section
-- ...
open CategoryTheory Limits CompHausLike
-- ...
attribute [local instance] ConcreteCategory.instFunLike
-- ...
namespace LightProfinite
-- ...
universe u
-- ...
variable (S : LightProfinite.{u})
-- ...
/-- The functor `ℕᵒᵖ ⥤ FintypeCat` whose limit is isomorphic to `S`. -/
abbrev fintypeDiagram : ℕᵒᵖ ⥤ FintypeCat := S.toLightDiagram.diagram
-- ...
/-- An abbreviation for `S.fintypeDiagram ⋙ FintypeCat.toProfinite`. -/
abbrev diagram : ℕᵒᵖ ⥤ LightProfinite := S.fintypeDiagram ⋙ FintypeCat.toLightProfinite
-- ...
-/
def asLimitConeAux : Cone S.diagram :=
  let c : Cone (S.diagram ⋙ lightToProfinite) := S.toLightDiagram.cone
  let hc : IsLimit c := S.toLightDiagram.isLimit
  liftLimit hc
/-- An auxiliary isomorphism of cones used to prove that `S.asLimitConeAux` is a limit cone. -/
def isoMapCone : lightToProfinite.mapCone S.asLimitConeAux ≅ S.toLightDiagram.cone :=
  let c : Cone (S.diagram ⋙ lightToProfinite) := S.toLightDiagram.cone
  let hc : IsLimit c := S.toLightDiagram.isLimit
  liftedLimitMapsToOriginal hc
-- ...
/-- A cone over `S.diagram` whose cone point is `S`. -/
def asLimitCone : Cone S.diagram where
  pt := S
  π := {
    app := fun n ↦ (lightToProfiniteFullyFaithful.preimageIso <|
      (Cones.forget _).mapIso S.isoMapCone).inv ≫ S.asLimitConeAux.π.app n
    naturality := fun _ _ _ ↦ by simp only [Category.assoc, S.asLimitConeAux.w]; rfl }
```

### `Mathlib/Topology/FiberPartition.lean`

```lean
import Mathlib.Topology.LocallyConstant.Basic
import Mathlib.Logic.Function.FiberPartition
-- ...
open Function
-- ...
variable {S Y : Type*} (f : S → Y)
-- ...
namespace TopologicalSpace.Fiber
-- ...
variable [TopologicalSpace S]
-- ...
/-- The canonical map from the disjoint union induced by `f` to `S`. -/
@[simps apply]
def sigmaIsoHom : C((x : Fiber f) × x.val, S) where
  toFun | ⟨a, x⟩ => x.val
-- ...
variable (l : LocallyConstant S Y) [CompactSpace S]
-- ...

instance : Finite (Fiber l) :=
  have : Finite (Set.range l) := l.range_finite
  Finite.Set.finite_range _
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
