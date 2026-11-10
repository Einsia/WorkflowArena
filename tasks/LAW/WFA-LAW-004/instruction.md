> The working directory is `/workspace`. The task inputs are in `/workspace/inputs/` (the `inputs/` referred to below is this directory, e.g. `inputs/agreements/A01.txt` is `/workspace/inputs/agreements/A01.txt`), and the blank template is in `/workspace/templates/` (the `templates/` referred to below). "The files in this package" means the files under `/workspace/inputs/` and `/workspace/templates/`. Write your deliverables to `/workspace/submission/` instead of `outputs/`: `outputs/deal_points.csv` below means `/workspace/submission/deal_points.csv` and `outputs/answers.json` means `/workspace/submission/answers.json` (grading reads only `/workspace/submission/`).
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, statsmodels 0.14.4, matplotlib 3.9.2, h5py 3.12.1, lxml 5.3.0, beautifulsoup4 4.12.3.

# Merger agreement deal-points survey: No-shop, fiduciary exception and change of recommendation

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

### `dp_noshop_rep_liability` (Deal Protection and Related Provisions)

Does the agreement make the Target liable (e.g., deem it a breach by the Target) for no-shop violations by its Representatives?

Options: `No`; `Yes`

### `dp_noshop_rep_standard` (Deal Protection and Related Provisions)

What liability standard applies to the Target for no-shop violations by Representatives other than directors and officers?

Options: `Reasonable standard`; `Strict liability`

Note: "Strict liability" = any violation by such Representatives is deemed a breach by the Target; "Reasonable standard" = the Target is liable only if, e.g., it failed to use reasonable efforts to cause them to comply, or the Representative acted at the Target's direction.

### `dp_fidout_trigger` (Deal Protection and Related Provisions)

Fiduciary exception to the no-shop: what kind of third-party proposal permits the Target to engage (furnish information / negotiate)?

Options: `Acquisition Proposal only`; `Superior Offer, or Acquisition Proposal reasonably likely/expected to result in a Superior Offer`

### `dp_fidout_standard` (Deal Protection and Related Provisions)

Fiduciary exception to the no-shop: what fiduciary-duty standard must the board determine is met (regarding failure to engage)?

Options: `"Breach" of fiduciary duties`; `"Inconsistent" with fiduciary duties`; `"Reasonably likely/expected breach" of fiduciary duties`; `"Reasonably likely/expected to be inconsistent" with fiduciary duties`; `"Reasonably likely/expected violation" of fiduciary duties`; `"Required to comply" with fiduciary duties`; `"Violation" of fiduciary duties`; `More likely than not violate fiduciary duties`; `Other specified standard`

### `dp_cor_board_only` (Deal Protection and Related Provisions)

Is a change of recommendation permitted on the basis of a board fiduciary determination alone (i.e., not tied to a Superior Offer or an Intervening Event)?

Options: `No`; `Yes`

### `dp_cor_so_standard` (Deal Protection and Related Provisions)

Change of recommendation in response to a Superior Offer: what fiduciary-duty standard must the board determine is met?

Options: `"Breach" of fiduciary duties`; `"Inconsistent" with fiduciary duties`; `"Reasonably likely/expected breach" of fiduciary duties`; `"Reasonably likely/expected to be inconsistent" with fiduciary duties`; `"Reasonably likely/expected violation" of fiduciary duties`; `"Required to comply" with fiduciary duties`; `"Violation" of fiduciary duties`; `More likely than not violate fiduciary duties`; `Other specified standard`

### `dp_cor_ie_yn` (Deal Protection and Related Provisions)

Is a change of recommendation permitted in response to an Intervening Event?

Options: `No`; `Yes`

### `dp_cor_match_initial` (Deal Protection and Related Provisions)

Buyer's matching right before a change of recommendation: length of the initial matching (notice) period?

Options: `2 business days or less`; `3 business days`; `3 calendar days`; `4 business days`; `4 calendar days`; `5 business days`; `Greater than 5 business days`

### `dp_cor_match_additional` (Deal Protection and Related Provisions)

Buyer's matching right before a change of recommendation: length of the additional matching period after a material modification of the proposal?

Options: `2 business days or less`; `3 business days`; `3 days`; `4 business days`; `5 business days`; `> 5 business days`

### `dp_so_stock_threshold` (Deal Protection and Related Provisions)

Superior Offer definition: what percentage of the Target's stock must the proposal cover?

Options: `"All or substantially all"`; `50%`; `Greater than 50% but not "all or substantially all"`; `Less than 50%`

Note: "50%" = the definition refers to 50% (e.g., "more than 50%" or "a majority"); "Greater than 50% but not all or substantially all" = e.g., 75% or 80%.

### `dp_so_asset_threshold` (Deal Protection and Related Provisions)

Superior Offer definition: what percentage of the Target's assets must the proposal cover?

Options: `"All or substantially all"`; `50%`; `Greater than 50% but not "all or substantially all"`; `Less than 50%`

Note: Same scale as the stock-threshold question.

### `dp_so_fpov_sole` (Deal Protection and Related Provisions)

Superior Offer definition: is being more favorable "from a financial point of view" the sole stated basis for comparison (no other factors such as legal, regulatory, financing or timing aspects)?

Options: `No`; `Yes`

### `kn_definition` (Knowledge)

Target knowledge definition: actual knowledge only, or constructive knowledge (e.g., knowledge after reasonable inquiry, or that would reasonably be expected to be known)?

Options: `Actual knowledge`; `Constructive knowledge`

### `kn_identified_persons` (Knowledge)

Target knowledge definition: is knowledge limited to one or more identified persons (e.g., persons named or listed in a schedule)?

Options: `No`; `Yes`

### `rem_specific_performance` (Remedies)

Specific performance: are the parties "entitled to" specific performance, or only "entitled to seek" it?

Options: `"entitled to seek" specific performance`; `"entitled to" specific performance`

### `gen_consideration` (General Information)

Type of merger consideration paid to Target stockholders?

Options: `All Cash`; `All Stock`; `Mixed Cash/Stock`; `Mixed Cash/Stock: Election`

## Merge (survey) questions

All questions refer to the 15 agreements A01–A15 and to their answers in your deal-point table; `dp` = «X» means the agreement's answer to that deal point is exactly the standard option X (guillemets delimit the option string); `dp` includes «X» means a multi-select answer contains option X.

- **M01**. Give the distribution of answers to `kn_definition` across all 15 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M02**. Give the distribution of answers to `dp_cor_match_additional` across all 15 agreements as an object mapping every standard option of that deal point (include options with count 0) to the number of agreements (each agreement counts once).
- **M03**. How many of the 15 agreements satisfy ALL of the following: `dp_cor_ie_yn` = «Yes» AND `dp_cor_match_initial` = «4 business days»? Answer with an integer.
- **M04**. How many of the 15 agreements satisfy ALL of the following: `dp_noshop_rep_liability` = «Yes» AND NOT (`dp_cor_match_additional` = «3 business days»)? Answer with an integer.
- **M05**. How many of the 15 agreements satisfy ALL of the following: `dp_so_stock_threshold` = «Greater than 50% but not "all or substantially all"» AND NOT (`dp_so_asset_threshold` = «50%»)? Answer with an integer.
- **M06**. List every agreement that satisfies: `dp_noshop_rep_standard` = «Strict liability» AND NOT (`dp_fidout_standard` = «"Inconsistent" with fiduciary duties»). If no agreement qualifies, answer with an empty list [].
- **M07**. List every agreement that satisfies: `dp_cor_so_standard` = «"Inconsistent" with fiduciary duties» AND NOT (`dp_cor_match_initial` = «3 business days»). If no agreement qualifies, answer with an empty list [].
- **M08**. List every agreement that satisfies: `dp_cor_so_standard` = «"Reasonably likely/expected to be inconsistent" with fiduciary duties» AND `dp_so_fpov_sole` = «Yes». If no agreement qualifies, answer with an empty list [].
- **M09**. List every agreement that satisfies: `dp_noshop_rep_standard` = «Reasonable standard» AND `dp_cor_match_initial` = «5 business days». If no agreement qualifies, answer with an empty list [].
- **M10**. List every agreement that satisfies: NOT (`dp_so_stock_threshold` gives the same answer as `dp_so_asset_threshold`). If no agreement qualifies, answer with an empty list [].
- **M11**. For `gen_consideration`, list every agreement whose answer is shared by at most 2 of the 15 agreements (counting the agreement itself).
- **M12**. For `kn_identified_persons`, list every agreement whose answer is shared by at most 1 of the 15 agreements (counting the agreement itself).
- **M13**. Consider the deal points `dp_noshop_rep_liability`, `dp_noshop_rep_standard`, `dp_fidout_standard`, `dp_cor_ie_yn`, `dp_cor_match_initial`, `dp_cor_match_additional`, `dp_so_stock_threshold`, `dp_so_asset_threshold`, `dp_so_fpov_sole`, `kn_definition`, `kn_identified_persons`, `rem_specific_performance`, `gen_consideration`. For each of them, take the most common answer across the 15 agreements (complete answer; for each listed deal point the most common answer is unique). List every agreement whose answer differs from that most common answer on at least 6 of these deal points.
- **M14**. Considering only `dp_fidout_standard`, `dp_cor_board_only`, `dp_cor_ie_yn`: group together agreements whose answers are identical on every one of these deal points. Report every group with two or more agreements, as a list of lists of agreement ids (agreements with a unique combination are omitted).
- **M15**. Considering only `dp_fidout_trigger`, `dp_so_asset_threshold`, `dp_so_fpov_sole`: how many distinct answer combinations occur among the 15 agreements? Answer with an integer.
- **M16**. Which other agreement(s) give the same answer as A15 on the largest number of the 16 deal points in the questionnaire? (A multi-select answer counts as the same only if the full set matches.) List all tied agreements.
