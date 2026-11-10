> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: the `output/` directory named in the task is this directory (`/workspace/output` is a symlink to it). Only the files in `/workspace/submission/` are graded.
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, lxml 5.3.0, beautifulsoup4 4.12.3.
>
> Codes in your CSV deliverables (`account`, `entity`, `counterparty`, `seller`, `buyer`, `responsible_entity`, `counterparty_entity`) are matched as text after trimming spaces and upper-casing, and an integer-valued number such as `1000.0` counts as `1000`; amounts are compared numerically.

# Halvard Group — FY2026 audit: transaction testing of all seven entities

As the group auditor, test the 2026 transactions of all seven entities against their source documents, the price
list, the vendor master and the group policy manual (`inputs/policy_manual.md`, especially sections 2, 4, 9.4, 9.5).
Identify every exception, state the expected (correct) value, quantify the effect on each entity's pretax income,
and summarize for the group. Work only from `inputs/`.

## Inputs (`inputs/`)
- `policy_manual.md`, `entities.csv`, `chart_of_accounts.csv`, `fx_rates.csv`, `vendor_master.csv`, `price_list.csv`,
  `ic_price_list.csv`, `materiality.csv` (performance materiality per entity, USD).
- `documents.csv` — the document register of 2026 (sales/purchase/expense/capex invoices, receipts, intercompany
  documents) with quantities, unit prices, net/tax/gross amounts, service period, preparer and approver.
- `ledgers/<entity>_gl.csv` — the 2026 general ledgers as posted (`doc_ref` links postings to documents);
  `opening_balances_2025-12-31.csv`, `fixed_asset_register.csv`.

## Deliverables (write to `output/`)
1. `findings.csv` — `entity,doc_id,error_type,field,recorded_value,expected_value`: one row per exception (entity = the
   entity whose record is wrong). `error_type` ∈ {posting_amount_mismatch, extension_error, tax_calc_error, price_anomaly, duplicate_posting, cutoff_error, misclassification, missing_approval, sod_violation, fx_rate_error, ic_counterparty_error, unrecorded_document}. `expected_value`: for posting_amount_mismatch the
   correct ledger amount; for extension_error the correct net amount; for tax_calc_error the correct tax; for
   price_anomaly the list price; for fx_rate_error the correct functional-currency amount; for misclassification the
   correct account; for cutoff_error the correct posting date (document date); for ic_counterparty_error the correct
   account; otherwise free text. Amounts as plain numbers with two decimals.
   Label rules: `price_anomaly` = a sales invoice whose unit price differs from the monthly list price without a noted
   approved discount (report only `price_anomaly` for such a document, even if its net then differs from quantity x unit
   price); `extension_error` = a document whose unit price is correct but whose net differs from quantity x unit price by more
   than rounding (differences under 1.00 from a unit price rounded to 4 decimals are not exceptions);
   `cutoff_error` = a posting dated in a different month from the document date (the second posting of a duplicated
   document is reported only as `duplicate_posting`). S5's sales invoices to customer `C-HALV` (Halvard, before S5 joined
   the group) are not tested against the list price.
2. `entity_impact.csv` — `entity,pretax_misstatement_local,pretax_misstatement_usd`: for every entity, pretax income
   (excluding income tax expense) as posted minus pretax income after correcting all exceptions, for the year 2026
   (USD: each month's local amount at that month's average rate).
3. `summary.json` with keys: `n_findings_<error_type>` for each of the 12 types, `total_findings`,
   `total_pretax_misstatement_usd` (sum over entities), `entities_above_materiality` (sorted list of entity codes whose
   absolute USD misstatement exceeds their performance materiality), `entity_with_most_findings` (ties broken
   alphabetically).

## Grading (programmatic)
Findings are matched on (entity, doc_id, error_type) and checked for the expected value (amounts within 5.00);
unmatched submitted rows count as false positives. Full success requires every finding with no extras, every entity
impact and every summary value to be correct.
