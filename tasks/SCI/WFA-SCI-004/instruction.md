> The working directory is `/workspace`. Input files are in `/workspace/inputs/`. Write your deliverables to `/workspace/submission/`.

# Inferring transcriptional regulatory networks from gene expression compendia (blind prediction)

You are given 4 gene expression compendia, each corresponding to one transcriptional regulatory network: one is a simulated network, and the other three come from real microarray data of different microorganisms (the species are not disclosed). All gene names have been anonymized to `G1, G2, ...`, and a small number of decoys that do not correspond to real genes have been mixed in. **Using only the data provided**, output, for each network, a list of regulatory edges (transcription factor → target gene) ranked by confidence.

## Inputs

Each of `inputs/Network{1,2,3,4}/` contains three tab-separated files:

- `expression.tsv`: the expression matrix. The first line contains the gene IDs; each subsequent line is one chip (sample) and each column one gene. Values have been normalized within each compendium (scales and preprocessing differ between networks).
- `chip_features.tsv`: the experimental conditions of each chip, in one-to-one correspondence with the rows of `expression.tsv`. Columns: `#Experiment` (experiment number; chips of the same experiment share it), `Perturbations` (anonymized perturbation IDs such as `P12`, comma-separated if several), `PerturbationLevels`, `Treatment`, `DeletedGenes` (IDs of knocked-out genes), `OverexpressedGenes` (IDs of overexpressed genes), `Time` (time point of a time series), `Repeat` (replicate number); `NA` means not applicable.
- `regulators.tsv`: the list of candidate transcription factors (regulators) of the network, one gene ID per line.

| Network | Genes | Chips | Transcription factors |
|---|---|---|---|
| Network1 | 1643 | 805 | 195 |
| Network2 | 2810 | 160 | 99 |
| Network3 | 4511 | 805 | 334 |
| Network4 | 5950 | 536 | 333 |

`inputs/MANIFEST.sha256` is the checksum list of all input files (`sha256  path  bytes`).

## Deliverables

Directory `submission/` with 4 files `submission/Network1.txt … Network4.txt`; **all 4 networks must be submitted**. One directed edge per line:

```
<TF>\t<target gene>\t<confidence>
```

- `<TF>` must be a gene in that network's `regulators.tsv`; `<target gene>` may be any gene of that network; no self-loops (a TF pointing to itself) and no duplicate edges.
- Sort by confidence from high to low; **line order is the ranking**; the confidence is a real number between 0 and 1 and must be non-increasing.
- At most 100,000 lines per file (anything beyond is ignored). Fewer than 100,000 lines are allowed; edges not listed are treated as ranked last, in no particular order.

Also submit `submission/METHODS.md`: briefly describe the methods used, data preprocessing, any network-specific handling and how methods were integrated (not scored; used for manual review).

## Constraints

- Fully offline: do not access any online service or database (including regulatory-interaction databases, gene annotation databases and literature search), and do not search for published results, participants' predictions or gold standards related to these datasets.
- Do not try to map the anonymized gene IDs back to real gene names, and do not use prior memorized knowledge of any particular species' regulatory network to generate or adjust edges; use only the expression data, the chip conditions and the transcription factor lists.
- You may use general-purpose scientific software installed locally (numpy / scipy / scikit-learn, etc.) and code you write yourself.
- Compute resources: a single multi-core CPU machine, no GPU.
- You may decompose the task, work in parallel and define your own intermediate artifacts.

## Evaluation

The evaluators use experimentally supported regulatory interactions (or, for the simulated network, the known ones) as the gold standard. For each network they compute the AUPR (area under the precision-recall curve) and AUROC (area under the ROC curve) of your ranked list; edges on regulators/genes not covered by the gold standard are excluded, and the part not covered by your list is completed in random order. Each AUPR/AUROC is then converted into a one-sided p-value against a fixed background distribution (the centre of this background distribution is clearly above that of a purely random ranking; a network that does not reach that level gets p≈1 and contributes about 0). The primary metric is the average of −log10(p) over the networks with a reliable gold standard (AUPR and AUROC weighted equally), which is converted into a rank among the participating methods in the public evaluation of that field at the time. A submission missing any network is considered incomplete.
