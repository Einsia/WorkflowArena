> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: put the CSV files required by the task directly in that directory, together with `code/` and `NOTES.md` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1; linearmodels 6.1.

# Effects of early-2020 non-pharmaceutical interventions in six countries on COVID-19 case growth rates (paper reproduction)

## Research question

Using daily sub-national (province / state / city) case and policy data for six countries (China, South Korea, Italy, Iran, France, the United States) from January to April 2020, estimate with panel regressions the effects of various containment policies on the "daily growth rate of log cases", then plug the estimates into a simple SIR-type transmission model and compare cumulative confirmed cases under "actual policies" and under a "no policy" counterfactual. You must implement all data processing, regressions, counterfactual predictions and transmission simulations yourself, and output 5 result tables.

## Given inputs (`inputs/`)

- `adm1/{FRA,IRN,ITA,KOR,USA}_processed.csv`, `adm2/{CHN,ITA}_processed.csv`: panels by administrative unit and date. Main columns: `date`; unit-name columns (`adm1_name`, `adm2_name`); `cum_confirmed_cases` (cumulative confirmed); `active_cases` (currently active confirmed cases, available for China and South Korea); `cum_hospitalized` (France); `population`; `testing_regime` (testing-regime index, incremented by 1 at every change of regime); and the policy variables. Policy variables take values in 0–1: without suffix they indicate whether the unit implemented the policy (some are the fraction partially implemented); the `_popwt` suffix is the population-weighted coverage fraction; `_opt` means "recommended / non-mandatory". For France, `no_gathering_size` is the maximum gathering size allowed at the time (99999 means no limit).
- `state_name_abbrev_xwalk.csv`: crosswalk between US state names and abbreviations.
- `case_detection_fraction.csv`: estimated fraction of true infections that are confirmed, per country (one row per country).
- `recovery_rate_estimates.csv`: daily removal rate γ estimated from Chinese and South Korean recovery data (`recovery_delay` is the assumed reporting delay in days).

## Method

### 1. Dependent variable and sample (common to all countries)

For each administrative unit, build a panel by date (take differences only with the observation of "exactly the previous day"; if the previous day's observation is missing, the difference is missing).

- For unit-days with cumulative confirmed cases < 10, treat the case counts as missing (for France and the USA delete these rows; for the other countries set them to missing).
- Default sample end date 2020-04-06 (except China, see below).
- Countries using cumulative confirmed cases (Italy, Iran, France, USA): `y = Δ log(cum_confirmed_cases)`; set `y < 0` to missing.
- Countries using active cases (China, South Korea): `y = Δ log(active_cases)`; if the raw `y < 0.04`, use `Δcum_confirmed_cases / active_cases(previous day)` instead; then set `y < 0` to missing.
- "Testing-regime change" dummies: for the whole country, order the regimes by the date on which each first appears, and create one dummy for the first day of every regime other than the first (= 1 on that day only). For the USA, set them per state: = 1 on the day a state's regime index increases by 1 relative to the previous day (one dummy per state per change).
- Regression: OLS absorbing unit fixed effects (and, except for China, day-of-week fixed effects), standard errors clustered by date, small-sample correction `G/(G-1)·(N-1)/(N-K)` (K includes the number of fixed-effect dummies).

### 2. Country specifications

- **South Korea** (province level, active cases): sample from 2020-02-17. `p_1 = (business_closure_opt + work_from_home_opt + social_distance_opt + no_gathering_opt)/4`; `p_2 = (no_demonstration + religious_closure + welfare_services_closure)/3`; `p_3 = emergency_declaration`; `p_4 = pos_cases_quarantine`. Control for testing-regime dummies.
- **Italy** (province / adm2 level, cumulative confirmed): drop `adm2_name == "Unknown"`; sample from 2020-02-26. `social_distance_comb = social_distance_popwt + 0.5·social_distance_opt_popwt`, `work_from_home_comb = work_from_home_popwt + 0.5·work_from_home_opt_popwt`; `p_1 = (no_gathering_popwt + social_distance_comb + work_from_home_comb)/3`, `p_2 = school_closure_popwt`, `p_3 = (travel_ban_local_popwt + transit_suspension_popwt)/2`, `p_4 = pos_cases_quarantine_popwt`, `p_5 = business_closure_popwt`, `p_6 = home_isolation_popwt`. No testing-regime dummies. Also report the linear combination `home_iso_combined = p_1 + 0.25·p_3 + 0.67·p_5 + p_6`.
- **Iran** (province level, cumulative confirmed): sample from 2020-02-27; there were no reports on 2020-03-02 and 03-03, so set `y` to missing on these two days. There is only one testing dummy, 2020-03-13. `travel_ban_local_opt_natl = travel_ban_local_opt` (but 0 for Qom province); `school_closure_natl`: equals `school_closure` if the province's minimum of `school_closure` over the sample period is 0, otherwise 0. `p_1 = (travel_ban_local_opt_natl + work_from_home + school_closure_natl)/3`, `p_2 = home_isolation`.
- **France** (region level, cumulative confirmed): sample from 2020-02-29. There is only one testing dummy, 2020-03-15. `national_lockdown = (business_closure + home_isolation_popwt)/2`; `pck_social_distance = (1[no_gathering_size ≤ 1000] + 1[no_gathering_size ≤ 100] + event_cancel_popwt + no_gathering_inside_popwt + social_distance_popwt)/5`; the third policy variable is `school_closure_popwt`. Also report `natl_lockdown_comb = national_lockdown + pck_social_distance`.
- **USA** (state level, cumulative confirmed): sample from 2020-03-03. `p_1 = no_gathering_popwt`, `p_2 = social_distance_popwt`, `p_3 = pos_cases_quarantine_popwt`, `p_4 = paid_sick_leave_popwt`, `p_5 = work_from_home_popwt`, `p_6 = school_closure_popwt`, `p_7 = (travel_ban_local_popwt + transit_suspension_popwt)/2`, `p_8 = business_closure_popwt`, `p_9 = religious_closure_popwt`, `p_10 = home_isolation_popwt`, `p_11 = federal_guidelines`. Control for the per-state testing-regime dummies. Also report `home_iso_combined = p_10 + p_1 + p_5 + p_8`.
- **China** (city / adm2 level, active cases; unit = province + city): sample ends 2020-03-05; set case data before 2020-01-16 to missing. Once a city lifts its local travel restriction (`travel_ban_local` changes from 1 to 0), delete all observations of that city from the day of lifting onward. Keep only cities for which `home_isolation` or `travel_ban_local` equals 1 at least once during the sample period. Construct `y` as above, and in addition set `y > 1.5` to missing and `y == 0` in January to missing. Policies enter the regression binned by "days since the policy started (changed from 0 to 1)": for each of `emergency_declaration`, `travel_ban_local` and `home_isolation` generate 5 dummies `<policy>_L0_to_L7`, `_L8_to_L14`, `_L15_to_L21`, `_L22_to_L28`, `_L29_to_L70` (= 1 if the policy started 0–7 days ago, 8–14 days ago, …). Absorb only city fixed effects (no day-of-week effects) and control for testing-regime dummies. Also report, for each bin, `home_iso_<bin> + trvl_ban_loc_<bin>` (the sum of the two) and the sum of the three policies (`first week` … `fifth week and after`). In addition, run a separate OLS without fixed effects for the single city of Wuhan (same binned policy variables + testing dummies, conventional non-clustered standard errors), and take the intercept as Wuhan's "no-policy growth rate".

### 3. Summary quantities

- For each country, `comb. policy` = the sum of all policy coefficients (not reported for China), with the standard error computed from the clustered covariance matrix.
- "No-policy growth rate" `no_policy rate`: on the regression sample compute `y_counter = fitted value − Σ policy variable·coefficient` (keeping the fixed effects, testing dummies and intercept), truncate negative values to 0, and report its sample mean (column `beta`) and sample standard deviation (column `se`).
- Daily growth rates: `y_actual = fitted value` and `y_counter` as above, both truncated at 0; then, for each country and each date, average over all units in the regression sample.

### 4. Counterfactual transmission simulation

For each country, re-estimate the point estimates with the same specification as in Section 2 (unit fixed effects and day-of-week effects as dummy variables; no day-of-week for China), then for each unit:

- Start from the unit's first date with non-missing cumulative confirmed cases and run to the sample end date. For every day after the first, use the model to predict that day's growth rate `g_t` (two scenarios: actual policies / all policy variables set to 0; predictions are not truncated, and fixed effects, day of week and testing dummies are included as usual).
- SIR simulation: 6 sub-steps per day, `γ' = (1+γ)^(1/6) − 1`, where γ = the mean of the China and South Korea γ values with `recovery_delay = 0` in `recovery_rate_estimates.csv`; the detection fraction `q` is that country's value in `case_detection_fraction.csv`. Initial values: `I_0 = cumulative confirmed on the first day / q`, `S_0 = population − I_0`, cumulative confirmed `C_0` = cumulative confirmed on the first day. In each sub-step: `r = (g_t/6 + γ')·S/N`; `I_new = I·exp(r − γ')`; `S_new = S − I_new·r`; new infections = `I_new − I + I·γ'`; `C += new infections · q`. The daily value is `C` at the last sub-step of the day.
- Country level: each day, sum `C` over all units to obtain the cumulative-confirmed curves under "actual policies" and "no policy".
- Sensitivity analysis (SEIR variant): recompute on the grid γ ∈ {0.05, 0.1, …, 0.4} and incubation exit rate σ ∈ {0.2, 0.33, 0.5, ∞} (σ = ∞ is the SIR above; for finite σ use per sub-step `σ' = (1+σ)^(1/6) − 1` and transmission rate `β' = (g/6 + γ')(g/6 + σ')/σ'`; the initial `E` is `I_0` times the ratio `E/I` in the eigenvector of the largest eigenvalue of the linearized system `[[−σ', β'],[σ', −γ']]`, where `g` here uses the second day's prediction truncated to be non-negative; per sub-step new exposures = `I·β'·S/N`, new onsets = `E·σ'`, `E += new exposures − new onsets`, `I += new onsets − I·γ'`, `S −= new exposures`, new infections = `I_new − I + I·γ'`). For each (γ, σ), sum the six countries' results on their respective last days and report the cumulative confirmed cases with actual policies, cumulative confirmed cases with no policy, their difference (cases averted), and the infections averted (= the cases averted converted to infections with each country's `q`, then summed).

### 5. Leave-one-out robustness check

For each country, drop one first-level administrative unit at a time (for China and Italy drop all cities of that province; for the others drop by adm1) and re-estimate the regression; report `comb. policy` (for China report the five weekly sums `first week` … `fifth week and after`) and `no_policy rate`; also report one full-sample row (`dropped_unit = full_sample`).

## Required outputs (CSV; column names must match exactly)

| File | Columns | Rows |
|---|---|---|
| `T1_coefficients.csv` | `country,term,beta,se` | country ∈ {CHN, KOR, ITA, IRN, FRA, USA, CHN_Wuhan}. term: South Korea `p_1..p_4`; Italy `p_1..p_6`, `home_iso_combined`; Iran `p_1,p_2`; France `national_lockdown`, `school_closure_popwt`, `pck_social_distance`, `natl_lockdown_comb`; USA `p_1..p_11`, `home_iso_combined`; each of these countries additionally has `comb. policy`, `no_policy rate`. China: the 15 binned variable names (e.g. `emergency_declaration_L0_to_L7`), the 5 combinations of the form `home_iso_L0_to_L7 + trvl_ban_loc_L0_to_L7` (strings exactly in this format, plus sign separated by spaces), `first week`, `second week`, `third week`, `fourth week`, `fifth week and after`, `no_policy rate`; `CHN_Wuhan,no_policy rate` (beta = Wuhan intercept, se = its standard error) |
| `T2_daily_growth.csv` | `country,date,growth_with_policy,growth_no_policy` | every date that appears in each country's regression sample (`date` as YYYY-MM-DD) |
| `T3_projection.csv` | `country,date,cum_cases_with_policy,cum_cases_no_policy` | every day for each country from the simulation start date (the first day holds the initial values) to the sample end date |
| `T4_leave_one_out.csv` | `country,dropped_unit,term,beta` | see Section 5; `dropped_unit` uses the first-level administrative unit names in the input data, plus `full_sample` |
| `T5_sensitivity.csv` | `gamma,sigma,predicted_cum_confirmed_cases_true,predicted_cum_confirmed_cases_no_policy,cases_saved,infections_saved` | γ ∈ {0.05,…,0.4} × σ ∈ {0.2, 0.33, 0.5, Inf} (write σ = ∞ as the string `Inf`) |

Also submit `code/` (re-runnable) and a short `NOTES.md`.

## Allowed tools and restrictions

Any open-source library in Python / R / Julia, single machine, CPU only; all computations take minutes. Searching online for the original study's code or results is not allowed.

## Acceptance (overview)

Tables are compared cell by cell: regression coefficients, standard errors and growth rates by absolute error; cumulative cases by log error. Each table requires most of its cells to be within tolerance; the task as a whole succeeds if at least 4 of the 5 tables pass.
