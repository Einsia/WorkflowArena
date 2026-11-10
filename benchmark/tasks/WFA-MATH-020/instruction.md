> Your working directory is `/workspace`, i.e. the `workspace/` referred to below: a pinned mathlib4 source checkout, initialised as a git repository (start commit `start`). The Lean toolchain, the dependency packages and the prebuilt Mathlib cache are already installed, and `lake build Mathlib` has already been run; there is no network access at run time, so `lake exe cache get` is neither needed nor possible. Deliver your work by editing `/workspace/Mathlib/` and `/workspace/Mathlib.lean` directly. Grading collects only these two paths into the grader's own clean copy, where every file that already exists under `Mathlib/` in the start state is reset to its start-state content (edits to existing Mathlib files are discarded; only new files under `Mathlib/` and your `Mathlib.lean` are kept, and start-state import lines missing from your `Mathlib.lean` are re-added), then runs `lake build Mathlib` and checks the required declarations; changes to any other file are ignored.

# feat: define Riemannian manifolds

You are working in a pinned mathlib4 checkout (`workspace/`; Lean toolchain pinned in
`lean-toolchain`, dependencies in `lake-manifest.json`; the prebuilt
Mathlib build is already installed). Develop the mathematics below as mathlib-quality Lean code.

## Goal

We introduce typeclasses to deal with Riemannian manifolds:

* In a fiber bundle whose fibers are already endowed with an inner product space structure, `[IsContinuousRiemannianBundle F E]` registers the fact the inner product depends continuously on the base point. This is a Prop-valued class, on top of existing data `[∀ x, NormedAddCommGroup (E x)]` `[∀ x, InnerProductSpace ℝ (E x)]`.
* We also register `[IsContMDiffRiemannianBundle n IB F E]` similarly.
* There is an issue when the fibers already have a topological structure (for instance the tangent spaces), because adding an assumption `[∀ x, NormedAddCommGroup (TangentSpace I x)]` would create a diamond. Instead, we introduce another typeclass `[RiemannianBundle E]` containing the data of an inner product space on the fibers, compatible with the preexisting topology. From this class, we register instances of inner product space structures on the fibers, whose topology is defeq to the original one.
* We make sure that registering concrete instances of `[RiemannianBundle E]` registers automatically `[IsContinuousRiemannianBundle F E]` and/or `[IsContMDiffRiemannianBundle n IB F E]` in terms of the regularity of the metric.
* Under the assumptions `[RiemannianBundle (fun (b : M) -> TangentSpace I b)]` and `[EMetricSpace M]`, we register a Prop-valued typeclass `[IsRiemannianManifold I M]` registering the fact that the edist coincides with the infimum of the lengths of paths, measured using the normed space structure in the tangent spaces.

With this design, one can develop the general theory of Riemannian bundles and Riemannian manifolds, and also define concrete instances. When working with a generic Riemannian manifold, the typeclasses will include (in addition to the usual one for manifolds, replacing the topological space one with an emetric space one) the assumptions
`[RiemannianBundle (fun (b : M) -> TangentSpace I b)]` `[IsContinuousRiemannianBundle E (fun (b : M) -> TangentSpace I b)]` `[IsContMDiffRiemannianBundle n I E (fun (b : M) -> TangentSpace I b)]`.

This is a substantial development: in the original history it took 6 separate
contributions. Everything needed beyond the current library is yours to build.

## Required deliverables

After your work, each of the following constants must exist (anywhere under
`Mathlib/`, imported from `Mathlib.lean`) and have exactly this type, as printed
by `#check @name` (grading compares the elaborated types structurally, so notation
and binder names do not matter, but the statement must be the same):

```lean
Bundle.ContMDiffRiemannianMetric :
  {EB : Type u_1} →
  [inst : NormedAddCommGroup EB] →
    [inst_1 : NormedSpace ℝ EB] →
      {HB : Type u_2} →
        [inst_2 : TopologicalSpace HB] →
          ModelWithCorners ℝ EB HB →
            WithTop ℕ∞ →
              {B : Type u_3} →
                [inst : TopologicalSpace B] →
                  [ChartedSpace HB B] →
                    (F : Type u_4) →
                      [inst_4 : NormedAddCommGroup F] →
                        [inst_5 : NormedSpace ℝ F] →
                          (E : B → Type u_5) →
                            [inst_6 : TopologicalSpace (Bundle.TotalSpace F E)] →
                              [inst_7 : (b : B) → TopologicalSpace (E b)] →
                                [inst_8 : (b : B) → AddCommGroup (E b)] →
                                  [inst_9 : (b : B) → Module ℝ (E b)] →
                                    [inst_10 : FiberBundle F E] → [VectorBundle ℝ F E] → Type (max u_3 u_5)
```

```lean
Bundle.RiemannianBundle :
  {B : Type u_1} →
  (E : B → Type u_2) →
    [(b : B) → TopologicalSpace (E b)] →
      [inst : (b : B) → AddCommGroup (E b)] → [(b : B) → Module ℝ (E b)] → Type (max u_1 u_2)
```

```lean
Bundle.instInnerProductSpaceReal :
  {B : Type u_1} →
  {E : B → Type u_2} →
    [inst : (b : B) → TopologicalSpace (E b)] →
      [inst_1 : (b : B) → AddCommGroup (E b)] →
        [inst_2 : (b : B) → Module ℝ (E b)] →
          [inst_3 : ∀ (b : B), IsTopologicalAddGroup (E b)] →
            [inst_4 : ∀ (b : B), ContinuousConstSMul ℝ (E b)] →
              [h : Bundle.RiemannianBundle E] → (b : B) → InnerProductSpace ℝ (E b)
```

```lean
Bundle.instNormedAddCommGroupOfRiemannianBundle :
  {B : Type u_1} →
  {E : B → Type u_2} →
    [inst : (b : B) → TopologicalSpace (E b)] →
      [inst_1 : (b : B) → AddCommGroup (E b)] →
        [inst_2 : (b : B) → Module ℝ (E b)] →
          [∀ (b : B), IsTopologicalAddGroup (E b)] →
            [∀ (b : B), ContinuousConstSMul ℝ (E b)] →
              [h : Bundle.RiemannianBundle E] → (b : B) → NormedAddCommGroup (E b)
```

```lean
EmetricSpace.ofRiemannianMetric :
  {E : Type u_1} →
  [inst : NormedAddCommGroup E] →
    [inst_1 : NormedSpace ℝ E] →
      {H : Type u_2} →
        [inst_2 : TopologicalSpace H] →
          (I : ModelWithCorners ℝ E H) →
            (M : Type u_3) →
              [inst_3 : TopologicalSpace M] →
                [inst_4 : ChartedSpace H M] →
                  [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x] →
                    [inst_6 : IsManifold I 1 M] →
                      [IsContinuousRiemannianBundle E fun x => TangentSpace I x] → [T3Space M] → EMetricSpace M
```

```lean
IsContinuousRiemannianBundle :
  {B : Type u_1} →
  [inst : TopologicalSpace B] →
    (F : Type u_2) →
      [inst_1 : NormedAddCommGroup F] →
        [inst_2 : NormedSpace ℝ F] →
          (E : B → Type u_3) →
            [inst_3 : TopologicalSpace (Bundle.TotalSpace F E)] →
              [inst_4 : (x : B) → NormedAddCommGroup (E x)] →
                [inst_5 : (x : B) → InnerProductSpace ℝ (E x)] →
                  [inst_6 : FiberBundle F E] → [VectorBundle ℝ F E] → Prop
```

```lean
IsRiemannianManifold :
  {E : Type u_1} →
  [inst : NormedAddCommGroup E] →
    [inst_1 : NormedSpace ℝ E] →
      {H : Type u_2} →
        [inst_2 : TopologicalSpace H] →
          (I : ModelWithCorners ℝ E H) →
            (M : Type u_3) →
              [inst_3 : TopologicalSpace M] →
                [PseudoEMetricSpace M] →
                  [inst_5 : ChartedSpace H M] → [Bundle.RiemannianBundle fun x => TangentSpace I x] → Prop
```

```lean
Manifold.riemannianEDist :
  {E : Type u_1} →
  [inst : NormedAddCommGroup E] →
    [inst_1 : NormedSpace ℝ E] →
      {H : Type u_2} →
        [inst_2 : TopologicalSpace H] →
          (I : ModelWithCorners ℝ E H) →
            {M : Type u_3} →
              [inst_3 : TopologicalSpace M] →
                [inst_4 : ChartedSpace H M] → [(x : M) → ENorm (TangentSpace I x)] → M → M → ENNReal
```

```lean
PseudoEmetricSpace.ofRiemannianMetric :
  {E : Type u_1} →
  [inst : NormedAddCommGroup E] →
    [inst_1 : NormedSpace ℝ E] →
      {H : Type u_2} →
        [inst_2 : TopologicalSpace H] →
          (I : ModelWithCorners ℝ E H) →
            (M : Type u_3) →
              [inst_3 : TopologicalSpace M] →
                [inst_4 : ChartedSpace H M] →
                  [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x] →
                    [inst_6 : IsManifold I 1 M] →
                      [IsContinuousRiemannianBundle E fun x => TangentSpace I x] →
                        [RegularSpace M] → PseudoEMetricSpace M
```

```lean
enorm_tangentSpace_vectorSpace :
  ∀ {F : Type u_1} [inst : NormedAddCommGroup F] [inst_1 : InnerProductSpace ℝ F]
  {x : F} {v : TangentSpace (modelWithCornersSelf ℝ F) x}, ‖v‖ₑ = ‖v‖ₑ
```

```lean
eventually_enorm_mfderivWithin_symm_extChartAt_lt :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E]
  [inst_1 : NormedSpace ℝ E] {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3}
  [inst_3 : TopologicalSpace M] [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x]
  [inst_6 : IsManifold I 1 M] [IsContinuousRiemannianBundle E fun x => TangentSpace I x] (x : M),
  ∃ C > 0,
    ∀ᶠ (y : E) in nhdsWithin (↑(extChartAt I x) x) (Set.range ↑I),
      ‖mfderivWithin (modelWithCornersSelf ℝ E) I (↑(PartialEquiv.symm (extChartAt I x))) (Set.range ↑I) y‖ₑ < ↑C
```

```lean
eventually_enorm_mfderiv_extChartAt_lt :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E] [inst_1 : NormedSpace ℝ E]
  {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3} [inst_3 : TopologicalSpace M]
  [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x] [inst_6 : IsManifold I 1 M]
  [IsContinuousRiemannianBundle E fun x => TangentSpace I x] (x : M),
  ∃ C > 0, ∀ᶠ (y : M) in nhds x, ‖mfderiv I (modelWithCornersSelf ℝ E) (↑(extChartAt I x)) y‖ₑ < ↑C
```

```lean
eventually_norm_mfderivWithin_symm_extChartAt_comp_lt :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E]
  [inst_1 : NormedSpace ℝ E] {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3}
  [inst_3 : TopologicalSpace M] [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x]
  [inst_6 : IsManifold I 1 M] [IsContinuousRiemannianBundle E fun x => TangentSpace I x] (x : M),
  ∃ C > 0,
    ∀ᶠ (y : M) in nhds x,
      ‖mfderivWithin (modelWithCornersSelf ℝ E) I (↑(PartialEquiv.symm (extChartAt I x))) (Set.range ↑I)
            (↑(extChartAt I x) y)‖ <
        C
```

```lean
eventually_norm_mfderivWithin_symm_extChartAt_lt :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E]
  [inst_1 : NormedSpace ℝ E] {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3}
  [inst_3 : TopologicalSpace M] [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x]
  [inst_6 : IsManifold I 1 M] [IsContinuousRiemannianBundle E fun x => TangentSpace I x] (x : M),
  ∃ C > 0,
    ∀ᶠ (y : E) in nhdsWithin (↑(extChartAt I x) x) (Set.range ↑I),
      ‖mfderivWithin (modelWithCornersSelf ℝ E) I (↑(PartialEquiv.symm (extChartAt I x))) (Set.range ↑I) y‖ < C
```

```lean
eventually_norm_mfderiv_extChartAt_lt :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E] [inst_1 : NormedSpace ℝ E]
  {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3} [inst_3 : TopologicalSpace M]
  [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x] [inst_6 : IsManifold I 1 M]
  [IsContinuousRiemannianBundle E fun x => TangentSpace I x] (x : M),
  ∃ C > 0, ∀ᶠ (y : M) in nhds x, ‖mfderiv I (modelWithCornersSelf ℝ E) (↑(extChartAt I x)) y‖ < C
```

```lean
eventually_riemannianEDist_le_edist_extChartAt :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E]
  [inst_1 : NormedSpace ℝ E] {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3}
  [inst_3 : TopologicalSpace M] [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x]
  [inst_6 : IsManifold I 1 M] [IsContinuousRiemannianBundle E fun x => TangentSpace I x] (x : M),
  ∃ C > 0, ∀ᶠ (y : M) in nhds x, Manifold.riemannianEDist I x y ≤ ↑C * edist (↑(extChartAt I x) x) (↑(extChartAt I x) y)
```

```lean
eventually_riemmanianEDist_lt :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E] [inst_1 : NormedSpace ℝ E]
  {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3} [inst_3 : TopologicalSpace M]
  [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x] [inst_6 : IsManifold I 1 M]
  [IsContinuousRiemannianBundle E fun x => TangentSpace I x] (x : M) {c : ENNReal},
  0 < c → ∀ᶠ (y : M) in nhds x, Manifold.riemannianEDist I x y < c
```

```lean
instRiemannianBundleTangentSpaceRealModelWithCornersSelf :
  {F : Type u_1} →
  [inst : NormedAddCommGroup F] →
    [inst_1 : InnerProductSpace ℝ F] → Bundle.RiemannianBundle fun x => TangentSpace (modelWithCornersSelf ℝ F) x
```

```lean
lintegral_fderiv_lineMap_eq_edist :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E] [inst_1 : NormedSpace ℝ E]
  {x y : E},
  ∫⁻ (t : ℝ) in Set.Icc 0 1, ‖(fderivWithin ℝ (⇑(ContinuousAffineMap.lineMap x y)) (Set.Icc 0 1) t) 1‖ₑ = edist x y
```

```lean
nnnorm_tangentSpace_vectorSpace :
  ∀ {F : Type u_1} [inst : NormedAddCommGroup F] [inst_1 : InnerProductSpace ℝ F]
  {x : F} {v : TangentSpace (modelWithCornersSelf ℝ F) x}, ‖v‖₊ = ‖v‖₊
```

```lean
norm_tangentSpace_vectorSpace :
  ∀ {F : Type u_1} [inst : NormedAddCommGroup F] [inst_1 : InnerProductSpace ℝ F] {x : F}
  {v : TangentSpace (modelWithCornersSelf ℝ F) x}, ‖v‖ = ‖v‖
```

```lean
normedAddCommGroupTangentSpaceVectorSpace :
  {E : Type u_1} →
  [inst : NormedAddCommGroup E] →
    [inst_1 : NormedSpace ℝ E] → (x : E) → NormedAddCommGroup (TangentSpace (modelWithCornersSelf ℝ E) x)
```

```lean
normedSpaceTangentSpaceVectorSpace :
  {E : Type u_1} →
  [inst : NormedAddCommGroup E] →
    [inst_1 : NormedSpace ℝ E] → (x : E) → NormedSpace ℝ (TangentSpace (modelWithCornersSelf ℝ E) x)
```

```lean
riemannianMetricVectorSpace :
  (F : Type u_1) →
  [inst : NormedAddCommGroup F] →
    [inst_1 : InnerProductSpace ℝ F] →
      Bundle.ContMDiffRiemannianMetric (modelWithCornersSelf ℝ F) ⊤ F fun x => TangentSpace (modelWithCornersSelf ℝ F) x
```

```lean
setOf_riemmanianEDist_lt_subset_nhds :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E] [inst_1 : NormedSpace ℝ E]
  {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3} [inst_3 : TopologicalSpace M]
  [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x] [inst_6 : IsManifold I 1 M]
  [IsContinuousRiemannianBundle E fun x => TangentSpace I x] [RegularSpace M] {x : M} {s : Set M},
  s ∈ nhds x → ∃ c > 0, {y | Manifold.riemannianEDist I x y < ↑c} ⊆ s
```

```lean
setOf_riemmanianEDist_lt_subset_nhds' :
  ∀ {E : Type u_1} [inst : NormedAddCommGroup E] [inst_1 : NormedSpace ℝ E]
  {H : Type u_2} [inst_2 : TopologicalSpace H] (I : ModelWithCorners ℝ E H) {M : Type u_3} [inst_3 : TopologicalSpace M]
  [inst_4 : ChartedSpace H M] [inst_5 : Bundle.RiemannianBundle fun x => TangentSpace I x] [inst_6 : IsManifold I 1 M]
  [IsContinuousRiemannianBundle E fun x => TangentSpace I x] [RegularSpace M] {x : M} {s : Set M},
  s ∈ nhds x → ∃ c > 0, {y | Manifold.riemannianEDist I x y < c} ⊆ s
```

## Pinned reference definitions

The excerpts below, taken from the reference development, contain every pinned declaration (32
constants including the auxiliary ones Lean generates for them, such as constructors, recursors,
projections and `match_` functions). Reproduce these declarations exactly. Using a file with the same
path, imports and `variable`/`open` context is the safest way to get an identical elaborated value
(for example, instance resolution depends on the imports). `-- ...` marks omitted parts of the
reference file (other declarations and proofs, which you develop yourself).

### `Mathlib/Geometry/Manifold/Instances/Icc.lean`

```lean
import Mathlib.Analysis.InnerProductSpace.Calculus
import Mathlib.Geometry.Manifold.ContMDiff.Basic
import Mathlib.Geometry.Manifold.Instances.Real
import Mathlib.Geometry.Manifold.MFDeriv.FDeriv
-- ...
open Set
open scoped Manifold Topology
-- ...
noncomputable section
-- ...
variable
  {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
  {H : Type*} [TopologicalSpace H] {I : ModelWithCorners ℝ E H} {n : WithTop ℕ∞}
  {M : Type*} [TopologicalSpace M] [ChartedSpace H M]

instance (x : ℝ) : One (TangentSpace 𝓘(ℝ) x) where
  one := (1 : ℝ)

/-- Unit vector in the tangent space to a segment, as the image of the unit vector in the real line
under the canonical projection. It is also mapped to the unit vector in the real line through
the canonical injection, see `mfderiv_subtype_coe_Icc_one`.

Note that one can not abuse defeqs for this definition: this is *not* the same as the vector
`fun _ ↦ 1` in `EuclideanSpace ℝ (Fin 1)` through defeqs, as one of the charts of `Icc x y` is
orientation-reversing. -/
irreducible_def oneTangentSpaceIcc {x y : ℝ} [h : Fact (x < y)] (z : Icc x y) :
    TangentSpace (𝓡∂ 1) z :=
  mfderivWithin 𝓘(ℝ) (𝓡∂ 1) (Set.projIcc x y h.out.le) (Icc x y) z 1

instance {x y : ℝ} [h : Fact (x < y)] (z : Icc x y) : One (TangentSpace (𝓡∂ 1) z) where
  one := oneTangentSpaceIcc z
```

### `Mathlib/Geometry/Manifold/Riemannian/Basic.lean`

```lean
import Mathlib.Geometry.Manifold.MFDeriv.Atlas
import Mathlib.Geometry.Manifold.Riemannian.PathELength
import Mathlib.Geometry.Manifold.VectorBundle.Riemannian
import Mathlib.Geometry.Manifold.VectorBundle.Tangent
import Mathlib.MeasureTheory.Integral.IntervalIntegral.ContDiff
-- ...
open Bundle Bornology Set MeasureTheory Manifold Filter
open scoped ENNReal ContDiff Topology
-- ...
local notation "⟪" x ", " y "⟫" => inner ℝ x y
-- ...
noncomputable section
-- ...
variable
  {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
  {H : Type*} [TopologicalSpace H] {I : ModelWithCorners ℝ E H} {n : WithTop ℕ∞}
  {M : Type*} [TopologicalSpace M] [ChartedSpace H M]
-- ...
section
-- ...
variable [PseudoEMetricSpace M] [ChartedSpace H M]
  [RiemannianBundle (fun (x : M) ↦ TangentSpace I x)]
-- ...
variable (I M) in
/-- Consider a manifold in which the tangent spaces are already endowed with an inner product, and
the space is already endowed with an extended distance. We say that this is a Riemannian manifold
if the distance is given by the infimum of the lengths of `C^1` paths, measured using the norm in
the tangent spaces.

This is a `Prop` valued typeclass, on top of existing data.

If you need to *construct* a distance using a Riemannian structure,
see `EmetricSpace.ofRiemannianMetric`. -/
class IsRiemannianManifold : Prop where
  out (x y : M) : edist x y = riemannianEDist I x y
-- ...
end
-- ...
section
-- ...
variable {F : Type*} [NormedAddCommGroup F] [InnerProductSpace ℝ F]
-- ...
variable (F) in
/-- The standard riemannian metric on a vector space with an inner product, given by this inner
product on each tangent space. -/
noncomputable def riemannianMetricVectorSpace :
    ContMDiffRiemannianMetric 𝓘(ℝ, F) ω F (fun (x : F) ↦ TangentSpace 𝓘(ℝ, F) x) where
  inner x := (innerSL ℝ (E := F) : F →L[ℝ] F →L[ℝ] ℝ)
  symm x v w := real_inner_comm  _ _
  pos x v hv := real_inner_self_pos.2 hv
  isVonNBounded x := by
    change IsVonNBounded ℝ {v : F | ⟪v, v⟫ < 1}
    have : Metric.ball (0 : F) 1 = {v : F | ⟪v, v⟫ < 1} := by
      ext v
      simp only [Metric.mem_ball, dist_zero_right, norm_eq_sqrt_re_inner (𝕜 := ℝ),
        RCLike.re_to_real, Set.mem_setOf_eq]
      conv_lhs => rw [show (1 : ℝ) = √ 1 by simp]
      rw [Real.sqrt_lt_sqrt_iff]
      exact real_inner_self_nonneg
    rw [← this]
    exact NormedSpace.isVonNBounded_ball ℝ F 1
  contMDiff := by
    intro x
    rw [contMDiffAt_section]
    convert contMDiffAt_const (c := innerSL ℝ)
    ext v w
    simp? [hom_trivializationAt_apply, ContinuousLinearMap.inCoordinates,
        Trivialization.linearMapAt_apply] says
      simp only [hom_trivializationAt_apply, ContinuousLinearMap.inCoordinates,
        TangentBundle.symmL_model_space, ContinuousLinearMap.coe_comp',
        Trivialization.continuousLinearMapAt_apply, Function.comp_apply,
        Trivialization.linearMapAt_apply, hom_trivializationAt_baseSet,
        TangentBundle.trivializationAt_baseSet, PartialHomeomorph.refl_partialEquiv,
        PartialEquiv.refl_source, PartialHomeomorph.singletonChartedSpace_chartAt_eq,
        Trivial.fiberBundle_trivializationAt', Trivial.trivialization_baseSet, inter_self, mem_univ,
        ↓reduceIte, Trivial.trivialization_apply]
    rfl

noncomputable instance : RiemannianBundle (fun (x : F) ↦ TangentSpace 𝓘(ℝ, F) x) :=
  ⟨(riemannianMetricVectorSpace F).toRiemannianMetric⟩
-- ...
open MeasureTheory Measure
-- ...
end
-- ...
section
-- ...
open Manifold Metric
open scoped NNReal
-- ...
variable [RiemannianBundle (fun (x : M) ↦ TangentSpace I x)]
  [IsManifold I 1 M] [IsContinuousRiemannianBundle E (fun (x : M) ↦ TangentSpace I x)]

/-- Register on the tangent space to a normed vector space the same `NormedAddCommGroup` structure
as in the vector space.

Should not be a global instance, as it does not coincide definitionally with the Riemannian
structure for inner product spaces, but can be activated locally. -/
def normedAddCommGroupTangentSpaceVectorSpace (x : E) :
    NormedAddCommGroup (TangentSpace 𝓘(ℝ, E) x) :=
  inferInstanceAs (NormedAddCommGroup E)
-- ...
attribute [local instance] normedAddCommGroupTangentSpaceVectorSpace

/-- Register on the tangent space to a normed vector space the same `NormedSpace` structure
as in the vector space.

Should not be a global instance, as it does not coincide definitionally with the Riemannian
structure for inner product spaces, but can be activated locally. -/
def normedSpaceTangentSpaceVectorSpace (x : E) : NormedSpace ℝ (TangentSpace 𝓘(ℝ, E) x) :=
  inferInstanceAs (NormedSpace ℝ E)
-- ...
attribute [local instance] normedSpaceTangentSpaceVectorSpace
-- ...
variable (I)
-- ...
variable (M) in
/-- The pseudoemetric space structure associated to a Riemannian metric on a manifold. Designed
so that the topology is defeq to the original one.

This should only be used when constructing data in specific situtations. To develop the theory,
one should rather assume that there is an already existing emetric space structure, which satisfies
additionally the predicate `IsRiemannianManifold I M`. -/
@[reducible] def PseudoEmetricSpace.ofRiemannianMetric [RegularSpace M] : PseudoEMetricSpace M :=
  PseudoEmetricSpace.ofEdistOfTopology (riemannianEDist I (M := M))
    (fun _ ↦ riemannianEDist_self)
    (fun _ _ ↦ riemannianEDist_comm)
    (fun _ _ _ ↦ riemannianEDist_triangle)
    (fun x ↦ (basis_sets (𝓝 x)).to_hasBasis'
      (fun _ hs ↦ setOf_riemmanianEDist_lt_subset_nhds' I hs)
      (fun _ hc ↦ eventually_riemmanianEDist_lt I x hc))
-- ...
variable (M) in
/-- The emetric space structure associated to a Riemannian metric on a manifold. Designed
so that the topology is defeq to the original one.

This should only be used when constructing data in specific situations. To develop the theory,
one should rather assume that there is an already existing emetric space structure, which satisfies
additionally the predicate `IsRiemannianManifold I M`. -/
@[reducible] def EmetricSpace.ofRiemannianMetric [T3Space M] : EMetricSpace M :=
  letI : PseudoEMetricSpace M := PseudoEmetricSpace.ofRiemannianMetric I M
  EMetricSpace.ofT0PseudoEMetricSpace M
```

### `Mathlib/Geometry/Manifold/Riemannian/PathELength.lean`

```lean
import Mathlib.Analysis.Calculus.AddTorsor.AffineMap
import Mathlib.Analysis.SpecialFunctions.SmoothTransition
import Mathlib.Geometry.Manifold.ContMDiff.NormedSpace
import Mathlib.Geometry.Manifold.Instances.Icc
import Mathlib.MeasureTheory.Constructions.UnitInterval
import Mathlib.MeasureTheory.Function.JacobianOneDim
-- ...
open Set MeasureTheory
open scoped Manifold ENNReal ContDiff Topology
-- ...
noncomputable section
-- ...
variable
  {E : Type*} [NormedAddCommGroup E] [NormedSpace ℝ E]
  {H : Type*} [TopologicalSpace H] {I : ModelWithCorners ℝ E H} {n : WithTop ℕ∞}
  {M : Type*} [TopologicalSpace M] [ChartedSpace H M]
-- ...
namespace Manifold
-- ...
variable [∀ (x : M), ENorm (TangentSpace I x)] {a b c a' b' : ℝ} {γ γ' : ℝ → M}
-- ...
attribute [local instance] Measure.Subtype.measureSpace
-- ...
open MeasureTheory
-- ...
variable [∀ (x : M), ENormSMulClass ℝ (TangentSpace I x)]
-- ...
section
-- ...
variable {x y z : M} {r : ℝ≥0∞} {a b : ℝ}
-- ...
variable (I) in
/-- The Riemannian extended distance between two points, in a manifold where the tangent spaces
have an extended norm, defined as the infimum of the lengths of `C^1` paths between the points. -/
noncomputable irreducible_def riemannianEDist (x y : M) : ℝ≥0∞ :=
  ⨅ (γ : Path x y) (_ : ContMDiff (𝓡∂ 1) I 1 γ), ∫⁻ x, ‖mfderiv (𝓡∂ 1) I γ x 1‖ₑ
```

### `Mathlib/Geometry/Manifold/VectorBundle/Riemannian.lean`

```lean
import Mathlib.Geometry.Manifold.VectorBundle.Hom
import Mathlib.Topology.VectorBundle.Riemannian
-- ...
open Manifold Bundle ContinuousLinearMap ENat Bornology
open scoped ContDiff Topology
-- ...
section
-- ...
variable
  {EB : Type*} [NormedAddCommGroup EB] [NormedSpace ℝ EB]
  {HB : Type*} [TopologicalSpace HB] {IB : ModelWithCorners ℝ EB HB} {n n' : WithTop ℕ∞}
  {B : Type*} [TopologicalSpace B] [ChartedSpace HB B]
  {F : Type*} [NormedAddCommGroup F] [NormedSpace ℝ F]
  {E : B → Type*} [TopologicalSpace (TotalSpace F E)] [∀ x, NormedAddCommGroup (E x)]
  [∀ x, InnerProductSpace ℝ (E x)]
  [FiberBundle F E] [VectorBundle ℝ F E]
-- ...
local notation "⟪" x ", " y "⟫" => inner ℝ x y
-- ...
section Trivial
-- ...
variable {F₁ : Type*} [NormedAddCommGroup F₁] [InnerProductSpace ℝ F₁]
-- ...
end Trivial
-- ...
section ContMDiff
-- ...
variable
  {EM : Type*} [NormedAddCommGroup EM] [NormedSpace ℝ EM]
  {HM : Type*} [TopologicalSpace HM] {IM : ModelWithCorners ℝ EM HM}
  {M : Type*} [TopologicalSpace M] [ChartedSpace HM M]
  [h : IsContMDiffRiemannianBundle IB n F E]
  {b : M → B} {v w : ∀ x, E (b x)} {s : Set M} {x : M}
-- ...
end ContMDiff
-- ...
end
-- ...
namespace Bundle
-- ...
section Construction
-- ...
variable
  {EB : Type*} [NormedAddCommGroup EB] [NormedSpace ℝ EB]
  {HB : Type*} [TopologicalSpace HB] {IB : ModelWithCorners ℝ EB HB} {n n' : WithTop ℕ∞}
  {B : Type*} [TopologicalSpace B] [ChartedSpace HB B]
  {F : Type*} [NormedAddCommGroup F] [NormedSpace ℝ F]
  {E : B → Type*} [TopologicalSpace (TotalSpace F E)]
  [∀ b, TopologicalSpace (E b)] [∀ b, AddCommGroup (E b)] [∀ b, Module ℝ (E b)]
  [∀ b, IsTopologicalAddGroup (E b)] [∀ b, ContinuousConstSMul ℝ (E b)]
  [FiberBundle F E] [VectorBundle ℝ F E]
-- ...
variable (IB n F E) in
/-- A family of inner product space structures on the fibers of a fiber bundle, defining the same
topology as the already existing one, and varying continuously with the base point. See also
`ContinuousRiemannianMetric` for a continuous version.

This structure is used through `RiemannianBundle` for typeclass inference, to register the inner
product space structure on the fibers without creating diamonds. -/
structure ContMDiffRiemannianMetric where
  /-- The scalar product along the fibers of the bundle. -/
  inner (b : B) : E b →L[ℝ] E b →L[ℝ] ℝ
  symm (b : B) (v w : E b) : inner b v w = inner b w v
  pos (b : B) (v : E b) (hv : v ≠ 0) : 0 < inner b v v
  isVonNBounded (b : B) : IsVonNBounded ℝ {v : E b | inner b v v < 1}
  contMDiff : ContMDiff IB (IB.prod 𝓘(ℝ, F →L[ℝ] F →L[ℝ] ℝ)) n
    (fun b ↦ TotalSpace.mk' (F →L[ℝ] F →L[ℝ] ℝ) b (inner b))

/-- A smooth Riemannian metric defines in particular a continuous Riemannian metric. -/
def ContMDiffRiemannianMetric.toContinuousRiemannianMetric
    (g : ContMDiffRiemannianMetric IB n F E) : ContinuousRiemannianMetric F E :=
  { g with continuous := g.contMDiff.continuous }

/-- A smooth Riemannian metric defines in particular a Riemannian metric. -/
def ContMDiffRiemannianMetric.toRiemannianMetric
    (g : ContMDiffRiemannianMetric IB n F E) : RiemannianMetric E :=
  g.toContinuousRiemannianMetric.toRiemannianMetric
```

### `Mathlib/Topology/VectorBundle/Riemannian.lean`

```lean
import Mathlib.Analysis.InnerProductSpace.LinearMap
import Mathlib.Topology.VectorBundle.Constructions
import Mathlib.Topology.VectorBundle.Hom
-- ...
open Bundle ContinuousLinearMap Filter
open scoped Topology
-- ...
variable
  {B : Type*} [TopologicalSpace B]
  {F : Type*} [NormedAddCommGroup F] [NormedSpace ℝ F]
  {E : B → Type*} [TopologicalSpace (TotalSpace F E)] [∀ x, NormedAddCommGroup (E x)]
  [∀ x, InnerProductSpace ℝ (E x)]
  [FiberBundle F E] [VectorBundle ℝ F E]
-- ...
local notation "⟪" x ", " y "⟫" => inner ℝ x y
-- ...
variable (F E) in
/-- Consider a real vector bundle in which each fiber is endowed with an inner product.
We say that the bundle is *Riemannian* if the inner product depends continuously on the base point.
This assumption is spelled `IsContinuousRiemannianBundle F E` where `F` is the model fiber,
and `E : B → Type*` is the bundle. -/
class IsContinuousRiemannianBundle : Prop where
  /-- There exists a bilinear form, depending continuously on the basepoint and defining the
  inner product in the fibers. This is expressed as an existence statement so that it is Prop-valued
  in terms of existing data, the inner product on the fibers and the fiber bundle structure. -/
  exists_continuous : ∃ g : (Π x, E x →L[ℝ] E x →L[ℝ] ℝ),
    Continuous (fun (x : B) ↦ TotalSpace.mk' (F →L[ℝ] F →L[ℝ] ℝ) x (g x))
    ∧ ∀ (x : B) (v w : E x), ⟪v, w⟫ = g x v w
-- ...
section Trivial
-- ...
variable {F₁ : Type*} [NormedAddCommGroup F₁] [InnerProductSpace ℝ F₁]
-- ...
end Trivial
-- ...
section Continuous
-- ...
variable
  {M : Type*} [TopologicalSpace M] [h : IsContinuousRiemannianBundle F E]
  {b : M → B} {v w : ∀ x, E (b x)} {s : Set M} {x : M}
-- ...
variable (F E)
-- ...
end Continuous
-- ...
namespace Bundle
-- ...
section Construction
-- ...
variable
  {B : Type*} [TopologicalSpace B]
  {F : Type*} [NormedAddCommGroup F] [NormedSpace ℝ F]
  {E : B → Type*} [TopologicalSpace (TotalSpace F E)]
  [∀ b, TopologicalSpace (E b)] [∀ b, AddCommGroup (E b)] [∀ b, Module ℝ (E b)]
  [∀ b, IsTopologicalAddGroup (E b)] [∀ b, ContinuousConstSMul ℝ (E b)]
  [FiberBundle F E] [VectorBundle ℝ F E]
-- ...
open Bornology
-- ...
variable (E) in
/-- A family of inner product space structures on the fibers of a fiber bundle, defining the same
topology as the already existing one. This family is not assumed to be continuous or smooth: to
guarantee continuity, resp. smoothness, of the inner product as a function of the base point,
use `ContinuousRiemannianMetric` or `ContMDiffRiemannianMetric`.

This structure is used through `RiemannianBundle` for typeclass inference, to register the inner
product space structure on the fibers without creating diamonds. -/
structure RiemannianMetric where
  /-- The inner product along the fibers of the bundle. -/
  inner (b : B) : E b →L[ℝ] E b →L[ℝ] ℝ
  symm (b : B) (v w : E b) : inner b v w = inner b w v
  pos (b : B) (v : E b) (hv : v ≠ 0) : 0 < inner b v v
  /-- The continuity at `0` is automatic when `E b` is isomorphic to a normed space, but since
  we are not making this assumption here we have to include it. -/
  continuousAt (b : B) : ContinuousAt (fun (v : E b) ↦ inner b v v) 0
  isVonNBounded (b : B) : IsVonNBounded ℝ {v : E b | inner b v v < 1}

/-- `Core structure associated to a family of inner products on the fibers of a fiber bundle. This
is an auxiliary construction to endow the fibers with an inner product space structure without
creating diamonds.

Warning: Do not use this `Core` structure if the space you are interested in already has a norm
instance defined on it, otherwise this will create a second non-defeq norm instance! -/
@[reducible] noncomputable def RiemannianMetric.toCore (g : RiemannianMetric E) (b : B) :
    InnerProductSpace.Core ℝ (E b) where
  inner v w := g.inner b v w
  conj_inner_symm v w := g.symm b w v
  re_inner_nonneg v := by
    rcases eq_or_ne v 0 with rfl | hv
    · simp
    · simpa using (g.pos b v hv).le
  add_left v w x := by simp
  smul_left c v := by simp
  definite v h := by contrapose! h; exact (g.pos b v h).ne'
-- ...
variable (E) in
/-- Class used to create an inner product structure space on the fibers of a fiber bundle, without
creating diamonds. Use as follows:
* `instance : RiemannianBundle E := ⟨g⟩` where `g : RiemannianMetric E` registers the inner product
space on the fibers;
* `instance : RiemannianBundle E := ⟨g.toRiemannianMetric⟩` where
`g : ContinuousRiemannianMetric F E` registers the inner product space on the fibers, and the fact
that it varies continuously (i.e., a `[IsContinuousRiemannianBundle]` instance).
* `instance : RiemannianBundle E := ⟨g.toRiemannianMetric⟩` where
`g : ContMDiffRiemannianMetric IB n F E` registers the inner product space on the fibers, and the
fact that it varies smoothly (and continuously), i.e., `[IsContMDiffRiemannianBundle]` and
`[IsContinuousRiemannianBundle]` instances.
-/
class RiemannianBundle where
  /-- The family of inner products on the fibers -/
  g : RiemannianMetric E
-- ...
We use 80 as this is rather specialized, so we want other paths to be tried first typically. -/
noncomputable instance (priority := 80) [h : RiemannianBundle E] (b : B) :
    NormedAddCommGroup (E b) :=
  (h.g.toCore b).toNormedAddCommGroupOfTopology (h.g.continuousAt b) (h.g.isVonNBounded b)
We use 80 as this is rather specialized, so we want other paths to be tried first typically. -/
noncomputable instance (priority := 80) [h : RiemannianBundle E] (b : B) :
    InnerProductSpace ℝ (E b) :=
  .ofCoreOfTopology (h.g.toCore b) (h.g.continuousAt b) (h.g.isVonNBounded b)
variable (F E) in
/-- A family of inner product space structures on the fibers of a fiber bundle, defining the same
topology as the already existing one, and varying continuously with the base point. See also
`ContMDiffRiemannianMetric` for a smooth version.

This structure is used through `RiemannianBundle` for typeclass inference, to register the inner
product space structure on the fibers without creating diamonds. -/
structure ContinuousRiemannianMetric where
  /-- The inner product along the fibers of the bundle. -/
  inner (b : B) : E b →L[ℝ] E b →L[ℝ] ℝ
  symm (b : B) (v w : E b) : inner b v w = inner b w v
  pos (b : B) (v : E b) (hv : v ≠ 0) : 0 < inner b v v
  isVonNBounded (b : B) : IsVonNBounded ℝ {v : E b | inner b v v < 1}
  continuous : Continuous (fun (b : B) ↦ TotalSpace.mk' (F →L[ℝ] F →L[ℝ] ℝ) b (inner b))

/-- A continuous Riemannian metric is in particular a Riemannian metric. -/
def ContinuousRiemannianMetric.toRiemannianMetric (g : ContinuousRiemannianMetric F E) :
    RiemannianMetric E where
  inner := g.inner
  symm := g.symm
  pos := g.pos
  isVonNBounded := g.isVonNBounded
  continuousAt b := by
    -- Continuity of bilinear maps is only true on normed spaces. As `F` is a normed space by
    -- assumption, we transfer everything to `F` and argue there.
    let e : E b ≃L[ℝ] F := Trivialization.continuousLinearEquivAt ℝ (trivializationAt F E b) _
      (FiberBundle.mem_baseSet_trivializationAt' b)
    let m : (E b →L[ℝ] E b →L[ℝ] ℝ) ≃L[ℝ] (F →L[ℝ] F →L[ℝ] ℝ) :=
      e.arrowCongr (e.arrowCongr (ContinuousLinearEquiv.refl ℝ ℝ ))
    have A (v : E b) : g.inner b v v = ((fun w ↦ m (g.inner b) w w) ∘ e) v := by simp [m]
    simp only [A]
    fun_prop
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
