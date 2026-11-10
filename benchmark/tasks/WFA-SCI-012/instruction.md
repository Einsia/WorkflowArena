> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: the `outputs/`, `code/` and `logs/` directories mentioned in the task correspond to `/workspace/submission/outputs/`, `/workspace/submission/code/` and `/workspace/submission/logs/` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 1.26.4, scipy 1.13.1, pandas 2.2.3, openpyxl, statsmodels, matplotlib, h5py; PySCF 2.8.0, pyscf-dispersion 1.3.0 (D3/D3(BJ)/D4).

# Main-group thermochemistry benchmark: reaction-energy errors of a dispersion-corrected hybrid functional on 7 subsets

## Background and method (adapted from a physical chemistry journal article and its supplementary material)

A large-scale density-functional benchmark study compiled high-accuracy reference values for thousands of main-group chemical reaction energies (atomization energies, ionization potentials, proton affinities, self-interaction-sensitive dissociations, bond dissociations, reaction barriers, radical stabilization energies, etc.) into a database, and then computed and statistically analysed the errors of dozens of functionals one by one. For 7 of its subsets, reproduce the results of the **hybrid functional PBE0 with the D3 dispersion correction (Becke–Johnson damping, D3(BJ), using the standard parameters for this functional, without the three-body term)**.

**Computational conventions**
- All species are single-point calculations at the given geometries: no geometry optimization, no zero-point or thermal corrections.
- Basis set: def2-QZVP (all species).
- Open-shell species use spin-unrestricted Kohn–Sham; the charge and number of unpaired electrons are given in `.CHRG` and `.UHF` in each species directory (a missing file means 0).
- The integration grid must be fine enough (reaction energies converged to ≤0.05 kcal/mol), with SCF converged to ≤1e-8 Eh; if a calculation converges to an excited state or shows symmetry breaking, check and record it.
- Reaction energy = Σ stoichiometric coefficient × total energy, in kcal/mol (1 Eh = 627.5094740631 kcal/mol). Deviation = computed value − reference value.
- Statistics per subset: MD (mean deviation), MAD (mean absolute deviation), RMSD.

## Given inputs

- `inputs/geometries/<subset>/<species>/`: `struc.xyz` (Å), `coord` (the same geometry in another format), `.CHRG`, `.UHF`.
- `inputs/reactions.csv`: columns `subset,idx,species,stoichiometry,ref_kcal_mol`; species and stoichiometry are space-separated, corresponding lists. 347 reactions in total: W4-11 (140), G21IP (36), PA26 (26), SIE4x4 (16), ALKBDE10 (10), BH76 (76), RSE43 (43).

You may use any open-source quantum-chemistry program (e.g. PySCF, Psi4) and an open-source D3 implementation. Searching online for the published functional results of this database is forbidden.

## Deliverables

- `outputs/reaction_energies.csv`: columns `subset,idx,value` (computed reaction energy, kcal/mol), 347 rows.
- `outputs/subset_stats.csv`: columns `subset,stat,value`, stat ∈ {MD, MAD, RMSD}, 7 × 3 = 21 rows.
- `outputs/total_energies.csv` (columns `subset,species,energy_Eh`), `code/`, `logs/`.

## Acceptance

Reaction energies are compared one by one with hidden reference values (tolerance 0.4 kcal/mol, at least 90% must pass in each group); the reactions are split by subset into 6 scoring targets, and the subset statistics (for the 5 subsets other than BH76 and W4-11) form the 7th target (tolerance 0.15 kcal/mol). The task as a whole succeeds only if all targets pass.
