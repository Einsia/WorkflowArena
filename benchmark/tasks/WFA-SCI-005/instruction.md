> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (`inputs.MANIFEST.tsv` is in `/workspace/`). Write the deliverable `submission.csv` to `/workspace/submission/submission.csv`.

# Predicting scalar coupling constants in molecules (NMR J-coupling)

Given the 3D structures of small organic molecules, predict the scalar coupling constant J (Hz) of intramolecular atom pairs (between H and C/N/H, separated by 1–3 chemical bonds). Training-set molecules come with J values and several auxiliary quantum-chemical quantities; for test-set molecules only the structures and the atom pairs to predict are given.

## Inputs (`inputs/`, verified by `inputs.MANIFEST.tsv`; file-name mapping: data_train.csv→train.csv, data_test_masked.csv→test.csv)

- `train.csv`: `id, molecule_name, atom_index_0, atom_index_1, type, scalar_coupling_constant` (about 4.66 million rows, about 85,000 molecules).
- `test.csv`: same as above but without `scalar_coupling_constant` (about 2.5 million rows, about 45,000 molecules).
- `structures.csv`: Cartesian coordinates (Å) of all molecules.
- Auxiliary quantities available only for training-set molecules: `dipole_moments_train.csv`, `magnetic_shielding_tensors_train.csv`, `mulliken_charges_train.csv`, `potential_energy_train.csv`, `scalar_coupling_contributions_train.csv` (the four-term decomposition of J: fc/sd/pso/dso).

There are 8 coupling types: `1JHC 1JHN 2JHH 2JHC 2JHN 3JHH 3JHC 3JHN` (the number is the number of bonds).

## Deliverable

`submission.csv`, two columns `id,scalar_coupling_constant`, covering every id in `test.csv`, with finite values.

## Constraints

- Fully offline: do not download any external dataset, pretrained model weights or other people's solutions; do not search for public code, discussions or results related to this data. You may use general-purpose libraries installed locally (e.g. RDKit, scikit-learn, LightGBM, PyTorch CPU build) and code you write yourself.
- Compute resources: a single multi-core CPU machine, no GPU.
- You may decompose the task and work in parallel as you see fit.

## Evaluation

The MAE is computed separately for each coupling type, log(MAE) is taken (floored at 1e-9), and the average over the 8 types is the score; lower is better. This score is converted into a rank among the teams of the original competition.
