> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: put the CSV files required by the task directly in that directory, together with `code/` and `NOTES.md` (grading reads only `/workspace/submission/`).
>
> The data files listed in `inputs/MANIFEST.json` were downloaded and verified when the image was built and are in `/workspace/inputs/data/` (file names equal the `name` field in the MANIFEST); there is no network access at runtime, so no download is needed or possible.
>
> Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1 (`scipy.io.loadmat` can read the data files); GNU Octave (Debian bookworm package, 7.3.x, `octave-cli`).

# High-dimensional geometry of population responses of ~10,000 neurons in mouse primary visual cortex: cross-validated PCA spectra and power-law exponents (paper reproduction)

## Research question

Two-photon calcium imaging simultaneously records about 10,000 visual-cortex neurons responding to thousands of images (each shown twice). Questions: how is the stimulus-related variance of the population response distributed over principal components? Does the eigenspectrum follow a power law n^(−α), with α close to 1? How does α change with the effective dimensionality of the stimulus ensemble (natural images, whitened images, images projected onto 8 / 4 dimensions, small-field images, gratings)? Are the results robust to removing spontaneous-activity dimensions? And nearest-neighbour decoding to test the discriminability of the population code.

## Given inputs

`inputs/MANIFEST.json`: public data (33 .mat files in total, about 7 GB; verify the md5 after download):
- `dbstims.mat`: recording catalogue. `stimset` = {natimg2800, natimg2800_white, natimg2800_8D, natimg2800_4D, natimg2800_small, ori32, natimg32}; `stype(i)` gives the stimulus set of the i-th recording; `dbstims(i).mouse_name` and `.date` identify the recording, whose file name is `<stimset>_<mouse_name>_<date>.mat`.
- Each recording file: `stim.resp` (presentations × neurons, deconvolved responses ordered by presentation), `stim.istim` (stimulus index of each presentation; the largest index denotes the grey screen), `stim.spont` (spontaneous activity, time × neurons), `stat` (if it has a field `stat.redcell`, the cells for which it is true are inhibitory interneurons and are excluded from the analysis).

## Method

**Preprocessing (per recording)**: remove redcells; let nimg = max(istim) − 1, keep only presentations with istim ≤ nimg, and set NaN to 0; z-score the responses and the spontaneous activity using the mean and standard deviation (population standard deviation) + 1e-6 of the spontaneous activity; take the SVD of the z-scored spontaneous activity and its first 32 right singular vectors V, and subtract from the responses their projection onto these dimensions, R ← R − (RV)Vᵀ; subtract from each neuron its mean over all presentations; split the presentations of each stimulus in order into two halves (the k-th half takes indices ceil(n(k−1)/2) + [1 … floor(n/2)]) and average each half to obtain two stimulus × neuron matrices, "repeat 1 / repeat 2"; discard stimuli without two repeats.

**Stimulus-related variance fraction**: for each neuron = mean of the product of the two mean-subtracted repeats / [0.5(var₁ + var₂)] (population variance), then the nanmean over neurons.

**Cross-validated PCA spectrum (shuffled version)**: repeat 10 times: for each stimulus, swap its two repeats with probability 1/2; build the row covariance matrix of the data arranged as "stimulus × repeat", take the S×S submatrix corresponding to the "training repeat" rows and its SVD to obtain A, B; projection P = R₁ᵀ A / sqrt(diag(B)); the variance estimate of the n-th component = Σ_stimuli (R₁P)_n · (R₂P)_n. Average over the 10 repetitions and divide by the total to obtain the normalized spectrum.

**Power-law exponent**: fit log s_n for the spectrum s_n over n = 11 … min(500, N−2) by weighted least squares with −log n and a constant as regressors and weights 1/n; the slope is α.

**Other analyses**:
- Decoding (the 7 natimg2800 recordings): z-score each of the two repeats along the stimulus dimension (population standard deviation), randomly permute the neurons and take the first m (m = 2^12, 2^11, …, 2^0, and all), compute the correlation matrix between the stimulus response vectors of repeat 1 and repeat 2, and score 1-NN decoding accuracy as "whether the most correlated repeat-1 stimulus of each repeat-2 stimulus is the same stimulus".
- Spontaneous dimensions: for the 7 natimg2800 recordings, repeat the spectrum and α computation above after removing 0, 1, 4, 16, 64, 256, 1024 spontaneous principal components (skipping values that exceed the available number).
- natimg32 (32 images, about 96 trials each): after z-scoring and mean subtraction, split the trials of each stimulus in order into two halves (at trial level, without averaging), then remove 32 spontaneous principal components, and compute the cross-validated spectrum with 10 shuffles using trial-level data; set negative values to 0 and normalize by the sum of positive values; report the cumulative variance fraction of the first 32 components.

## Required outputs (CSV)

Recording identifier `recording` = `<mouse_name>_<date>`.

| File | Columns | Rows |
|---|---|---|
| `T1_alpha.csv` | `stimset,recording,alpha` | the 24 recordings of stimsets 1–5 (ori32 has only 32 components, no α is fitted) |
| `T2_stimvar.csv` | `stimset,recording,stim_var_fraction` | all 28 recordings of stimsets 1–6 |
| `T3_spectrum.csv` | `stimset,recording,pc,log10_var` | the 24 recordings of stimsets 1–5, pc = 1…min(500, number of components), listing only components with spectrum value > 0 |
| `T4_decoding.csv` | `recording,n_neurons,accuracy` | the 7 natimg2800 recordings; n_neurons ∈ {1,2,4,…,4096, all} |
| `T5_alpha_vs_spont_pcs.csv` | `recording,n_spont_pcs_removed,alpha` | the 7 natimg2800 recordings × {0,1,4,16,64,256,1024} |
| `T6_natimg32_cumvar.csv` | `recording,pc,cum_var_fraction` | the 4 natimg32 recordings, pc = 1…32 |

Also submit `code/` and `NOTES.md`.

## Allowed tools and restrictions

Python / MATLAB / Octave / Julia, single CPU machine (no GPU), a few CPU hours in total. Note: numerical linear-algebra libraries may give wrong results on some server CPUs; please verify your results yourself (e.g. that two runs agree). Searching online for the original study's code or results is forbidden.

## Acceptance (overview)

The exponents α, variance fractions, decoding accuracies and cumulative variances are compared by absolute error (with a margin for the fluctuations introduced by random shuffling); spectra are compared as series of log values by correlation and RMSE. The task as a whole succeeds if at least 5 of the 6 tables pass.
