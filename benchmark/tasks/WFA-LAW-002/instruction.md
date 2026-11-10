> The working directory is `/workspace`. The task inputs are in `/workspace/inputs/` (the `inputs/` referred to below is this directory, e.g. `inputs/agreements/A01.txt` is `/workspace/inputs/agreements/A01.txt`), and the blank template is in `/workspace/templates/` (the `templates/` referred to below). "The files in this package" means the files under `/workspace/inputs/` and `/workspace/templates/`. Write your deliverables to `/workspace/submission/` instead of `outputs/`: `outputs/deal_points.csv` below means `/workspace/submission/deal_points.csv` and `outputs/answers.json` means `/workspace/submission/answers.json` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1, lxml 5.3.0, beautifulsoup4 4.12.3.

# Merger agreement deal-points survey: MAE definition structure and transaction-related carve-outs

You are given 15 definitive merger agreements for acquisitions of U.S. public companies, identified only as A01–A15 (`inputs/agreements/<ID>.txt`, plain text converted from the filed documents). Prepare a deal-points survey of these agreements, in the style of a market-practice ("deal points") study:

1. For every agreement, answer each of the 16 deal-point questions in `inputs/questionnaire.json` (reproduced below), choosing **only from the standard options** listed for that question.
2. Using the completed table, answer the 16 survey questions in `inputs/merge_questions.json` (reproduced below). These questions compare and aggregate answers across the agreements.

Party names, ticker symbols, product names and the names of signatories and notice recipients in the agreements have been replaced with fictitious placeholders; e-mail addresses and URLs have been removed. Treat the placeholders as the parties' real names.

Terminology: "Target" / "Company" is the company being acquired; "Buyer" / "Parent" is the acquirer (including its merger subsidiary). "MAE" means the material-adverse-effect definition applicable to the Target. "COR" is a change of the Target board's recommendation; "FTR" is the Target's right to terminate the agreement to accept a superior proposal. Answer from the text of each agreement as executed (including definitions incorporated by cross-reference).

## Rules

- Closed book: no internet access; use only the files in this package.
- Do not use outside knowledge of the transactions or of any published annotations of these agreements.
- Every cell must contain an exact standard option string (copy it verbatim). Multi-select deal points: join the selected options with ` | ` (space, pipe, space), in any order.

## Deliverables (write to `outputs/`)

1. `outputs/deal_points.csv` — columns `agreement,deal_point,answer`, one row per agreement × deal point (240 rows). A blank template is in `templates/deal_points_template.csv`. Use standard CSV quoting (options contain quotes and commas).
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

### `mae_taken_as_whole` (Material Adverse Effect)

Does the Target MAE definition measure the adverse effect on the Target and its subsidiaries "taken as a whole"?

Options: `Applies to Target and subsidiaries "taken as a whole"`; `No`

### `mae_ability_to_consummate` (Material Adverse Effect)

Does the Target MAE definition include (as a separate prong) an adverse effect on the Target's ability to consummate the transaction / perform its obligations?

Options: `No`; `Yes`

### `mae_ability_subject_to_carveouts` (Material Adverse Effect)

Is the "ability to consummate" prong of the MAE definition subject to the MAE carve-outs?

Options: `No`; `Yes`

Note: Answer "No" if the definition has no ability-to-consummate prong, or if the carve-outs apply only to the business/financial-condition prong.

### `mae_fls_yn` (Material Adverse Effect)

Does the MAE definition contain a forward-looking standard (e.g., an effect that "would reasonably be expected to" have an MAE)?

Options: `No`; `Yes`

### `mae_fls_standard` (Material Adverse Effect)

Which forward-looking standard does the MAE definition use?

Options: `"Could" (reasonably) be expected to`; `"Would"`; `"Would" (reasonably) be expected to`; `No`; `Other forward-looking standard`

Note: Answer "No" if there is no forward-looking standard.

### `mae_fls_applies_to` (Material Adverse Effect) — multi-select

To which prong(s) of the MAE definition does the forward-looking standard apply? (select all that apply)

Options: `No`; `ability to consummate transaction`; `business and operation of Target`

Note: Select only "No" if there is no forward-looking standard.

### `mae_relational_yn` (Material Adverse Effect)

Do the MAE carve-outs use relational language (e.g., matters "arising from", "resulting from", "relating to" or "attributable to" the excluded events)?

Options: `No`; `Yes`

### `mae_relational_scope` (Material Adverse Effect)

Does the relational language apply to all MAE carve-outs or only some?

Options: `All MAE carveouts`; `No`; `Some MAE carveouts`

Note: Answer "No" if there is no relational language.

### `mae_relational_terms` (Material Adverse Effect) — multi-select

Which relational phrases are used in the MAE carve-outs? (select all that apply)

Options: `"Arising from/out of"`; `"Attributable to"`; `"Relating to"`; `"Resulting from"`; `No`; `Other`; `Relational language varies among carveouts`

Note: Select "Relational language varies among carveouts" in addition to the phrases if different carve-outs use different phrases. Select only "No" if there is no relational language.

### `mae_co_apc_scope` (Material Adverse Effect) — multi-select

Which of announcement / pendency / consummation of the transaction does the deal-related carve-out cover? (select all that apply)

Options: `No`; `announcement`; `consummation`; `pendency`

Note: Select only "No" if there is no such carve-out.

### `mae_co_required_actions` (Material Adverse Effect)

MAE carve-out: actions required to be taken (or taken in compliance with) the merger agreement?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_buyer_consent` (Material Adverse Effect)

MAE carve-out: actions taken (or not taken) at the request of, or with the consent or approval of, the Buyer?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_stockholder_litigation` (Material Adverse Effect)

MAE carve-out: stockholder litigation/proceedings relating to the agreement or the transaction?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_disclosure_schedules` (Material Adverse Effect)

MAE carve-out: matters disclosed in the Target's disclosure schedules (or disclosure letter)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_buyer_actions` (Material Adverse Effect)

MAE carve-out: actions taken by the Buyer or its affiliates (including breaches by the Buyer, or the identity of the Buyer)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_prohibited_actions` (Material Adverse Effect)

MAE carve-out: the Target's failure to take an action that is prohibited by the agreement (e.g., under the interim operating covenants) where the Buyer withheld consent?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

## Merge (survey) questions

All questions refer to the 15 agreements A01–A15 and to their answers in your deal-point table; `dp` = «X» means the agreement's answer to that deal point is exactly the standard option X (guillemets delimit the option string); `dp` includes «X» means a multi-select answer contains option X.

- **M01**. Give the distribution of answers to `mae_relational_scope` across all 15 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M02**. Give the distribution of answers to `mae_relational_terms` across all 15 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (count each agreement once for every option included in its answer).
- **M03**. How many of the 15 agreements satisfy ALL of the following: `mae_taken_as_whole` = «Applies to Target and subsidiaries "taken as a whole"» AND `mae_co_buyer_consent` = «Yes»? Answer with an integer.
- **M04**. How many of the 15 agreements satisfy ALL of the following: `mae_fls_yn` = «Yes» AND `mae_co_disclosure_schedules` = «No»? Answer with an integer.
- **M05**. How many of the 15 agreements satisfy ALL of the following: `mae_ability_subject_to_carveouts` = «No» AND NOT (`mae_co_apc_scope` includes «consummation»)? Answer with an integer.
- **M06**. List every agreement that satisfies: `mae_ability_to_consummate` = «Yes» AND `mae_co_buyer_actions` = «Yes». If no agreement qualifies, answer with an empty list [].
- **M07**. List every agreement that satisfies: `mae_fls_standard` = «"Would" (reasonably) be expected to» AND `mae_fls_applies_to` includes «ability to consummate transaction». If no agreement qualifies, answer with an empty list [].
- **M08**. List every agreement that satisfies: `mae_co_stockholder_litigation` = «No» AND `mae_co_prohibited_actions` = «No». If no agreement qualifies, answer with an empty list [].
- **M09**. List every agreement that satisfies: `mae_taken_as_whole` = «No» AND `mae_relational_yn` = «No». If no agreement qualifies, answer with an empty list [].
- **M10**. Which agreement(s) have the lowest value of the number of options selected for `mae_fls_applies_to` (not counting 'No')? List all tied agreements.
- **M11**. For `mae_fls_yn`, list every agreement whose answer is shared by at most 3 of the 15 agreements (counting the agreement itself).
- **M12**. For `mae_relational_scope`, list every agreement whose answer is shared by at most 3 of the 15 agreements (counting the agreement itself).
- **M13**. Consider the deal points `mae_taken_as_whole`, `mae_ability_to_consummate`, `mae_ability_subject_to_carveouts`, `mae_fls_yn`, `mae_fls_standard`, `mae_fls_applies_to`, `mae_relational_yn`, `mae_relational_scope`, `mae_co_required_actions`, `mae_co_buyer_consent`, `mae_co_stockholder_litigation`, `mae_co_disclosure_schedules`, `mae_co_buyer_actions`, `mae_co_prohibited_actions`. For each of them, take the most common answer across the 15 agreements (complete answer; for each listed deal point the most common answer is unique). List every agreement whose answer differs from that most common answer on at least 8 of these deal points.
- **M14**. Considering only `mae_co_apc_scope`, `mae_co_required_actions`, `mae_co_disclosure_schedules`: group together agreements whose answers are identical on every one of these deal points. Report every group with two or more agreements, as a list of lists of agreement ids (agreements with a unique combination are omitted).
- **M15**. Considering only `mae_relational_yn`, `mae_relational_terms`, `mae_co_required_actions`: how many distinct answer combinations occur among the 15 agreements? Answer with an integer.
- **M16**. Which other agreement(s) give the same answer as A06 on the largest number of the 16 deal points in the questionnaire? (A multi-select answer counts as the same only if the full set matches.) List all tied agreements.
