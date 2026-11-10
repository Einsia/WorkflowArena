> The working directory is `/workspace`. Input files are in `/workspace/inputs/`. Write your deliverables to `/workspace/submission/`.

# Blind prediction: hydration free energies of 47 organic molecules

## Goal

Predict the **hydration free energy** ΔG_hyd (kcal/mol, transfer free energy from 1 M gas phase to 1 M aqueous phase) at 298 K of the 47 molecules (`HF01`–`HF47`, ranging from small hydrocarbons / alcohols to drug molecules and polyfunctional natural products) in `inputs/molecules.csv`.

- Treat every molecule in its neutral form (carboxylic acids stay –COOH, amines are neutral amines).
- Some molecules have complex conformational landscapes with high barriers between conformers (nanosecond-scale MD may undersample them); take care.
- The SMILES are the authoritative input; generate any 3D structures you need yourself.

## Inputs

- `inputs/molecules.csv`: IDs, SMILES.
- `inputs/submission_template.csv`.

## Deliverables

`submission/hydration-prediction.csv`:

```
Predictions:
HF01,<ΔG_hyd kcal/mol>,<statistical uncertainty>,<model uncertainty>
...(all 47 rows are required)
Name:
<method name>
Software:
<software and version>
Method:
<method description: force field / charges / water model or QM solvent model, sampling, free energy estimation, conformer handling>
```

A submission missing any molecule, or with an empty `Name:` / `Method:`, is invalid. Optional `submission/notes.md` (division of work, resource usage, declarations).

## Rules

- Offline. Do not look up the experimental hydration free energies of these molecules (literature, databases such as FreeSolv / MNSol, and specific values you remember are all forbidden). If you recognize the values, declare it in `notes.md`.
- Time cut-off: you may only use methods and parameters that were public before 2013-08-01; you may not use any training set that contains measured values for these 47 molecules.
- Only CPUs (multi-core) are provided.

## Evaluation

- Primary metric: RMSE over the 47 molecules (kcal/mol); MAE, mean signed error, R², slope and Kendall τ are also reported.
- Overall success: RMSE, MAE and Kendall τ all reach fixed thresholds (roughly the level of the best few submissions of that round).
- In addition, the RMSE (as well as MAE and Kendall τ) is converted into an **approximate rank** among all official submissions of that round (43); this is for reference only and does not count towards success.
