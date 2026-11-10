> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: the `output/` directory named in the task is this directory (`/workspace/output` is a symlink to it). Only the files in `/workspace/submission/` are graded.
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, lxml 5.3.0, beautifulsoup4 4.12.3.
>
> Codes in your CSV deliverables (`account`, `entity`, `counterparty`, `seller`, `buyer`, `responsible_entity`, `counterparty_entity`) are matched as text after trimming spaces and upper-casing, and an integer-valued number such as `1000.0` counts as `1000`; amounts are compared numerically.

# Halvard Group — Q2 2026 (April-June) close for S2, S3, S4 and S6

You are closing the books of S2, S3, S4 and S6 for Q2 2026 (April-June). Earlier months are closed and correct. The ledgers
as exported contain errors. Using the evidence provided and `inputs/policy_manual.md` (sections 2, 4, 9 in
particular), find every error, book correcting entries in the month to which each corrected transaction belongs,
and report the corrected month-end trial balances and group figures. Work only from `inputs/`.

## Inputs (`inputs/`)
- `policy_manual.md`, `entities.csv`, `chart_of_accounts.csv`, `fx_rates.csv`, `vendor_master.csv`, `ic_price_list.csv`.
- `opening_balances_2025-12-31.csv`, `ledgers/<entity>_gl.csv` (journal lines from 1 Jan 2026 to 2026-06-30, as booked).
- `bank_statements.csv` — bank statements for April, May and June 2026 (value dates; running balance).
- `documents.csv` — source documents (sales/purchase/expense/capex invoices, receipts) dated from the month before
  the close period to the month after it, with preparer/approver and service period.
- `ic_documents.csv` — intercompany documents; `fixed_asset_register.csv`, `inventory_lots_2026-06-30.csv` (lot listing per books) and `inventory_count_2026-06-30.csv` (physical count at 30 June).

## Deliverables (write to `output/`)
1. `adjustments.csv` — `entry_id,entity,date,account,counterparty,amount,txn_currency,txn_amount[,description]`:
   correcting entries (functional currency, debit positive; counterparty required on intercompany accounts;
   foreign-currency items of USD entities carry `txn_currency`/`txn_amount`). Each entry must balance. Do not touch
   income tax (8000, 2300) or equity (3000, 3100, 3200) accounts, and do not adjust timing differences.
2. `closing_tb.csv` — `entity,month,account,counterparty,amount`: corrected trial balance of each entity at each
   month-end of April, May and June 2026 (cumulative balances incl. year-to-date income statement; intercompany accounts
   additionally broken down by counterparty in extra rows with `counterparty` filled).
3. `findings.csv` — `entity,month,error_type,reference`: one row per erroneous, missing or duplicated posting, with
   `month` = the month of that posting (e.g. an asset left out of three monthly depreciation runs = three rows; a
   missing accrual together with its missing reversal = one row; follow-on corrections in later months, such as
   depreciation of a wrongly expensed asset or an FX true-up, add no rows). `reference` is free text (document or
   asset id). `error_type` ∈ {unrecorded_bank_fee, unrecorded_bank_interest, duplicate_invoice, transposition, misclassification, missing_accrual, accrual_not_reversed, missing_depreciation, missing_prepaid_amortization, missing_ic_entry, vat_error, sales_cutoff, capex_expensed, allowance_error, missing_count_adjustment, missing_fx_remeasurement, wrong_fx_rate}.
4. `summary.json` with keys: `combined_pretax_income_2026-04`, `combined_pretax_income_2026-05`, `combined_pretax_income_2026-06` (corrected pretax income of these entities for that month in USD, foreign entities translated at the month's average rate, each entity rounded to cents), `total_pretax_correction_usd` (corrected minus as-booked pretax income over the period, summed over entities in USD), `entity_with_largest_pretax_correction` (entity code, by absolute amount), `n_findings` (number of rows in findings.csv).

## Grading (programmatic)
Your adjustments are replayed on the as-booked ledgers; every balance that must change (or that you change) is
compared with the correct balance at every month-end (tolerance 5.00 in functional currency). Hard checks: balanced
entries, protected accounts untouched, no adjustment of bank timing differences, intercompany balances among these
entities agree after your corrections at every month-end, your `closing_tb.csv` equals the replayed balances.
Findings are scored by multiset F1 on (entity, month, error_type).
