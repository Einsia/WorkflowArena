> Your working directory is `/workspace`, i.e. the `workspace/` referred to below: a pinned mathlib4 source checkout, initialised as a git repository (start commit `start`). The Lean toolchain, the dependency packages and the prebuilt Mathlib cache are already installed, and `lake build Mathlib` has already been run; there is no network access at run time, so `lake exe cache get` is neither needed nor possible. Deliver your work by editing `/workspace/Mathlib/` and `/workspace/Mathlib.lean` directly. Grading collects only these two paths into the grader's own clean copy, where every file that already exists under `Mathlib/` in the start state is reset to its start-state content (edits to existing Mathlib files are discarded; only new files under `Mathlib/` and your `Mathlib.lean` are kept, and start-state import lines missing from your `Mathlib.lean` are re-added), then runs `lake build Mathlib` and checks the required declarations; changes to any other file are ignored.

# feat: Hahn embedding theorem

You are working in a pinned mathlib4 checkout (`workspace/`; Lean toolchain pinned in
`lean-toolchain`, dependencies in `lake-manifest.json`; the prebuilt
Mathlib build is already installed). Develop the mathematics below as mathlib-quality Lean code.

## Goal

This proves [Hahn embedding theorem](https://en.wikipedia.org/wiki/Hahn_embedding_theorem), one among the 1000+ theorems project.

Note on file location: I originally placed it in Algebra/Order/Group, but got prompted that Algebra can't import Analysis (needed for `Real` being a `Rat`-module` and related fact), so now I moved it under HahnSeries

This is a substantial development: in the original history it took 6 separate
contributions. Everything needed beyond the current library is yours to build.

## Required deliverables

After your work, each of the following constants must exist (anywhere under
`Mathlib/`, imported from `Mathlib.lean`) and have exactly this type, as printed
by `#check @name` (grading compares the elaborated types structurally, so notation
and binder names do not matter, but the statement must be the same):

```lean
hahnEmbedding_isOrderedAddMonoid :
  ∀ (M : Type u_1) [inst : AddCommGroup M] [inst_1 : LinearOrder M]
  [inst_2 : IsOrderedAddMonoid M],
  ∃ (f : M →+o Lex (HahnSeries (FiniteArchimedeanClass M) ℝ)),
    Function.Injective ⇑f ∧
      ∀ (a : M), ArchimedeanClass.mk a = (FiniteArchimedeanClass.withTopOrderIso M) (HahnSeries.orderTop (ofLex (f a)))
```

```lean
hahnEmbedding_isOrderedModule_rat :
  ∀ (M : Type u_1) [inst : AddCommGroup M] [inst_1 : LinearOrder M]
  [inst_2 : IsOrderedAddMonoid M] [inst_3 : Module ℚ M] [IsOrderedModule ℚ M],
  ∃ (f : M →ₗ[ℚ] Lex (HahnSeries (FiniteArchimedeanClass M) ℝ)),
    StrictMono ⇑f ∧
      ∀ (a : M), ArchimedeanClass.mk a = (FiniteArchimedeanClass.withTopOrderIso M) (HahnSeries.orderTop (ofLex (f a)))
```

## Rules

- No `sorry`, no new `axiom`/`opaque` tricks; standard axioms (`propext`,
  `Classical.choice`, `Quot.sound`) are fine.
- Existing library files are read-only: grading resets every start-state file under `Mathlib/` to
  its original content and keeps only your new files under `Mathlib/` plus your `Mathlib.lean`
  (start-state import lines missing from it are re-added). Put all of your work in new files and
  import them from `Mathlib.lean`; the whole library must build.
- This task has no pinned definitions: every required declaration is a theorem whose statement only
  uses start-state definitions.
- Apart from that, organise files, auxiliary definitions and lemmas, and the order of work as you
  see fit; the original file layout is not required.
