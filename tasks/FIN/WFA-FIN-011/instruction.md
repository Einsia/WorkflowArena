> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: the `output/` directory named in the task is this directory (`/workspace/output` is a symlink to it). Only the files in `/workspace/submission/` are graded.
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, lxml 5.3.0, beautifulsoup4 4.12.3.
>
> Codes in your CSV deliverables (`account`, `entity`, `counterparty`, `seller`, `buyer`, `responsible_entity`, `counterparty_entity`) are matched as text after trimming spaces and upper-casing, and an integer-valued number such as `1000.0` counts as `1000`; amounts are compared numerically.

# Halvard Group — consolidation as at 2026-12-31

You are the group reporting accountant of the Halvard Group (a US parent and six subsidiaries, two of them
reporting in EUR and JPY). Prepare the group consolidation **as at 2026-12-31 and for the year ended 31 December 2026**, applying the
group accounting policy manual (`inputs/policy_manual.md`) exactly. Work only from the files in `inputs/`; no
internet access is needed or allowed.

## Inputs (`inputs/`)
- `policy_manual.md` — the authoritative accounting rules (translation, eliminations, NCI, unrealized profit,
  designated loan, business combinations).
- `entities.csv`, `chart_of_accounts.csv`, `fx_rates.csv` (monthly average and closing rates, USD per unit).
- `opening_balances_2025-12-31.csv` — every entity's balances at 31 Dec 2025 (intercompany balances by
  counterparty and transaction currency).
- `ledgers/<entity>_gl.csv` — all journal lines posted by each entity from 1 Jan 2026 to 2026-12-31
  (debit/credit in the entity's functional currency; foreign-currency lines carry `txn_currency`/`txn_amount`).
- `inventory_lots_2025-12-31.csv`, `inventory_lots_2026-06-30.csv`, `inventory_lots_2026-12-31.csv` — inventory lot listings of all entities.
- `ic_price_list.csv` (intercompany markups and effective dates), `vendor_master.csv`, `fixed_asset_register.csv`.
- `prior_year_workpapers.json` — historical-rate equity and opening translated retained earnings / CTA of the
  foreign subsidiaries, cumulative FX on the designated loan, P's investment cost, opening consolidated TB.
- `acquisition.json`, `fair_value_schedule.csv` — the acquisition of S5 (acquired on 2026-07-01; S5's ledger covers the whole period, including the months before the acquisition).

## Deliverables (write to `output/`)
All amounts USD, signed trial-balance convention (debit positive, credit negative), two decimals, accounts
from `chart_of_accounts.csv`.
1. `entity_tb_usd.csv` — columns `entity,account,amount`: the trial balance of **each consolidated entity**
   at 2026-12-31 in USD before eliminations: income-statement accounts carry the activity of the consolidated period,
   balance-sheet accounts the closing balance, 3200 the opening retained earnings. Foreign subsidiaries are
   translated (their CTA in 3400). For S5 report only post-acquisition income-statement activity; its retained earnings at the acquisition date go in 3200.
   Each entity's rows must sum to zero.
2. `eliminations.csv` — columns `entry_id,account,amount` (optional `description`): every consolidation entry
   (eliminations, NCI, unrealized profit, fair-value adjustments, reclassifications). Each `entry_id` must
   balance.
3. `consolidated_tb.csv` — columns `account,amount`: the consolidated trial balance at 2026-12-31
   (= entity trial balances + consolidation entries).
4. `summary.json` — a JSON object with these keys (USD, two decimals; positive numbers on the natural side):
`consolidated_revenue` (external sales), `consolidated_net_income`, `net_income_attributable_to_nci`,
`net_income_attributable_to_parent`, `nci_closing_total`, `nci_closing_S2`, `nci_closing_S3`,
`cta_attributable_to_parent_closing` (credit balance of 3400 shown positive, debit balance negative),
`goodwill`, `total_assets`, `total_liabilities`, `total_equity` (including NCI, after closing the period's net income).

## Grading (programmatic)
Each amount is compared with the reference within USD 5.00. Hard checks: every consolidation entry balances,
each entity TB and the consolidated TB sum to zero, entity TBs + consolidation entries reproduce your
consolidated TB, and the summary totals agree with your consolidated TB (assets = liabilities + equity).
Full success requires all hard checks and every entity, consolidated and summary amount to be correct.
