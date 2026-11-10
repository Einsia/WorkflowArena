> The working directory is `/workspace`. Input files are in `/workspace/inputs/` (the `inputs/` referred to in the task is this directory). Write your deliverables to `/workspace/submission/`: the `output/` directory named in the task is this directory (`/workspace/output` is a symlink to it). Only the files in `/workspace/submission/` are graded.
>
> No network access at runtime. Installed software: Python 3.12 with numpy 2.1.3, scipy 1.14.1, pandas 2.2.3, openpyxl 3.1.5, xlrd 2.0.1, lxml 5.3.0, beautifulsoup4 4.12.3.
>
> Codes in your CSV deliverables (`account`, `entity`, `counterparty`, `seller`, `buyer`, `responsible_entity`, `counterparty_entity`) are matched as text after trimming spaces and upper-casing, and an integer-valued number such as `1000.0` counts as `1000`; amounts are compared numerically.

# Halvard Group — acquisition of Corvex Instruments (S5): purchase price allocation and post-acquisition accounting

On 2026-09-01 P acquired 80% of Corvex Instruments Inc. (S5). Prepare the acquisition accounting for the FY2026 group
financial statements following `inputs/policy_manual.md` (sections 6 and 8): the acquired net assets, the purchase
price allocation, goodwill, non-controlling interest, the post-acquisition fair-value adjustments through
31 December 2026, and S5's contribution to the consolidated result. Work only from `inputs/`.

## Inputs (`inputs/`)
- `policy_manual.md`, `entities.csv`, `chart_of_accounts.csv`, `fx_rates.csv`, `ic_price_list.csv`, `vendor_master.csv`.
- `acquisition.json` (consideration, NCI fair value), `fair_value_schedule.csv` (fair values and remaining lives).
- `opening_balances_2025-12-31.csv`, `ledgers/<entity>_gl.csv` (all of 2026; S5's ledger includes its pre-acquisition months).
- `fixed_asset_register.csv` (all entities, incl. 2026 additions), `inventory_lots_<date>.csv` (lot listings of all entities on
  the day before the acquisition and at 31 Dec 2026).
- `prior_year_workpapers.json`.

## Deliverables (write to `output/`)
1. `acquired_net_assets.csv` — `account,carrying_amount`: S5's balance sheet at the acquisition date (all balance-sheet
   accounts incl. equity; retained earnings include the pre-acquisition result), signed TB convention.
2. `ppa.csv` — `item,asset_id,carrying_amount,fair_value,step_up`: one row per line of `fair_value_schedule.csv`
   (use the same `item`/`asset_id` values; intangibles have carrying amount 0).
3. `ppa_subsequent.csv` — `item,asset_id,charge_to_date,unamortized_step_up_closing`: for every step-up, the
   depreciation / amortization / inventory release recognized in consolidation from the acquisition date to
   31 Dec 2026 and the remaining step-up at 31 Dec 2026 (land: charge 0).
4. `summary.json` with keys (USD, positive numbers):
   `consideration`, `fair_value_identifiable_net_assets`, `goodwill`, `nci_at_acquisition`,
   `s5_post_acquisition_net_income_own_books`, `ppa_charges_to_date` (total of deliverable 3 charges),
   `up_closing_on_s5_sales` (unrealized profit at year end in group inventory bought from S5),
   `s5_adjusted_post_acquisition_profit` (own-books profit − PPA charges − closing UP on S5's sales),
   `nci_share_of_profit_S5`, `nci_closing_S5`, `contingent_consideration_liability_closing`,
   `change_in_fv_contingent_consideration` (loss positive, gain negative), `acquisition_costs_expensed`,
   `ic_sales_with_s5_eliminated` (sales between S5 and other group entities after the acquisition, both directions),
   `ic_balances_with_s5_eliminated` (sum of S5's intercompany receivables and payables at year end, absolute amounts),
   `sales_s5_to_p_before_acquisition` (third-party sales by S5 to P before the acquisition date, not eliminated).

## Grading (programmatic)
Amounts within USD 5.00. Full success requires every row and summary value to be correct.
