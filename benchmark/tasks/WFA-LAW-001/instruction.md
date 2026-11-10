> The working directory is `/workspace`. The task inputs are in `/workspace/inputs/` (the `inputs/` referred to below is this directory, e.g. `inputs/agreements/A01.txt` is `/workspace/inputs/agreements/A01.txt`), and the blank template is in `/workspace/templates/` (the `templates/` referred to below). "The files in this package" means the files under `/workspace/inputs/` and `/workspace/templates/`. Write your deliverables to `/workspace/submission/` instead of `outputs/`: `outputs/deal_points.csv` below means `/workspace/submission/deal_points.csv` and `outputs/answers.json` means `/workspace/submission/answers.json` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1, lxml 5.3.0, beautifulsoup4 4.12.3.

# Merger agreement deal-points survey: MAE carve-outs and disproportionate-impact modifiers

You are given 16 definitive merger agreements for acquisitions of U.S. public companies, identified only as A01–A16 (`inputs/agreements/<ID>.txt`, plain text converted from the filed documents). Prepare a deal-points survey of these agreements, in the style of a market-practice ("deal points") study:

1. For every agreement, answer each of the 18 deal-point questions in `inputs/questionnaire.json` (reproduced below), choosing **only from the standard options** listed for that question.
2. Using the completed table, answer the 17 survey questions in `inputs/merge_questions.json` (reproduced below). These questions compare and aggregate answers across the agreements.

Party names, ticker symbols, product names and the names of signatories and notice recipients in the agreements have been replaced with fictitious placeholders; e-mail addresses and URLs have been removed. Treat the placeholders as the parties' real names.

Terminology: "Target" / "Company" is the company being acquired; "Buyer" / "Parent" is the acquirer (including its merger subsidiary). "MAE" means the material-adverse-effect definition applicable to the Target. "COR" is a change of the Target board's recommendation; "FTR" is the Target's right to terminate the agreement to accept a superior proposal. Answer from the text of each agreement as executed (including definitions incorporated by cross-reference).

## Rules

- Closed book: no internet access; use only the files in this package.
- Do not use outside knowledge of the transactions or of any published annotations of these agreements.
- Every cell must contain an exact standard option string (copy it verbatim). Multi-select deal points: join the selected options with ` | ` (space, pipe, space), in any order.

## Deliverables (write to `outputs/`)

1. `outputs/deal_points.csv` — columns `agreement,deal_point,answer`, one row per agreement × deal point (288 rows). A blank template is in `templates/deal_points_template.csv`. Use standard CSV quoting (options contain quotes and commas).
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

### `mae_co_political` (Material Adverse Effect)

MAE carve-out: general political and/or social conditions?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_economic` (Material Adverse Effect)

MAE carve-out: general economic and/or financial (including capital/credit market) conditions?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_industry` (Material Adverse Effect)

MAE carve-out: changes or conditions generally affecting the Target's industry?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_gaap` (Material Adverse Effect)

MAE carve-out: changes in GAAP or other accounting principles (or their interpretation)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_apc` (Material Adverse Effect)

MAE carve-out: the announcement, pendency and/or consummation of the transaction?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_apc_scope` (Material Adverse Effect) — multi-select

Which of announcement / pendency / consummation of the transaction does the deal-related carve-out cover? (select all that apply)

Options: `No`; `announcement`; `consummation`; `pendency`

Note: Select only "No" if there is no such carve-out.

### `mae_co_projections` (Material Adverse Effect)

MAE carve-out: failure by the Target to meet projections, forecasts, estimates or budgets (in and of itself)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_market_price` (Material Adverse Effect)

MAE carve-out: changes in the market price or trading volume of the Target's securities, or in its credit rating (in and of themselves)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_wnaf_scope` (Material Adverse Effect) — multi-select

Which of the following does the MAE carve-out for calamities cover: war or terrorism, natural disasters, "acts of God", force majeure? (select all that apply)

Options: `"act of God"`; `Natural disaster`; `No`; `War or terrorism`; `force majeure`

Note: Select an item only if the carve-out expressly covers that category (e.g., select "force majeure" only if the words force majeure are used). Select only "No" if there is no such carve-out.

### `mae_co_pandemic` (Material Adverse Effect)

MAE carve-out: pandemics, epidemics or other public health events?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_di_political` (Material Adverse Effect)

Is the general political/social conditions carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_di_economic` (Material Adverse Effect)

Is the general economic/financial conditions carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_di_industry` (Material Adverse Effect)

Is the industry-changes carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_di_law` (Material Adverse Effect)

Is the change-in-law carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_di_gaap` (Material Adverse Effect)

Is the change-in-GAAP/accounting-principles carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_di_pandemic` (Material Adverse Effect)

Is the pandemic/public-health carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_di_wnaf` (Material Adverse Effect) — multi-select

Which parts of the war/terrorism / natural disaster / act of God / force majeure carve-out are subject to a "disproportionate impact" modifier? (select all that apply)

Options: `"act of God"`; `Natural disaster`; `No`; `War or terrorism`; `force majeure`

Note: Select only "No" if no part of that carve-out is subject to a disproportionate-impact modifier (or there is no such carve-out).

## Merge (survey) questions

All questions refer to the 16 agreements A01–A16 and to their answers in your deal-point table; `dp` = «X» means the agreement's answer to that deal point is exactly the standard option X (guillemets delimit the option string); `dp` includes «X» means a multi-select answer contains option X.

- **M01**. Give the distribution of answers to `mae_di_gaap` across all 16 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M02**. Give the distribution of answers to `mae_co_political` across all 16 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M03**. How many of the 16 agreements satisfy ALL of the following: `mae_co_apc` = «Yes» AND `mae_di_wnaf` includes «War or terrorism»? Answer with an integer.
- **M04**. How many of the 16 agreements satisfy ALL of the following: `mae_taken_as_whole` = «Applies to Target and subsidiaries "taken as a whole"» AND NOT (`mae_co_wnaf_scope` includes «"act of God"»)? Answer with an integer.
- **M05**. How many of the 16 agreements satisfy ALL of the following: `mae_co_political` = «Yes» AND `mae_co_gaap` = «Yes»? Answer with an integer.
- **M06**. List every agreement that satisfies: `mae_co_industry` = «Yes» AND `mae_di_economic` = «No». If no agreement qualifies, answer with an empty list [].
- **M07**. List every agreement that satisfies: `mae_co_economic` = «Yes» AND `mae_co_market_price` = «Yes» AND NOT (`mae_co_apc_scope` includes «pendency»). If no agreement qualifies, answer with an empty list [].
- **M08**. List every agreement that satisfies: `mae_di_industry` = «No» AND `mae_di_law` = «Yes». If no agreement qualifies, answer with an empty list [].
- **M09**. List every agreement that satisfies: `mae_di_political` = «No» AND `mae_di_wnaf` includes «"act of God"». If no agreement qualifies, answer with an empty list [].
- **M10**. List every agreement that satisfies: NOT (`mae_co_pandemic` gives the same answer as `mae_di_pandemic`). If no agreement qualifies, answer with an empty list [].
- **M11**. Which agreement(s) have the highest value of the number of options selected for `mae_co_wnaf_scope` (not counting 'No')? List all tied agreements.
- **M12**. For `mae_co_projections`, list every agreement whose answer is shared by at most 3 of the 16 agreements (counting the agreement itself).
- **M13**. For `mae_co_apc`, list every agreement whose answer is shared by at most 2 of the 16 agreements (counting the agreement itself).
- **M14**. Consider the deal points `mae_taken_as_whole`, `mae_co_political`, `mae_co_economic`, `mae_co_industry`, `mae_co_gaap`, `mae_co_apc`, `mae_co_apc_scope`, `mae_co_projections`, `mae_co_market_price`, `mae_co_wnaf_scope`, `mae_co_pandemic`, `mae_di_political`, `mae_di_economic`, `mae_di_industry`, `mae_di_law`, `mae_di_gaap`, `mae_di_pandemic`, `mae_di_wnaf`. For each of them, take the most common answer across the 16 agreements (complete answer; for each listed deal point the most common answer is unique). List every agreement whose answer differs from that most common answer on at least 10 of these deal points.
- **M15**. Considering only `mae_taken_as_whole`, `mae_co_market_price`, `mae_di_pandemic`: group together agreements whose answers are identical on every one of these deal points. Report every group with two or more agreements, as a list of lists of agreement ids (agreements with a unique combination are omitted).
- **M16**. Considering only `mae_co_industry`, `mae_co_apc_scope`, `mae_di_economic`: how many distinct answer combinations occur among the 16 agreements? Answer with an integer.
- **M17**. Which other agreement(s) give the same answer as A07 on the largest number of the 18 deal points in the questionnaire? (A multi-select answer counts as the same only if the full set matches.) List all tied agreements.
