> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: the `outputs/`, `code/` and `logs/` directories mentioned in the task correspond to `/workspace/submission/outputs/`, `/workspace/submission/code/` and `/workspace/submission/logs/` (grading reads only `/workspace/submission/`).
>
> The data files that the task says are placed by the evaluation environment / harness (see `inputs/MANIFEST.json`) were downloaded when the image was built, verified by sha256, and placed at the locations under `/workspace/inputs/` described in the task; there is no network access at runtime, so no download is needed or possible.
>
> Installed software: Python 3.9; numpy 1.21.6, scipy 1.7.3, pandas 1.3.5, scikit-learn 1.0.2, xgboost 1.5.2 (CPU), pymatgen 2021.3.9, matminer 0.6.5, spglib 2.0.2 (full version list in the image at /opt/constraints.txt). No GPU.

# Can machine-learned formation energies predict compound stability? A systematic test of three composition-based models

## Background and method (adapted from a computational materials journal article)

Machine-learning models that predict the formation energy ΔH_f from the chemical composition alone appear to have small errors on ΔH_f, but whether a material is stable depends on its decomposition energy ΔH_d relative to the convex hull, which is a difference between the energies of several compounds in the same chemical space, so its errors do not cancel as they do for ΔH_f. Reproduce this test with three kinds of composition features.

**Models**
- Features (three kinds, each trained separately):
  - ElFrac: the atomic fraction of each element (elements 1–103).
  - Meredig: elemental atomic fractions + composition statistics such as mean atomic weight, mean column, mean row, range of atomic number, mean atomic number, mean atomic radius, mean electronegativity, mean numbers of s/p/d/f valence electrons and their fractions (the composition descriptors proposed by Meredig et al. in 2014).
  - Magpie: 6 atomic-fraction-weighted statistics (minimum, maximum, range, mean, mean deviation, mode) of 22 elemental properties, 132 dimensions in total.
  - Missing feature values are filled with 0.
- Regressor: gradient-boosted trees (XGBoost regression, 200 trees, maximum depth 5, learning rate 0.1, squared-error objective, other settings default). Note: the default learning rate of recent XGBoost versions is 0.3, so it must be set to 0.1 explicitly.

**Stability analysis**
- Convex hull: within a chemical space (set of elements), build the lower convex hull from the per-atom formation energies of all compounds (elements have ΔH_f = 0). The decomposition energy of a compound is ΔH_d = ΔH_f − the energy at that composition of the hull formed by the **other** phases in the same space; ΔH_d ≤ 0 means stable (on the hull). Each compound is analysed in the smallest chemical space given in `spaces.json`.
- When the stability analysis uses ML energies, replace the DFT ΔH_f of all non-elemental compounds in the relevant chemical space with ML predictions and rebuild the hull.

**Experiments**
1. **allMP**: 5-fold cross-validation over all compounds in `hullout.json` (in file order) with `KFold(n_splits=5, shuffle=True, random_state=10)` (scikit-learn semantics), giving an out-of-fold ML ΔH_f for every compound; then build the hulls of all chemical spaces with the ML energies and compute the ML ΔH_d of every compound. Report: the MAE of ΔH_f and of ΔH_d (relative to the DFT `Ef`/`Ed`), and the classification accuracy, F1 and false-positive rate FPR with "stable" as the positive class.
2. **LiMnTMO**: remove from the training set the 267 Li–Mn–transition-metal–O quaternary compounds in `mp_LiMnTMO.json`, train on all remaining compounds, and predict the ΔH_f of these 267; compute ΔH_d in their chemical spaces replacing only the energies of these compounds. Report the MAE of ΔH_f and ΔH_d.
3. **Candidate screening**: train in the same way (excluding the 267 MP compounds and the candidate set itself), predict the ΔH_f of all candidate compositions in `smact_LiMnTMO.json`, add them to the corresponding MP chemical space and compute ΔH_d, and count the candidates predicted to be stable. Choice of the corresponding space: among all MP chemical spaces that appear in `spaces.json` (elements in alphabetical order joined by `_`), select the spaces that contain all four elements of the candidate and have fewer than 7 elements; if there are several, take the one with the fewest elements, and among equal element counts the lexicographically smallest string. The energies of those of the 267 MP quaternary compounds that lie in the space are also replaced by the same model's predictions; the other MP phases keep their DFT values.

## Given inputs

`inputs/data/`: `Ef.json`, `hullout.json`, `spaces.json`, `mp_LiMnTMO.json`, `smact_LiMnTMO.json`, and `hullin.json` unpacked and placed by the evaluation environment (DFT energies and compositions of the compounds in each chemical space). See `inputs/MANIFEST.json`. pymatgen, matminer (featurization only), scikit-learn and xgboost may be used.

## Deliverables

`outputs/results.csv`, columns `experiment,model,metric,value`:
- experiment=allMP, model ∈ {ElFrac, Meredig, Magpie}, metric ∈ {Ef_MAE, Ed_MAE, Ed_cl_accuracy, Ed_cl_f1, Ed_cl_fpr}
- experiment=LiMnTMO, metric ∈ {Ef_MAE, Ed_MAE}
- experiment=smact, metric = n_pred_stable

Energies in eV/atom. Also submit `outputs/predictions/` (ML ΔH_f and ΔH_d of each model in each experiment), `code/` and `logs/`.

## Acceptance

Results are divided by experiment / model into 5 scoring targets and compared with hidden reference values (relative tolerance 5–8% for MAEs, absolute tolerance 0.02 for classification metrics, relative tolerance 10% for the candidate count); a target passes if 80% of its numbers are within tolerance, and the task as a whole succeeds only if all targets pass. Searching online for the original paper and the author code is forbidden.
