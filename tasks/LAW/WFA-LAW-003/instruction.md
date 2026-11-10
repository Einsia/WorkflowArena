> The working directory is `/workspace`. The task inputs are in `/workspace/inputs/` (the `inputs/` referred to below is this directory, e.g. `inputs/agreements/A01.txt` is `/workspace/inputs/agreements/A01.txt`), and the blank template is in `/workspace/templates/` (the `templates/` referred to below). "The files in this package" means the files under `/workspace/inputs/` and `/workspace/templates/`. Write your deliverables to `/workspace/submission/` instead of `outputs/`: `outputs/deal_points.csv` below means `/workspace/submission/deal_points.csv` and `outputs/answers.json` means `/workspace/submission/answers.json` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1, lxml 5.3.0, beautifulsoup4 4.12.3.

# Merger agreement deal-points survey: Pandemic-era provisions (MAE pandemic carve-out, interim-covenant pandemic exceptions)

You are given 18 definitive merger agreements for acquisitions of U.S. public companies, identified only as A01–A18 (`inputs/agreements/<ID>.txt`, plain text converted from the filed documents). Prepare a deal-points survey of these agreements, in the style of a market-practice ("deal points") study:

1. For every agreement, answer each of the 17 deal-point questions in `inputs/questionnaire.json` (reproduced below), choosing **only from the standard options** listed for that question.
2. Using the completed table, answer the 17 survey questions in `inputs/merge_questions.json` (reproduced below). These questions compare and aggregate answers across the agreements.

Party names, ticker symbols, product names and the names of signatories and notice recipients in the agreements have been replaced with fictitious placeholders; e-mail addresses and URLs have been removed. Treat the placeholders as the parties' real names.

Terminology: "Target" / "Company" is the company being acquired; "Buyer" / "Parent" is the acquirer (including its merger subsidiary). "MAE" means the material-adverse-effect definition applicable to the Target. "COR" is a change of the Target board's recommendation; "FTR" is the Target's right to terminate the agreement to accept a superior proposal. Answer from the text of each agreement as executed (including definitions incorporated by cross-reference).

## Rules

- Closed book: no internet access; use only the files in this package.
- Do not use outside knowledge of the transactions or of any published annotations of these agreements.
- Every cell must contain an exact standard option string (copy it verbatim). Multi-select deal points: join the selected options with ` | ` (space, pipe, space), in any order.

## Deliverables (write to `outputs/`)

1. `outputs/deal_points.csv` — columns `agreement,deal_point,answer`, one row per agreement × deal point (306 rows). A blank template is in `templates/deal_points_template.csv`. Use standard CSV quoting (options contain quotes and commas).
2. `outputs/answers.json` — a JSON object mapping each merge-question id (`M01`, …) to its answer:
   - integer questions: a JSON integer;
   - agreement lists: a JSON list of agreement ids, e.g. `["A03", "A11"]` (order irrelevant; `[]` if none);
   - distributions: a JSON object mapping every standard option of the deal point to an integer count;
   - groups: a JSON list of lists of agreement ids, e.g. `[["A01", "A07"], ["A02", "A05", "A09"]]`.

## Grading

- **Branch score**: mean per-cell score over the table — exact match for single-select deal points, set F1 for multi-select deal points.
- **Merge score**: fraction of merge questions answered exactly right (compared with reference answers).
- **Full success**: branch score ≥ 0.90 **and** merge score ≥ 0.75.

## Deal-point questionnaire

### `mae_co_pandemic` (Material Adverse Effect)

MAE carve-out: pandemics, epidemics or other public health events?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_pandemic_covid` (Material Adverse Effect)

Does the MAE definition specifically refer to COVID-19 (by name) in its carve-outs?

Options: `No`; `Yes`

Note: Answer "No" if there is no pandemic carve-out.

### `mae_co_pandemic_measures` (Material Adverse Effect)

Does the pandemic carve-out specifically refer to governmental (or industry) responses/measures related to the pandemic (e.g., shutdowns, "COVID-19 Measures", quarantine or stay-at-home orders)?

Options: `No`; `Yes`

Note: Answer "No" if there is no pandemic carve-out.

### `mae_di_pandemic` (Material Adverse Effect)

Is the pandemic/public-health carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_co_economic` (Material Adverse Effect)

MAE carve-out: general economic and/or financial (including capital/credit market) conditions?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_di_economic` (Material Adverse Effect)

Is the general economic/financial conditions carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_co_wnaf_scope` (Material Adverse Effect) — multi-select

Which of the following does the MAE carve-out for calamities cover: war or terrorism, natural disasters, "acts of God", force majeure? (select all that apply)

Options: `"act of God"`; `Natural disaster`; `No`; `War or terrorism`; `force majeure`

Note: Select an item only if the carve-out expressly covers that category (e.g., select "force majeure" only if the words force majeure are used). Select only "No" if there is no such carve-out.

### `mae_di_wnaf` (Material Adverse Effect) — multi-select

Which parts of the war/terrorism / natural disaster / act of God / force majeure carve-out are subject to a "disproportionate impact" modifier? (select all that apply)

Options: `"act of God"`; `Natural disaster`; `No`; `War or terrorism`; `force majeure`

Note: Select only "No" if no part of that carve-out is subject to a disproportionate-impact modifier (or there is no such carve-out).

### `mae_co_required_actions` (Material Adverse Effect)

MAE carve-out: actions required to be taken (or taken in compliance with) the merger agreement?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_prohibited_actions` (Material Adverse Effect)

MAE carve-out: the Target's failure to take an action that is prohibited by the agreement (e.g., under the interim operating covenants) where the Buyer withheld consent?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `oc_pandemic_carveout` (Operating and Efforts Covenant)

Ordinary-course covenant: does it include an exception for actions taken in response to the pandemic (e.g., COVID-19 measures)?

Options: `No`; `Yes`

### `nc_pandemic_carveout` (Operating and Efforts Covenant)

Negative interim operating covenants: do they include an exception for actions taken in response to the pandemic (e.g., COVID-19 measures)?

Options: `No`; `Yes`

### `oc_past_practice` (Operating and Efforts Covenant)

Ordinary-course covenant: does it require operation in the ordinary course "consistent with past practice"?

Options: `No`; `Yes`

### `oc_efforts_standard` (Operating and Efforts Covenant)

Ordinary-course covenant: what efforts standard qualifies the Target's obligation to operate in the ordinary course?

Options: `Commercially reasonable efforts`; `Flat covenant (no efforts standard)`; `Reasonable best efforts`

### `oc_consent_standard` (Operating and Efforts Covenant)

Ordinary-course covenant: is the Buyer's consent to deviate from the ordinary course a flat consent or one that may not be unreasonably withheld, conditioned or delayed?

Options: `Consent may not be unreasonably withheld, conditioned or delayed`; `Flat consent`

### `nc_consent_standard` (Operating and Efforts Covenant)

Negative interim operating covenants (list of prohibited actions): is the Buyer's consent a flat consent or one that may not be unreasonably withheld, conditioned or delayed?

Options: `Consent may not be unreasonably withheld, conditioned or delayed`; `Flat consent`

### `nc_consent_application` (Operating and Efforts Covenant)

Negative interim operating covenants: does the "not unreasonably withheld" consent standard apply to all of the negative covenants or only to specified ones?

Options: `Applies only to specified negative covenants`; `Applies to all negative covenants`

## Merge (survey) questions

All questions refer to the 18 agreements A01–A18 and to their answers in your deal-point table; `dp` = «X» means the agreement's answer to that deal point is exactly the standard option X (guillemets delimit the option string); `dp` includes «X» means a multi-select answer contains option X.

- **M01**. Give the distribution of answers to `mae_di_wnaf` across all 18 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (count each agreement once for every option included in its answer).
- **M02**. Give the distribution of answers to `mae_co_pandemic_covid` across all 18 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M03**. How many of the 18 agreements satisfy ALL of the following: `nc_pandemic_carveout` = «No» AND NOT (`oc_efforts_standard` = «Reasonable best efforts»)? Answer with an integer.
- **M04**. How many of the 18 agreements satisfy ALL of the following: `oc_consent_standard` = «Consent may not be unreasonably withheld, conditioned or delayed» AND `nc_consent_standard` = «Consent may not be unreasonably withheld, conditioned or delayed»? Answer with an integer.
- **M05**. How many of the 18 agreements satisfy ALL of the following: `mae_co_pandemic` = «Yes» AND NOT (`mae_di_wnaf` includes «"act of God"»)? Answer with an integer.
- **M06**. List every agreement that satisfies: `mae_co_pandemic_measures` = «Yes» AND `mae_co_wnaf_scope` includes «"act of God"». If no agreement qualifies, answer with an empty list [].
- **M07**. List every agreement that satisfies: `oc_pandemic_carveout` = «No» AND `nc_consent_application` = «Applies to all negative covenants». If no agreement qualifies, answer with an empty list [].
- **M08**. List every agreement that satisfies: `mae_di_economic` = «No» AND `mae_co_required_actions` = «No». If no agreement qualifies, answer with an empty list [].
- **M09**. List every agreement that satisfies: `mae_co_economic` = «Yes» AND `mae_di_economic` = «No». If no agreement qualifies, answer with an empty list [].
- **M10**. List every agreement that satisfies: NOT (`mae_di_pandemic` gives the same answer as `mae_di_economic`). If no agreement qualifies, answer with an empty list [].
- **M11**. Which agreement(s) have the lowest value of the number of options selected for `mae_co_wnaf_scope` (not counting 'No')? List all tied agreements.
- **M12**. For `mae_co_pandemic_covid`, list every agreement whose answer is shared by at most 3 of the 18 agreements (counting the agreement itself).
- **M13**. For `nc_consent_standard`, list every agreement whose answer is shared by at most 3 of the 18 agreements (counting the agreement itself).
- **M14**. Consider the deal points `mae_co_pandemic`, `mae_co_pandemic_covid`, `mae_co_pandemic_measures`, `mae_di_pandemic`, `mae_co_economic`, `mae_di_economic`, `mae_co_wnaf_scope`, `mae_di_wnaf`, `mae_co_required_actions`, `mae_co_prohibited_actions`, `nc_pandemic_carveout`, `oc_past_practice`, `oc_efforts_standard`, `oc_consent_standard`, `nc_consent_standard`, `nc_consent_application`. For each of them, take the most common answer across the 18 agreements (complete answer; for each listed deal point the most common answer is unique). List every agreement whose answer differs from that most common answer on at least 11 of these deal points.
- **M15**. Considering only `oc_pandemic_carveout`, `oc_past_practice`, `oc_consent_standard`: group together agreements whose answers are identical on every one of these deal points. Report every group with two or more agreements, as a list of lists of agreement ids (agreements with a unique combination are omitted).
- **M16**. Considering only `mae_co_pandemic_measures`, `mae_di_pandemic`, `mae_co_prohibited_actions`: how many distinct answer combinations occur among the 18 agreements? Answer with an integer.
- **M17**. Which other agreement(s) give the same answer as A01 on the largest number of the 17 deal points in the questionnaire? (A multi-select answer counts as the same only if the full set matches.) List all tied agreements.
