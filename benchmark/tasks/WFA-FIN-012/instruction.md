> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: the `output/` directory named in the task is this directory (`/workspace/output` is a symlink to it). Only the files in `/workspace/submission/` are graded.
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, lxml 5.3.0, beautifulsoup4 4.12.3.
>
> Codes in your CSV deliverables (`account`, `entity`, `counterparty`, `seller`, `buyer`, `responsible_entity`, `counterparty_entity`) are matched as text after trimming spaces and upper-casing, and an integer-valued number such as `1000.0` counts as `1000`; amounts are compared numerically.

# Halvard Group — foreign-currency remeasurement, translation and CTA for FY2026

The 2026 ledgers of the US-dollar entities were exported **before** the month-end foreign-currency remeasurement
runs were posted (policy 2.2), and the two foreign subsidiaries (S3, EUR; S4, JPY) still have to be translated.
Following `inputs/policy_manual.md` (sections 2, 5, 6.3, 6.5, 6.7), compute the missing remeasurements, translate
S3 and S4, roll forward the cumulative translation adjustment and determine the group's FX figures for 2026.
Work only from `inputs/`.

## Inputs (`inputs/`)
- `policy_manual.md`, `entities.csv`, `chart_of_accounts.csv`, `fx_rates.csv`, `vendor_master.csv`.
- `opening_balances_2025-12-31.csv` (foreign-currency balances with `txn_currency`/`txn_amount`).
- `ledgers/<entity>_gl.csv` — 2026 journal lines; the USD entities' files contain **no** month-end
  remeasurement entries.
- `prior_year_workpapers.json` (historical-rate equity, opening translated RE and CTA, designated-loan history,
  opening consolidated TB), `acquisition.json`, `fair_value_schedule.csv`, `fixed_asset_register.csv`.

## Deliverables (write to `output/`)
1. `remeasurement.csv` — `entity,month,account,counterparty,currency,amount_usd`: for P, S1, S2 and S6, every
   month-end remeasurement line (one row per entity, month and foreign-currency balance that changes; the offset
   to 7200 is implied, do not list it). Signed, debit positive.
2. `translated_tb.csv` — `entity,account,amount_usd`: the translated trial balances of S3 and S4 at 31 Dec 2026
   (income statement for the year, balance sheet at year end, CTA in 3400).
3. `cta_rollforward.csv` — `entity,cta_opening,translation_adjustment,cta_closing,nci_share_closing,parent_share_closing`
   for S3 and S4 (USD; **credit balances shown positive**, i.e. a translation gain is positive).
4. `ic_balances_usd.csv` — `entity,counterparty,account,amount_usd`: every intercompany balance denominated in EUR
   or JPY at 31 Dec 2026, from both sides (USD entities after remeasurement, S3/S4 translated), signed.
5. `summary.json` with keys (USD; P&L amounts debit-positive = loss, OCI/CTA amounts credit-positive = gain):
   `fx_7200_P`, `fx_7200_S1`, `fx_7200_S2`, `fx_7200_S6` (each entity's 2026 total in 7200 after remeasurement),
   `consolidated_fx_7200` (7200 in the consolidated income statement), `designated_loan_fx_reclassified_current_year`
   (amount moved out of profit or loss, gain positive), `oci_translation_parent_current_year`,
   `oci_translation_nci_current_year`, `cta_attributable_to_parent_closing`.

## Grading (programmatic)
Amounts within USD 5.00. Hard check: your intercompany USD balances must agree pairwise. Full success requires all
rows and summary values to be correct.
