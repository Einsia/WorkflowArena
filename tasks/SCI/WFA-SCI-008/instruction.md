> The working directory is `/workspace`. Input files are in `/workspace/inputs/`. Write your deliverables to `/workspace/submission/`.

# Blind prediction: octanol/water partition coefficients (log P) of 11 kinase-inhibitor fragment-like molecules

## Goal

Predict the octanol/water partition coefficient log P at 25 °C for the 11 molecules (IDs `LP01`–`LP11`) in `inputs/molecules.csv`:

log P = log10( [neutral species]_octanol / [neutral species]_water )

This refers only to the **neutral form** (not log D). Some molecules were supplied as hydrochloride salts in the solid state (`.Cl` in the SMILES). The measurements were made with an ionic-strength-adjusted aqueous phase (0.15 M KCl); the counter-ion does not affect the neutral partitioning being asked for.

Experimental background (measurement method only, no values): pH-metric (potentiometric) log P. The instrument performs acid-base titrations at several octanol/water volume ratios and back-calculates the partitioning of the neutral and ionic species from the shift of the apparent pKa. At least 3 independent replicates per molecule.

## Inputs

- `inputs/molecules.csv`: IDs and isomeric SMILES.
- `inputs/submission_template.csv`: submission template.

## Deliverables

Create `submission/` in the working directory containing `logP-prediction.csv`, in the same format as the template:

```
Predictions:
LP01,<logP>,<logP SEM>,<logP model uncertainty>
...(all 11 rows are required; give logP to two decimal places)
Name:
<method name>
Software:
<software and version, one per line>
Category:
Physical (MM) | Physical (QM) | Empirical | Mixed
Method:
<method description, at roughly the level of detail of a paper's methods section, including key parameters and how the uncertainties were estimated>
```

A submission missing a prediction for any molecule is invalid. You may additionally submit `submission/notes.md` describing the division of work and the calibration procedure (not scored).

## Rules

- The environment is offline. Do not look up the experimental log P of these molecules in the literature, databases or web pages, and do not use any dataset that contains measured values for these molecules (including specific values you remember). If you recognize these molecules or their measured values, declare it in `notes.md`.
- Time cut-off: you may only use empirical models, force fields, quantum-chemical methods and training data that were public before 2019-03-22 (the original submission deadline); any training set you build must exclude these 11 molecules.
- You may use the local CPU (multi-core); no GPU is provided.
- You may combine several methods (e.g. physics-based solvation free energies, quantum-chemical continuum models, empirical / machine-learning models) and decide yourself how to split the work and how to combine the results into a final prediction.

## Evaluation

- Primary metric: RMSE over the 11 molecules (log units); MAE, mean signed error, R², regression slope and Kendall τ are also reported.
- The RMSE is converted into a rank among all official blind submissions of that challenge round.
