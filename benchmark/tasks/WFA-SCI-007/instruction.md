> The working directory is `/workspace`. Input files are in `/workspace/inputs/`. Write your deliverables to `/workspace/submission/`.

# Blind prediction: binding free energies of two deep-cavity aromatic hosts (OA and TEMOA) with the same set of 8 carboxylic-acid guests

## Goal

Two hosts: octa-acid (OA) and its methylated derivative (TEMOA, with 4 additional methyl groups at the portal). The same set of 8 carboxylic-acid guests binds each host: `OA-L01`–`OA-L08` and `TEMOA-L01`–`TEMOA-L08` (the same number denotes the same guest), 16 complexes in total, all required.

Predict the **standard binding free energy** ΔG° (kcal/mol, 1 M standard state, 1:1 binding) of each complex under the experimental conditions. The binding enthalpy is optional (not scored).

Experimental conditions: 10 mM sodium phosphate buffer, pH 11.7 ± 0.1, 298 K; ITC (1H NMR titration where needed), 1:1 complexation. The carboxyl groups of the hosts are fully deprotonated at this pH.

## Inputs

- `inputs/structures/`: 3D structure files of the host and guests (mol2 with the partial charges provided by the original organizers, sdf). The protonation states / conformations given are for reference only and may be changed.
- `inputs/submission_template.txt`: submission template.

## Deliverables

`submission/dG-prediction.txt`:

```
Predictions:
<ID>,<ΔG kcal/mol>,<ΔG statistical error>,<ΔG model uncertainty>,<ΔH, may be empty>,<ΔH error, may be empty>,<ΔH model uncertainty, may be empty>
...
Name:
<method name>
Software:
<software and version>
Method:
<method description: system preparation, protonation states, force field / QM level, sampling scheme and length, free energy estimator, correction terms>
```

Fill in all 16 IDs. A submission missing any required system, or with an empty `Name:` / `Method:`, is invalid. Optional `submission/notes.md` describing the division of work, calibration and resource usage (not scored).

## Rules

- Offline. Do not look up experimental binding data for these host-guest systems (literature, databases and specific values you remember are all forbidden). If you recognize a system or its values, declare it in `notes.md`.
- Time cut-off: you may only use methods, force fields, parameters and training data that were public before 2018-01-19 (the original deadline); training sets must exclude the measured values of the systems in this task.
- Compute resources: multi-core CPU on this machine; no GPU is provided. Report the CPU core-hours actually used in `notes.md`.

## Evaluation

- Primary metric: RMSE of the binding free energy over the 16 required systems (kcal/mol); MAE, mean signed error, R², slope and Kendall τ are also reported.
- The RMSE is converted into a rank among the official (ranked) submissions of that challenge round.
