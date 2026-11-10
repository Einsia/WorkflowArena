> The working directory is `/workspace`. The task inputs are in `/workspace/inputs/` (the `inputs/` referred to below is this directory, e.g. `inputs/agreements/A01.txt` is `/workspace/inputs/agreements/A01.txt`), and the blank template is in `/workspace/templates/` (the `templates/` referred to below). "The files in this package" means the files under `/workspace/inputs/` and `/workspace/templates/`. Write your deliverables to `/workspace/submission/` instead of `outputs/`: `outputs/deal_points.csv` below means `/workspace/submission/deal_points.csv` and `outputs/answers.json` means `/workspace/submission/answers.json` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1, lxml 5.3.0, beautifulsoup4 4.12.3.

# Merger agreement deal-points survey: Buyer-side closing risk (MAE + conditions + efforts + remedies)

You are given 12 definitive merger agreements for acquisitions of U.S. public companies, identified only as A01–A12 (`inputs/agreements/<ID>.txt`, plain text converted from the filed documents). Prepare a deal-points survey of these agreements, in the style of a market-practice ("deal points") study:

1. For every agreement, answer each of the 22 deal-point questions in `inputs/questionnaire.json` (reproduced below), choosing **only from the standard options** listed for that question.
2. Using the completed table, answer the 17 survey questions in `inputs/merge_questions.json` (reproduced below). These questions compare and aggregate answers across the agreements.

Party names, ticker symbols, product names and the names of signatories and notice recipients in the agreements have been replaced with fictitious placeholders; e-mail addresses and URLs have been removed. Treat the placeholders as the parties' real names.

Terminology: "Target" / "Company" is the company being acquired; "Buyer" / "Parent" is the acquirer (including its merger subsidiary). "MAE" means the material-adverse-effect definition applicable to the Target. "COR" is a change of the Target board's recommendation; "FTR" is the Target's right to terminate the agreement to accept a superior proposal. Answer from the text of each agreement as executed (including definitions incorporated by cross-reference).

## Rules

- Closed book: no internet access; use only the files in this package.
- Do not use outside knowledge of the transactions or of any published annotations of these agreements.
- Every cell must contain an exact standard option string (copy it verbatim). Multi-select deal points: join the selected options with ` | ` (space, pipe, space), in any order.

## Deliverables (write to `outputs/`)

1. `outputs/deal_points.csv` — columns `agreement,deal_point,answer`, one row per agreement × deal point (264 rows). A blank template is in `templates/deal_points_template.csv`. Use standard CSV quoting (options contain quotes and commas).
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

### `mae_fls_standard` (Material Adverse Effect)

Which forward-looking standard does the MAE definition use?

Options: `"Could" (reasonably) be expected to`; `"Would"`; `"Would" (reasonably) be expected to`; `No`; `Other forward-looking standard`

Note: Answer "No" if there is no forward-looking standard.

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

### `mae_co_market_price` (Material Adverse Effect)

MAE carve-out: changes in the market price or trading volume of the Target's securities, or in its credit rating (in and of themselves)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_pandemic` (Material Adverse Effect)

MAE carve-out: pandemics, epidemics or other public health events?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_di_economic` (Material Adverse Effect)

Is the general economic/financial conditions carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_di_industry` (Material Adverse Effect)

Is the industry-changes carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_di_pandemic` (Material Adverse Effect)

Is the pandemic/public-health carve-out subject to a "disproportionate impact" modifier?

Options: `No`; `Yes`

Note: Answer "Yes" only if this carve-out exists AND it is expressly subject to a "disproportionate effect" exception (i.e., the carve-out does not apply to the extent the matter disproportionately affects the Target relative to other participants in its industry). If the carve-out does not exist, answer "No".

### `mae_co_stockholder_litigation` (Material Adverse Effect)

MAE carve-out: stockholder litigation/proceedings relating to the agreement or the transaction?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_disclosure_schedules` (Material Adverse Effect)

MAE carve-out: matters disclosed in the Target's disclosure schedules (or disclosure letter)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `cc_general_bringdown_timing` (Conditions to Closing)

Closing condition on accuracy of the Target's general representations and warranties: as of which time(s) must they be accurate?

Options: `At Closing Only`; `At Signing & At Closing`

### `cc_cap_bringdown_standard` (Conditions to Closing)

Closing condition on accuracy of the Target's capitalization representation (outstanding shares): what accuracy standard applies?

Options: `Accurate in all material respects`; `Accurate in all respects`; `Accurate in all respects with below-threshold carveout`; `Accurate in all respects with de minimis exception`

### `cc_fund_bringdown_standard` (Conditions to Closing)

Closing condition on accuracy of the Target's fundamental representations (other than capitalization): what accuracy standard applies?

Options: `Accurate at another materiality standard (e.g., hybrid standard)`; `Accurate in all material respects`; `Accurate in all respects`

Note: If different fundamental representations are held to different standards (e.g., some in all respects, others in all material respects), answer "Accurate at another materiality standard (e.g., hybrid standard)".

### `cc_scrape_applies_to` (Conditions to Closing) — multi-select

To which representations does the materiality/MAE "scrape" in the bring-down closing condition apply (i.e., materiality qualifiers in the representations are disregarded when testing accuracy)? (select all that apply)

Options: `Capitalization R&Ws`; `General R&Ws`; `Specified R&Ws only`; `fundamental/Special R&Ws`

### `cc_covenant_compliance` (Conditions to Closing)

Closing condition on the Target's performance of covenants: is the materiality standard applied to the covenants collectively or to each covenant individually?

Options: `All Covenants`; `Each Covenant`; `Hybrid/Other Standard`

Note: "All Covenants" = the Target shall have performed in all material respects all covenants/obligations (collective); "Each Covenant" = each covenant/obligation shall have been performed in all material respects.

### `ef_antitrust_standard` (Operating and Efforts Covenant)

What general efforts standard applies to obtaining antitrust/regulatory approvals?

Options: `Commercially reasonable efforts`; `Flat standard`; `Reasonable best efforts`

Note: "Flat standard" = the covenant on obtaining antitrust/regulatory approvals is not qualified by "reasonable best efforts" or "commercially reasonable efforts" (e.g. the parties "shall take all actions necessary" to obtain the approvals, or use plain "best efforts"). If that covenant is qualified by reasonable best efforts or commercially reasonable efforts, choose that option, even if a separate clause (e.g. a divestiture / hell-or-high-water undertaking) is unqualified.

### `oc_efforts_standard` (Operating and Efforts Covenant)

Ordinary-course covenant: what efforts standard qualifies the Target's obligation to operate in the ordinary course?

Options: `Commercially reasonable efforts`; `Flat covenant (no efforts standard)`; `Reasonable best efforts`

### `rem_specific_performance` (Remedies)

Specific performance: are the parties "entitled to" specific performance, or only "entitled to seek" it?

Options: `"entitled to seek" specific performance`; `"entitled to" specific performance`

### `kn_definition` (Knowledge)

Target knowledge definition: actual knowledge only, or constructive knowledge (e.g., knowledge after reasonable inquiry, or that would reasonably be expected to be known)?

Options: `Actual knowledge`; `Constructive knowledge`

## Merge (survey) questions

All questions refer to the 12 agreements A01–A12 and to their answers in your deal-point table; `dp` = «X» means the agreement's answer to that deal point is exactly the standard option X (guillemets delimit the option string); `dp` includes «X» means a multi-select answer contains option X.

- **M01**. Give the distribution of answers to `mae_di_economic` across all 12 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M02**. Give the distribution of answers to `rem_specific_performance` across all 12 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M03**. How many of the 12 agreements satisfy ALL of the following: `mae_taken_as_whole` = «Applies to Target and subsidiaries "taken as a whole"» AND NOT (`cc_fund_bringdown_standard` = «Accurate in all respects»)? Answer with an integer.
- **M04**. How many of the 12 agreements satisfy ALL of the following: `mae_co_political` = «Yes» AND `mae_co_market_price` = «Yes»? Answer with an integer.
- **M05**. How many of the 12 agreements satisfy ALL of the following: `mae_co_disclosure_schedules` = «No» AND NOT (`cc_scrape_applies_to` includes «fundamental/Special R&Ws»)? Answer with an integer.
- **M06**. List every agreement that satisfies: `mae_co_stockholder_litigation` = «Yes» AND `oc_efforts_standard` = «Commercially reasonable efforts». If no agreement qualifies, answer with an empty list [].
- **M07**. List every agreement that satisfies: `cc_cap_bringdown_standard` = «Accurate in all material respects» AND NOT (`cc_covenant_compliance` = «Each Covenant»). If no agreement qualifies, answer with an empty list [].
- **M08**. List every agreement that satisfies: `mae_co_economic` = «No» AND `ef_antitrust_standard` = «Flat standard». If no agreement qualifies, answer with an empty list [].
- **M09**. List every agreement that satisfies: `mae_fls_standard` = «No» AND `mae_di_pandemic` = «No». If no agreement qualifies, answer with an empty list [].
- **M10**. List every agreement that satisfies: NOT (`mae_di_industry` gives the same answer as `mae_di_pandemic`). If no agreement qualifies, answer with an empty list [].
- **M11**. Which agreement(s) have the highest value of the number of options selected for `cc_scrape_applies_to` (not counting 'No')? List all tied agreements.
- **M12**. For `mae_co_industry`, list every agreement whose answer is shared by at most 3 of the 12 agreements (counting the agreement itself).
- **M13**. For `mae_co_pandemic`, list every agreement whose answer is shared by at most 1 of the 12 agreements (counting the agreement itself).
- **M14**. Consider the deal points `mae_taken_as_whole`, `mae_ability_to_consummate`, `mae_fls_standard`, `mae_co_political`, `mae_co_economic`, `mae_co_industry`, `mae_co_market_price`, `mae_co_pandemic`, `mae_di_economic`, `mae_di_industry`, `mae_di_pandemic`, `mae_co_stockholder_litigation`, `mae_co_disclosure_schedules`, `cc_general_bringdown_timing`, `cc_cap_bringdown_standard`, `cc_fund_bringdown_standard`, `cc_scrape_applies_to`, `cc_covenant_compliance`, `ef_antitrust_standard`, `oc_efforts_standard`, `rem_specific_performance`. For each of them, take the most common answer across the 12 agreements (complete answer; for each listed deal point the most common answer is unique). List every agreement whose answer differs from that most common answer on at least 9 of these deal points.
- **M15**. Considering only `mae_di_pandemic`, `cc_general_bringdown_timing`, `kn_definition`: group together agreements whose answers are identical on every one of these deal points. Report every group with two or more agreements, as a list of lists of agreement ids (agreements with a unique combination are omitted).
- **M16**. Considering only `mae_ability_to_consummate`, `mae_co_political`, `kn_definition`: how many distinct answer combinations occur among the 12 agreements? Answer with an integer.
- **M17**. Which other agreement(s) give the same answer as A01 on the largest number of the 22 deal points in the questionnaire? (A multi-select answer counts as the same only if the full set matches.) List all tied agreements.
