> Your working directory is `/workspace`, i.e. the `workspace/` referred to below: a pinned mathlib4 source checkout, initialised as a git repository (start commit `start`). The Lean toolchain, the dependency packages and the prebuilt Mathlib cache are already installed, and `lake build Mathlib` has already been run; there is no network access at run time, so `lake exe cache get` is neither needed nor possible. Deliver your work by editing `/workspace/Mathlib/` and `/workspace/Mathlib.lean` directly. Grading collects only these two paths into the grader's own clean copy, where every file that already exists under `Mathlib/` in the start state is reset to its start-state content (edits to existing Mathlib files are discarded; only new files under `Mathlib/` and your `Mathlib.lean` are kept, and start-state import lines missing from your `Mathlib.lean` are re-added), then runs `lake build Mathlib` and checks the required declarations; changes to any other file are ignored.

# feat: the index of Fredholm operators is locally constant

You are working in a pinned mathlib4 checkout (`workspace/`; Lean toolchain pinned in
`lean-toolchain`, dependencies in `lake-manifest.json`; the prebuilt
Mathlib build is already installed). Develop the mathematics below as mathlib-quality Lean code.

## Goal

Formalize in mathlib: the index of Fredholm operators is locally constant. The required deliverables below pin down the exact statements.

This is a substantial development: in the original history it took 9 separate
contributions. Everything needed beyond the current library is yours to build.

## Required deliverables

After your work, each of the following constants must exist (anywhere under
`Mathlib/`, imported from `Mathlib.lean`) and have exactly this type, as printed
by `#check @name` (grading compares the elaborated types structurally, so notation
and binder names do not matter, but the statement must be the same):

```lean
ContinuousLinearMap.IsFredholm :
  {𝕜 : Type u_1} →
  {E : Type u_2} →
    {F : Type u_3} →
      [inst : NontriviallyNormedField 𝕜] →
        [inst_1 : AddCommGroup E] →
          [inst_2 : AddCommGroup F] →
            [inst_3 : Module 𝕜 E] →
              [inst_4 : Module 𝕜 F] → [inst_5 : TopologicalSpace E] → [inst_6 : TopologicalSpace F] → (E →L[𝕜] F) → Prop
```

```lean
ContinuousLinearMap.IsFredholm.eventually_nhds :
  ∀ {𝕜 : Type u_1} {E : Type u_2} {F : Type u_3}
  [inst : NontriviallyNormedField 𝕜] [inst_1 : NormedAddCommGroup E] [inst_2 : NormedAddCommGroup F]
  [inst_3 : NormedSpace 𝕜 E] [inst_4 : NormedSpace 𝕜 F] [CompleteSpace E] [CompleteSpace 𝕜] {T₀ : E →L[𝕜] F},
  ContinuousLinearMap.IsFredholm T₀ → ∀ᶠ (T : E →L[𝕜] F) in nhds T₀, ContinuousLinearMap.IsFredholm T
```

```lean
ContinuousLinearMap.IsFredholm.eventually_nhds_index_eq :
  ∀ {𝕜 : Type u_1} {E : Type u_2} {F : Type u_3}
  [inst : NontriviallyNormedField 𝕜] [inst_1 : NormedAddCommGroup E] [inst_2 : NormedAddCommGroup F]
  [inst_3 : NormedSpace 𝕜 E] [inst_4 : NormedSpace 𝕜 F] [CompleteSpace E] [CompleteSpace 𝕜] {T₀ : E →L[𝕜] F},
  ContinuousLinearMap.IsFredholm T₀ → ∀ᶠ (T : E →L[𝕜] F) in nhds T₀, LinearMap.index ↑T = LinearMap.index ↑T₀
```

```lean
ContinuousLinearMap.IsFredholm.index_comp :
  ∀ {𝕜 : Type u_1} {E : Type u_2} {F : Type u_3} {G : Type u_4}
  [inst : NontriviallyNormedField 𝕜] [inst_1 : AddCommGroup E] [inst_2 : AddCommGroup F] [inst_3 : AddCommGroup G]
  [inst_4 : Module 𝕜 E] [inst_5 : Module 𝕜 F] [inst_6 : Module 𝕜 G] [inst_7 : TopologicalSpace E]
  [inst_8 : TopologicalSpace F] [inst_9 : TopologicalSpace G] {g : F →L[𝕜] G} {f : E →L[𝕜] F},
  ContinuousLinearMap.IsFredholm g →
    ContinuousLinearMap.IsFredholm f → LinearMap.index ↑(g ∘SL f) = LinearMap.index ↑g + LinearMap.index ↑f
```

```lean
ContinuousLinearMap.IsFredholm.index_continuousAt :
  ∀ {𝕜 : Type u_1} {E : Type u_2} {F : Type u_3}
  [inst : NontriviallyNormedField 𝕜] [inst_1 : NormedAddCommGroup E] [inst_2 : NormedAddCommGroup F]
  [inst_3 : NormedSpace 𝕜 E] [inst_4 : NormedSpace 𝕜 F] [CompleteSpace E] [CompleteSpace 𝕜] {T₀ : E →L[𝕜] F},
  ContinuousLinearMap.IsFredholm T₀ → ContinuousAt (fun (T : E →L[𝕜] F) => LinearMap.index ↑T) T₀
```

```lean
ContinuousLinearMap.index_continuousOn_isFredholm :
  ∀ {𝕜 : Type u_1} {E : Type u_2} {F : Type u_3}
  [inst : NontriviallyNormedField 𝕜] [inst_1 : NormedAddCommGroup E] [inst_2 : NormedAddCommGroup F]
  [inst_3 : NormedSpace 𝕜 E] [inst_4 : NormedSpace 𝕜 F] [CompleteSpace E] [CompleteSpace 𝕜],
  ContinuousOn (fun (T : E →L[𝕜] F) => LinearMap.index ↑T) {T : E →L[𝕜] F | ContinuousLinearMap.IsFredholm T}
```

## Pinned reference definitions

The excerpts below, taken from the reference development, contain every pinned declaration (2
constants including the auxiliary ones Lean generates for them, such as constructors, recursors,
projections and `match_` functions). Reproduce these declarations exactly. Using a file with the same
path, imports and `variable`/`open` context is the safest way to get an identical elaborated value
(for example, instance resolution depends on the imports). `-- ...` marks omitted parts of the
reference file (other declarations and proofs, which you develop yourself).

### `Mathlib/Analysis/Normed/Operator/Fredholm/Basic.lean`

```lean
module
-- ...
public import Mathlib.Algebra.Module.LinearMap.Index
public import Mathlib.Analysis.Normed.Operator.Perturbation.StrictByFinite
public import Mathlib.Topology.Algebra.Module.ContinuousLinearMap.Invertible
-- ...
@[expose] public noncomputable section
-- ...
open Topology Submodule LinearMap Function
open Set (MapsTo)
open LinearMap.FiniteRangeSetoid
-- ...
namespace ContinuousLinearMap
section TVS
-- ...
variable {𝕜 E F G : Type*} [NontriviallyNormedField 𝕜]
    [AddCommGroup E] [AddCommGroup F] [AddCommGroup G]
    [Module 𝕜 E] [Module 𝕜 F] [Module 𝕜 G]
    [TopologicalSpace E] [TopologicalSpace F] [TopologicalSpace G]
-- ...
section DefTFAE
-- ...
section IsFredholm

/-- A continuous linear map `u : E →L[𝕜] F` is a **Fredholm operator** if it is strict,
its range is closed and has finite codimension, and its kernel is (topologically) complemented and
has finite dimension.

See also `isFredholm_tfae` for other equivalent characterizations.
We will also prove later (not in Mathlib yet) that for maps between Banach (or even Fréchet)
spaces over `ℝ` or `ℂ`, all the conditions follow from the kernel and cokernel having finite
dimension. -/
structure IsFredholm (u : E →L[𝕜] F) : Prop where
  isStrictMap : IsStrictMap u
  isClosed_range : IsClosed (u.range : Set F)
  finite_ker : FiniteDimensional 𝕜 u.ker
  finite_coker : u.range.CoFG
  closedComplemented_ker : u.ker.ClosedComplemented
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
