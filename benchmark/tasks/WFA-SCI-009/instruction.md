> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: the `outputs/`, `code/` and `logs/` directories mentioned in the task correspond to `/workspace/submission/outputs/`, `/workspace/submission/code/` and `/workspace/submission/logs/` (grading reads only `/workspace/submission/`).
>
> The data files that the task says are placed by the evaluation environment / harness (see `inputs/MANIFEST.json`) were downloaded when the image was built, verified by sha256, and placed at the locations under `/workspace/inputs/` described in the task; there is no network access at runtime, so no download is needed or possible.
>
> Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1; Quantum ESPRESSO 6.7 (Debian bookworm package quantum-espresso 6.7-2+b1, `pw.x`, linked against the Debian reference BLAS/LAPACK), OpenMPI (`mpirun`), ASE 3.24.0.

# Equation-of-state precision verification with plane-wave pseudopotential DFT: 10 crystals

## Background and method (adapted from a research article in a physics review journal)

To verify the numerical precision of different DFT codes against one another, a multi-code collaborative study computed equations of state (EOS) for more than a thousand elemental crystals and cubic oxide prototypes, using the average of two all-electron codes as the reference. Using **the plane-wave pseudopotential code Quantum ESPRESSO (pw.x) and the given pseudopotential library (SSSP 1.3.0 PBE precision)**, reproduce the EOS parameters of 10 of these crystals following the same protocol.

**Protocol**
- Exchange-correlation: PBE; no spin polarization; scalar-relativistic pseudopotentials (i.e. the files in the given library).
- Cutoffs: the wavefunction and charge-density cutoffs recommended for each element in the library's JSON; for compounds take the maximum over the elements.
- Smearing: Fermi–Dirac with width 0.0045 Ry; the energy used in the EOS is the free energy E − TS (the total energy printed by pw.x is the free energy including the −TS term).
- k-points: a regular Γ-centred grid; on the cell with the smallest volume, take the smallest grid whose point spacing along each reciprocal lattice vector is at most 0.06 Å⁻¹ (reciprocal vector lengths defined including 2π); use the same grid (same reduced coordinates) for all other volumes.
- Volume points: with the given structure as the central volume V_c, take V_c × {0.94, 0.96, 0.98, 1.00, 1.02, 1.04, 1.06}, 7 points in total, scaling the cell isotropically with fixed fractional atomic coordinates and no relaxation.
- Fit: least-squares fit of the third-order Birch–Murnaghan equation of state to the 7 (V, E) points, giving the equilibrium volume V0 (per given cell, Å³/cell), the bulk modulus B0 (GPa) and its pressure derivative B1.
- SCF convergence threshold strict enough (energy converged to the order of ≤1e-10 Ry/atom) to keep the EOS smooth.

## Given inputs

- `inputs/structures/<system>.xsf`: cells at the central volume for the 10 structures (XCrySDen XSF format). Systems: Al-FCC, Na-BCC, Pb-FCC, Si-Diamond, Cu-FCC, W-BCC, Mg-XO (rock-salt MgO prototype), Li-X2O (anti-fluorite prototype), Ti-XO2 (fluorite prototype), Zn-XO (rock-salt prototype).
- `inputs/pseudos/`: pseudopotential files and the JSON of recommended cutoffs (placed by the evaluation environment, see `inputs/MANIFEST.json`).
- The runtime environment provides Quantum ESPRESSO pw.x (you may also compile the same major version yourself).

Searching online for the EOS data published by this collaborative study is forbidden.

## Deliverables

- `outputs/eos.csv`: columns `system,quantity,value`, quantity ∈ {V0_A3_per_cell, B0_GPa, B1}, 30 rows.
- `outputs/eos_points/<system>.csv`: the 7 (V, E) points of each system (Å³/cell, eV/cell).
- `code/`, `logs/` (including the pw.x input files and an output summary for each volume).

## Acceptance

The systems are divided into 4 scoring targets by group (in each group up to 15% of the numbers may miss): relative tolerance 0.05% for V0, relative tolerance 0.5% for B0, absolute tolerance 0.03 for B1. The task as a whole succeeds only if all targets pass.
