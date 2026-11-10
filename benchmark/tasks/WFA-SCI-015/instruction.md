> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: put the CSV files required by the task directly in that directory, together with `code/` and `NOTES.md` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: R 4.0.3 (rocker/r-ver:4.0.3, CRAN snapshot) with EpiEstim 2.2-4, deSolve, jsonlite; Python 3.8 (Ubuntu 20.04) with numpy 1.24.4, scipy 1.10.1, pandas 2.0.3.

# Practical issues in real-time estimation of the effective reproduction number R_t: method comparison, generation-interval misspecification, smoothing windows and reporting delays (paper reproduction)

## Research question

Using synthetic epidemic data with known ground truth, systematically evaluate the sources of bias of commonly used R_t estimators in practice: differences between estimators (the Cori method based on infection times, and the Wallinga–Teunis method based on case pairs), the effect of a wrongly specified mean / variance of the generation interval (GI), the effect of smoothing-window length and time alignment, and the bias when observation delays (infection → report / death) are not handled correctly (simple shifting vs. deconvolution). Also compute the exact "case reproduction number" R_c as a reference.

## Given inputs (`inputs/`)

Synthetic SEIR epidemic (N = 2×10^6, initial I = 60, mean latent period t_E = 4 days, mean infectious period t_I = 4 days; R_0 decreases linearly from 2.0 to 0.8 over 7 days starting on day 60, and increases to 1.15 over 7 days starting on day 90):

- `sim_seir_ode.csv`: deterministic ODE version; `sim_seir_stochastic.csv`: stochastic version. Columns: `time, S, E, I, R, dS` (new infections that day), `dEI` (new onsets that day), `true_r0`, `true_rt` (= R_0(t)·S/N), `incidence` (= round(dS), daily new infections, used as the "infection time" series), `obs_cases` (daily new onsets, used as the "symptom onset" series).
- `observed_cases_deaths.csv`: `time, obs_case, obs_deaths`: daily "reported cases" and "deaths" obtained by sampling a delay for each daily ODE infection (t ≤ 110). Case delay = Gamma(shape 5.8, scale 0.95) + Uniform(0, 4) days; death delay = Gamma(shape 5.8, scale 0.95) + Gamma(mean 15, standard deviation 6.9) days.

True generation interval: Gamma distribution with mean 8 days and variance 32 (= 2·(8/2)^2).

## Method conventions

- **Cori method**: daily windows of length τ (default 1 day), window [t_s, t_e], with t_s starting from the 2nd time point; prior on R Gamma(mean 5, standard deviation 5); the generation interval is discretized as in common implementations (discretization of a Gamma distribution "offset by 1 day"). **Generation-interval uncertainty**: draw 50 samples of the GI mean from a truncated normal (mean = the specified value, standard deviation 1.5, truncated at the specified value ± 1) and of the GI standard deviation from a truncated normal (mean = the specified standard deviation, standard deviation 1.5, truncated at the specified value ×[0.8, 1.2]); for each GI draw 100 samples from the posterior of R, and report the mean of the pooled samples. Treat missing / negative values as 0. By default assign the estimate to the window end t_e ("end"); with "mid" alignment assign it to ceil((t_s + t_e)/2).
- **Wallinga–Teunis method**: case-pair likelihood with a parametric Gamma GI (mean 8, variance 32), window 1 day, estimate assigned to the window midpoint; use `incidence` (infection times) and `obs_cases` (onset times) as inputs separately. Use only the part of the series after the first day with incidence > 0 (fill missing days in between with 0).
- **Generation-interval misspecification** (ODE data, t < 150 or ≤ 150): GI mean set to 6, 7, 8, 9, 10 (variance kept at 32); or GI variance changed: Gamma(shape = 1/k, scale = 8k), k ∈ {1/8, 1/4, 1/2, 1, 2} (variances 8, 16, 32, 64, 128 respectively, mean 8).
- **Smoothing window** (stochastic data, t < 150): τ = 1, 7, 14 days, each with end and mid alignment.
- **Delay handling** (t ≤ 110):
  - Shift: shift the observed series back by the "mean delay" in days (the mean delay is the mean of 1,000 draws from the delay distribution, rounded to whole days).
  - Deconvolution: Richardson–Lucy iteration (delay probability mass function from 10,000 delay draws rounded and normalized; pad the start of the series with initial values for the length of the maximum delay, correct for right censoring by the cumulative detection probability, iterate until the chi-square statistic < 1; values in the result larger than 10 times the initial values are treated as missing).
  - Run the Cori estimation (τ = 1) separately on the true infections, the shifted cases, the shifted deaths and the deconvolved cases (rounded).
- **Case reproduction number R_c(t)**: under the ODE model, compute exactly the expected number of secondary infections caused over their entire infectious period by individuals infected at time t (integrating with the given R_0(t) trajectory, t_E, t_I, N, time step 0.001 day).

## Required outputs (CSV, long format)

| File | Columns | Content |
|---|---|---|
| `T1_cori_ode.csv` | `time,rt_mean` | ODE data, t ≤ 150, Cori (τ = 1, true GI) |
| `T2_wt_ode.csv` | `time,method,rt_mean` | method ∈ {`wt_infection`, `wt_onset`} |
| `T3_gi_misspecification.csv` | `time,setting,rt_mean` | setting ∈ {`gi_mean_6`,…,`gi_mean_10`, `gi_var_8`, `gi_var_16`, `gi_var_32`, `gi_var_64`, `gi_var_128`} |
| `T4_smoothing_window.csv` | `time,setting,rt_mean` | setting ∈ {`window_1_end`, `window_1_mid`, `window_7_end`, `window_7_mid`, `window_14_end`, `window_14_mid`} |
| `T5_backcalculated_infections.csv` | `time,series,infections` | series ∈ {`shift_case`, `shift_death`, `case_deconvolved`, `death_deconvolved`} |
| `T6_rt_from_delayed_data.csv` | `time,input,rt_mean` | input ∈ {`rt_true_infections`, `rt_shift_case`, `rt_shift_death`, `rt_case_deconvolved`} |
| `T7_case_reproduction_number.csv` | `time,R_case` | t = 0…150 |

Also submit `code/` and `NOTES.md` (qualitative conclusions on each source of bias).

## Allowed tools and restrictions

Any open-source library in R / Python (general-purpose R_t estimation packages may be used), single CPU machine, minutes of compute. Searching online for the original study's code or results is forbidden.

## Acceptance (overview)

Each time series is compared with the reference result by correlation coefficient and root-mean-square error (RMSE tolerance for R_t about 0.06–0.1; infection-count series are judged by correlation only); grouped tables require most series to pass. The task as a whole succeeds if at least 6 of the 7 tables pass.
