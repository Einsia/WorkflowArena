> The working directory is `/workspace`. The task inputs are in `/workspace/inputs/` (the `inputs/` referred to below is this directory, e.g. `inputs/agreements/A01.txt` is `/workspace/inputs/agreements/A01.txt`), and the blank template is in `/workspace/templates/` (the `templates/` referred to below). "The files in this package" means the files under `/workspace/inputs/` and `/workspace/templates/`. Write your deliverables to `/workspace/submission/` instead of `outputs/`: `outputs/deal_points.csv` below means `/workspace/submission/deal_points.csv` and `outputs/answers.json` means `/workspace/submission/answers.json` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1, lxml 5.3.0, beautifulsoup4 4.12.3.

# Merger agreement deal-points survey: Fundamental representations, bring-down mechanics and knowledge

You are given 20 definitive merger agreements for acquisitions of U.S. public companies, identified only as A01–A20 (`inputs/agreements/<ID>.txt`, plain text converted from the filed documents). Prepare a deal-points survey of these agreements, in the style of a market-practice ("deal points") study:

1. For every agreement, answer each of the 15 deal-point questions in `inputs/questionnaire.json` (reproduced below), choosing **only from the standard options** listed for that question.
2. Using the completed table, answer the 15 survey questions in `inputs/merge_questions.json` (reproduced below). These questions compare and aggregate answers across the agreements.

Party names, ticker symbols, product names and the names of signatories and notice recipients in the agreements have been replaced with fictitious placeholders; e-mail addresses and URLs have been removed. Treat the placeholders as the parties' real names.

Terminology: "Target" / "Company" is the company being acquired; "Buyer" / "Parent" is the acquirer (including its merger subsidiary). "MAE" means the material-adverse-effect definition applicable to the Target. "COR" is a change of the Target board's recommendation; "FTR" is the Target's right to terminate the agreement to accept a superior proposal. Answer from the text of each agreement as executed (including definitions incorporated by cross-reference).

## Rules

- Closed book: no internet access; use only the files in this package.
- Do not use outside knowledge of the transactions or of any published annotations of these agreements.
- Every cell must contain an exact standard option string (copy it verbatim). Multi-select deal points: join the selected options with ` | ` (space, pipe, space), in any order.

## Deliverables (write to `outputs/`)

1. `outputs/deal_points.csv` — columns `agreement,deal_point,answer`, one row per agreement × deal point (300 rows). A blank template is in `templates/deal_points_template.csv`. Use standard CSV quoting (options contain quotes and commas).
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

### `cc_fund_rw_types` (Conditions to Closing) — multi-select

Which Target representations are singled out in the closing conditions for a stricter-than-MAE bring-down standard ("fundamental" representations)? (select all that apply)

Options: `Approval`; `Authority`; `Brokers' Fee`; `Capitalization-Other`; `Enforceability`; `No MAE`; `No-Conflict`; `Opinion of Financial Advisor`; `Organization`; `Other`; `Rights Agreement`; `Subsidiaries`; `Takeover Statutes`; `Tax`

Note: "Capitalization-Other" = capitalization representations other than (or in addition to) the outstanding-share-count portion; "Approval" = board/stockholder approval and vote-required representations; "Authority" = corporate power and authority. Use "Other" for any other singled-out representation.

### `cc_fund_bringdown_standard` (Conditions to Closing)

Closing condition on accuracy of the Target's fundamental representations (other than capitalization): what accuracy standard applies?

Options: `Accurate at another materiality standard (e.g., hybrid standard)`; `Accurate in all material respects`; `Accurate in all respects`

Note: If different fundamental representations are held to different standards (e.g., some in all respects, others in all material respects), answer "Accurate at another materiality standard (e.g., hybrid standard)".

### `cc_cap_bringdown_standard` (Conditions to Closing)

Closing condition on accuracy of the Target's capitalization representation (outstanding shares): what accuracy standard applies?

Options: `Accurate in all material respects`; `Accurate in all respects`; `Accurate in all respects with below-threshold carveout`; `Accurate in all respects with de minimis exception`

### `cc_scrape_applies_to` (Conditions to Closing) — multi-select

To which representations does the materiality/MAE "scrape" in the bring-down closing condition apply (i.e., materiality qualifiers in the representations are disregarded when testing accuracy)? (select all that apply)

Options: `Capitalization R&Ws`; `General R&Ws`; `Specified R&Ws only`; `fundamental/Special R&Ws`

### `cc_general_bringdown_timing` (Conditions to Closing)

Closing condition on accuracy of the Target's general representations and warranties: as of which time(s) must they be accurate?

Options: `At Closing Only`; `At Signing & At Closing`

### `cc_general_bringdown_standard` (Conditions to Closing)

Closing condition on accuracy of the Target's general representations and warranties: what accuracy standard applies?

Options: `All/The R&Ws accurate at MAE standard`; `All/The R&Ws accurate in all respects (repeating R&Ws)`; `Each R&W accurate at MAE standard`; `R&Ws accurate at another materiality standard (e.g., hybrid standard)`

### `cc_covenant_compliance` (Conditions to Closing)

Closing condition on the Target's performance of covenants: is the materiality standard applied to the covenants collectively or to each covenant individually?

Options: `All Covenants`; `Each Covenant`; `Hybrid/Other Standard`

Note: "All Covenants" = the Target shall have performed in all material respects all covenants/obligations (collective); "Each Covenant" = each covenant/obligation shall have been performed in all material respects.

### `kn_definition` (Knowledge)

Target knowledge definition: actual knowledge only, or constructive knowledge (e.g., knowledge after reasonable inquiry, or that would reasonably be expected to be known)?

Options: `Actual knowledge`; `Constructive knowledge`

### `kn_identified_persons` (Knowledge)

Target knowledge definition: is knowledge limited to one or more identified persons (e.g., persons named or listed in a schedule)?

Options: `No`; `Yes`

### `mae_co_disclosure_schedules` (Material Adverse Effect)

MAE carve-out: matters disclosed in the Target's disclosure schedules (or disclosure letter)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_buyer_actions` (Material Adverse Effect)

MAE carve-out: actions taken by the Buyer or its affiliates (including breaches by the Buyer, or the identity of the Buyer)?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_co_stockholder_litigation` (Material Adverse Effect)

MAE carve-out: stockholder litigation/proceedings relating to the agreement or the transaction?

Options: `No`; `Yes`

Note: Answer "Yes" if the MAE definition (Target/Company MAE) excludes this category of events from what can constitute or be taken into account in determining an MAE.

### `mae_ability_subject_to_carveouts` (Material Adverse Effect)

Is the "ability to consummate" prong of the MAE definition subject to the MAE carve-outs?

Options: `No`; `Yes`

Note: Answer "No" if the definition has no ability-to-consummate prong, or if the carve-outs apply only to the business/financial-condition prong.

### `ef_antitrust_standard` (Operating and Efforts Covenant)

What general efforts standard applies to obtaining antitrust/regulatory approvals?

Options: `Commercially reasonable efforts`; `Flat standard`; `Reasonable best efforts`

Note: "Flat standard" = the covenant on obtaining antitrust/regulatory approvals is not qualified by "reasonable best efforts" or "commercially reasonable efforts" (e.g. the parties "shall take all actions necessary" to obtain the approvals, or use plain "best efforts"). If that covenant is qualified by reasonable best efforts or commercially reasonable efforts, choose that option, even if a separate clause (e.g. a divestiture / hell-or-high-water undertaking) is unqualified.

### `rem_specific_performance` (Remedies)

Specific performance: are the parties "entitled to" specific performance, or only "entitled to seek" it?

Options: `"entitled to seek" specific performance`; `"entitled to" specific performance`

## Merge (survey) questions

All questions refer to the 20 agreements A01–A20 and to their answers in your deal-point table; `dp` = «X» means the agreement's answer to that deal point is exactly the standard option X (guillemets delimit the option string); `dp` includes «X» means a multi-select answer contains option X.

- **M01**. Give the distribution of answers to `mae_co_disclosure_schedules` across all 20 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M02**. Give the distribution of answers to `mae_ability_subject_to_carveouts` across all 20 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M03**. How many of the 20 agreements satisfy ALL of the following: `cc_cap_bringdown_standard` = «Accurate in all respects with de minimis exception» AND `cc_covenant_compliance` = «All Covenants»? Answer with an integer.
- **M04**. How many of the 20 agreements satisfy ALL of the following: `mae_co_buyer_actions` = «No» AND `mae_ability_subject_to_carveouts` = «No»? Answer with an integer.
- **M05**. How many of the 20 agreements satisfy ALL of the following: `cc_fund_rw_types` includes «Opinion of Financial Advisor» AND `cc_general_bringdown_standard` = «All/The R&Ws accurate at MAE standard»? Answer with an integer.
- **M06**. List every agreement that satisfies: `cc_general_bringdown_timing` = «At Signing & At Closing» AND NOT (`cc_covenant_compliance` = «All Covenants»). If no agreement qualifies, answer with an empty list [].
- **M07**. List every agreement that satisfies: `cc_fund_bringdown_standard` = «Accurate at another materiality standard (e.g., hybrid standard)» AND NOT (`cc_scrape_applies_to` includes «Specified R&Ws only»). If no agreement qualifies, answer with an empty list [].
- **M08**. List every agreement that satisfies: `mae_co_disclosure_schedules` = «No» AND `mae_co_stockholder_litigation` = «No». If no agreement qualifies, answer with an empty list [].
- **M09**. Which agreement(s) have the highest value of the number of options selected for `cc_scrape_applies_to` (not counting 'No')? List all tied agreements.
- **M10**. For `rem_specific_performance`, list every agreement whose answer is shared by at most 3 of the 20 agreements (counting the agreement itself).
- **M11**. For `ef_antitrust_standard`, list every agreement whose answer is shared by at most 3 of the 20 agreements (counting the agreement itself).
- **M12**. Consider the deal points `cc_fund_rw_types`, `cc_fund_bringdown_standard`, `cc_cap_bringdown_standard`, `cc_scrape_applies_to`, `cc_general_bringdown_timing`, `cc_general_bringdown_standard`, `cc_covenant_compliance`, `kn_definition`, `kn_identified_persons`, `mae_co_disclosure_schedules`, `mae_co_buyer_actions`, `mae_co_stockholder_litigation`, `mae_ability_subject_to_carveouts`, `ef_antitrust_standard`, `rem_specific_performance`. For each of them, take the most common answer across the 20 agreements (complete answer; for each listed deal point the most common answer is unique). List every agreement whose answer differs from that most common answer on at least 8 of these deal points.
- **M13**. Considering only `cc_cap_bringdown_standard`, `cc_general_bringdown_timing`, `cc_general_bringdown_standard`: group together agreements whose answers are identical on every one of these deal points. Report every group with two or more agreements, as a list of lists of agreement ids (agreements with a unique combination are omitted).
- **M14**. Considering only `mae_co_buyer_actions`, `mae_co_stockholder_litigation`, `mae_ability_subject_to_carveouts`: how many distinct answer combinations occur among the 20 agreements? Answer with an integer.
- **M15**. Which other agreement(s) give the same answer as A05 on the largest number of the 15 deal points in the questionnaire? (A multi-select answer counts as the same only if the full set matches.) List all tied agreements.
