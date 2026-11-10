> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: put the CSV files required by the task directly in that directory, together with `code/` and `NOTES.md` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1; uncertainties 3.2.2.

# The distribution of cellular turnover in the adult human body: cell numbers, lifespans and turnover rates by cell type (paper reproduction)

## Research question

How many cells, and how many grams of cell mass, are replaced by new cells every day in a reference adult (a male of about 70 kg)? In which cell types is this turnover concentrated? Starting from the given compilations of literature data, estimate for each cell type (26 types, covering blood, epithelia, endothelium, lung, adipose tissue, muscle, cardiac muscle, brain and liver) the number of cells, mean lifespan and mass per cell, and from these the number and mass of cells turned over per day, then aggregate over the whole body.

## Given inputs (`inputs/`)

- `inputs/data/*.xlsx`: literature data organised by tissue (each file has several sheets: cell counts, tissue volume / mass, cell volume, turnover times from labelling / kinetic experiments, rodent lifespans, etc.).
- `inputs/methods/*.md`: method notes corresponding to each tissue file (in English, taken from the explanatory text of the original analysis with all code removed). `Utility_Functions.md` describes the common conventions (geometric mean and its error, conversion between additive / multiplicative uncertainties, multiplicative error propagation). **These notes are authoritative**.

## Conventions

- Cell lifespan (days) = mean replacement time of the cell population; turnover rate (cells/day) = number of cells / lifespan; mass turnover rate (g/day) = turnover rate × mass per cell; total cell mass (g) = number of cells × mass per cell.
- If human lifespan data are missing for a cell type, the method notes describe how to extrapolate from rodent lifespans: in that case report the rodent lifespan (`source=rodent`), and use the extrapolated values for the turnover rate and mass turnover rate.
- Do not round results to significant figures (keep full floating-point values). Uncertainties are not scored, but please give them in `NOTES.md`.

Cell-type keys (you must use exactly these names, with the same capitalization):
Erythrocytes; Neutrophils; Thymocytes; Mature T cells; B cells progenitors; Transitional B cells; Mature B cells; Monocytes; Stomach epithelia; Small intestine epithelia; Colon epithelia; Epidermal cells; Dermal fibroblasts; Endothelial cells; Alveolar epithelial cells; Alveolar macrophages; Bronchial epithelial cells; Lung interstitial cells; Adipocytes; Myocytes; Cardiomyocytes; Neurons; Glial cells; Hepatocytes; Kupffer cells; Stellate cells.

## Required outputs (CSV; column names must match exactly)

| File | Columns | Rows |
|---|---|---|
| `T1_cell_number.csv` | `cell_type,number_cells` | 26 cell types |
| `T2_lifespan.csv` | `cell_type,source,lifespan_days` | one row per cell type; `source` = `human` (human data available) or `rodent` (types extrapolated from rodent lifespans) |
| `T3_turnover_cells.csv` | `cell_type,cells_per_day` | 26 cell types (human values or extrapolated values) |
| `T4_cell_mass.csv` | `cell_type,cell_mass_pg` | 26 cell types |
| `T5_turnover_mass.csv` | `cell_type,grams_per_day` | 26 cell types |
| `T6_total_mass.csv` | `cell_type,total_mass_g` | 26 cell types |
| `T7_aggregates.csv` | `quantity,value` | `total_cells_per_day`, `total_grams_per_day` (sums over the 26 types), `blood_fraction_of_cell_turnover`, `blood_fraction_of_mass_turnover` (blood cells = erythrocytes, neutrophils, monocytes and the 5 lymphocyte classes), `gut_epithelium_fraction_of_cell_turnover`, `gut_epithelium_fraction_of_mass_turnover` (stomach, small-intestine and colon epithelia), `erythrocyte_fraction_of_cell_turnover` |

Also submit `code/` (re-runnable) and `NOTES.md` (the estimation route and uncertainty for each cell type).

## Allowed tools and restrictions

Any open-source library in Python / R, single CPU machine, minutes of compute. Searching online for the original study's code or result tables is forbidden; use only `inputs/`.

## Acceptance (overview)

Each table is compared cell by cell by log error (a tolerance of a few percent per cell); a table passes only if most of its cells pass; the task as a whole succeeds if at least 6 of the 7 tables pass.
