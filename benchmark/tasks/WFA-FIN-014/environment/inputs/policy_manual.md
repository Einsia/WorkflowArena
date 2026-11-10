# Halvard Group — Group Accounting Policy Manual (FY2026 edition)

This manual is the only authoritative source for how the Halvard Group keeps its books, closes its
months and prepares consolidated financial statements. It simplifies US GAAP (ASC 810 consolidation,
ASC 830 foreign currency, ASC 805 business combinations) so that every number has exactly one correct
value. Where this manual differs from US GAAP, **this manual prevails**.

Conventions used in every file of the group:

* Amounts are signed: **debit positive, credit negative**, two decimals, in the stated currency.
* A trial balance (TB) lists, per account, the signed balance. A balanced TB sums to zero.
* Rates are quoted as **USD per one unit of foreign currency** (EUR, JPY).
* Fiscal year = calendar year 2026. Month-end = last calendar day of the month.
* Entity codes: `P`, `S1` … `S6` (see `entities.csv`). External counterparties use codes such as
  `C-…` (customers), `V-…` (vendors), `BANK`, `TAX-AUTH`, `PAYROLL`, `LANDLORD`, `NCI-S2`, `SHAREHOLDERS`.

---------------------------------------------------------------------------------------------------

## 1. Group structure

| Entity | Functional currency | Group ownership | Notes |
|---|---|---|---|
| P  | USD | parent | holding company, also a wholesaler |
| S1 | USD | 100% | manufacturer, main internal supplier |
| S2 | USD | 80%  | distributor; 20% held by an outside investor (`NCI-S2`) |
| S3 | EUR | 70%  | European distributor; 30% held by an outside investor (`NCI-S3`) |
| S4 | JPY | 100% | Japanese manufacturer/distributor |
| S5 | USD | acquired during 2026 (see `acquisition.json` where provided) | before the acquisition date S5 is an unrelated third party |
| S6 | USD | 100% | group treasury (intercompany lender) and shared services |

S1, S2, S3, S4 and S6 were **formed** by the group (no goodwill arose). P carries its investments in
subsidiaries (account 1500) at cost. Outside investors in S2 and S3 contributed share capital in
proportion to their holdings.

## 2. Bookkeeping conventions in entity ledgers

2.1 **Foreign-currency transactions.** A USD entity records any transaction denominated in EUR or JPY
at the **average rate of the month in which the transaction occurs** (the monthly average in
`fx_rates.csv`). The ledger line keeps the original currency and amount (`txn_currency`, `txn_amount`).
Foreign-currency cash is converted to USD on receipt/payment; USD entities hold no foreign-currency cash.

2.2 **Month-end remeasurement.** At every month-end each USD entity remeasures its foreign-currency
monetary balances (accounts 1200, 1250, 1260, 1270, 2100, 2150, 2160, 2250) **per account and
counterparty**: target USD = (cumulative `txn_amount` balance) × closing rate of the month, rounded to
cents; the difference to the carrying USD amount is posted to that account with the offset in 7200
Foreign exchange (gain) loss. Remeasurement lines carry the currency code and a `txn_amount` of 0.

2.3 **Intercompany invoicing currency.** Intercompany invoices, fees, loans, interest and dividends
involving S3 or S4 are denominated in that subsidiary's currency (EUR or JPY). All other
intercompany items are in USD.

2.4 Intercompany accounts must always carry the counterparty entity code. Trade items and management
fees use 1200/2100; loans 1250/2150; loan interest 1260/2160; dividends 1270 (receiver) / 2250 (payer).

## 3. Inventory and intercompany pricing

3.1 Inventory is held in lots and expensed **FIFO** (oldest lot first) at the lot's carrying amount.
Items of class `SPR` (service spare kits held for warranty) are not sold and stay in inventory.

3.2 Intercompany sales are priced at the seller's FIFO cost plus the markup in `ic_price_list.csv`
that is in force on the invoice date. When the invoice currency differs from the seller's currency,
the seller's cost is converted at the month's average rate.

3.3 A buyer may write a lot down to net realizable value (debit 5000, credit 1300). The cumulative
write-down per lot is shown in the lot listing (`nrv_writedown`).

## 4. Fixed assets, receivables, accruals, taxes

4.1 Straight-line depreciation, no residual value: monthly charge = cost ÷ useful life (months),
rounded to cents. Depreciation starts in the month **after** the in-service month; no depreciation is
charged in the month of disposal. Land is not depreciated.

4.2 Allowance for doubtful accounts is set quarterly (March, June, September, December month-end) to
the sum over open invoices of open amount × rate, each product rounded to cents, where days past due
are measured from invoice date + 30 days: not yet due 1%; 1–30 days 3%; 31–90 days 10%; over 90 days
40%. Before setting the allowance, invoices older than 150 days that are not expected to be collected
are written off against the allowance.

4.3 Services received in a month but invoiced after month-end are accrued at month-end (debit the
expense, credit 2200) and the accrual is reversed on the first day of the following month; the vendor
invoice is then booked normally. Annual bonuses are accrued monthly in 2200 and paid in March of the
following year. Prepaid insurance is amortized evenly over the 12 months of the year (December takes
the rounding remainder).

4.4 Sales tax / VAT is charged on external sales only (rates: P 7%, S1 6%, S2 8%, S3 19%, S4 10%,
S5 6.5%, S6 none; sales to resellers holding a resale certificate are exempt) and remitted on the 20th
of the following month. Intercompany sales carry no sales tax.

4.5 Income tax expense is provided monthly by each entity on its own pretax income excluding dividend
income from affiliates (4400), at its statutory rate (US entities 25%, S3 30%, S4 31%). Income tax
amounts are **never adjusted in consolidation, in reconciliations or in close corrections**; no
deferred taxes are recognized on any adjustment.

## 5. Translation of foreign subsidiaries (S3 EUR, S4 JPY)

5.1 Balance-sheet accounts other than equity: closing local balance of the account × closing rate of
the reporting month, rounded to cents (translate at **account** level).

5.2 Income-statement accounts: **each month's** activity per account × that month's average rate,
rounded to cents, summed over the months of the reporting period. Dividends declared (3300) are
translated the same way (average rate of the month of declaration).

5.3 Common stock and APIC at historical rates; opening retained earnings at the translated amount
carried forward from the prior-year consolidation (both given in `prior_year_workpapers.json`).

5.4 The cumulative translation adjustment (CTA, account 3400) of the subsidiary is the balancing figure
of its translated trial balance. The current-period translation adjustment = closing CTA − opening CTA.

## 6. Consolidation (full consolidation of all controlled entities)

6.1 **Scope and timing.** P and all subsidiaries are consolidated. An acquired subsidiary is
consolidated from its acquisition date only: its income-statement activity before that date is
excluded and becomes part of acquired equity (section 8).

6.2 **Investment elimination (formed subsidiaries).** Eliminate P's investment (1500) against the
subsidiary's common stock and APIC (USD historical amounts). The NCI share of common stock and APIC is
credited to 3500.

6.3 **Non-controlling interests (NCI)** are measured at their proportionate share of the subsidiary's
translated net assets, adjusted for unrealized profit on the subsidiary's own sales (6.6). Components:
NCI share of opening retained earnings (debit 3200, credit 3500); NCI share of opening CTA (debit
3400, credit 3500); NCI share of current-period profit (debit 3550, credit 3500); NCI share of the
current-period translation adjustment (debit/credit 3400 against 3500); NCI share of dividends
declared (debit 3500, credit 3300). Each component is computed and rounded to cents separately.
Account 3550 therefore shows the profit attributable to NCI; 3400 in the consolidated TB shows the
CTA attributable to the parent; 3500 shows the closing NCI.

6.4 **NCI share of profit** = NCI% × (subsidiary's translated net income for the consolidated period
− unrealized profit in closing group inventory on goods sold by that subsidiary + unrealized profit in
opening group inventory on goods sold by that subsidiary [+ for an acquired subsidiary with NCI, the
post-acquisition fair-value adjustments of section 8.5]).

6.5 **Intercompany balances and transactions** between consolidated entities are eliminated in full:
1200/2100, 1250/2150, 1260/2160, 1270/2250 (the part of 2250 owed to P only), 4100 against 5000,
4200/6600, 4300/7100, and 4400 against 3300 (P's share; the NCI share of dividends reduces 3500).
Any residual difference between the two sides of a balance or income/expense pair (rounding only, a
few cents) is taken to 7200.

6.6 **Unrealized profit (UP) in inventory.** For every intercompany lot still held by a group buyer
at the reporting date (including `SPR` lots): UP (buyer currency) = carrying amount − seller's cost,
where seller's cost = (carrying amount + cumulative NRV write-down) ÷ (1 + markup applicable to that
lot), rounded to cents; UP is floored at zero. For a foreign buyer UP is translated at the closing rate
of the reporting date. Eliminate: debit 5000, credit 1300. Lots bought from S5 **before** its
acquisition date are third-party purchases (no UP). Profit in group inventory at the start of the year
(opening UP) is computed the same way on the opening lots (translated at the 31 Dec 2025 closing rate)
and is fully realized during the year: debit 3200 (parent share) and 3500 (NCI share, if the seller has
NCI), credit 5000.

6.7 **Designated long-term intercompany loan.** The EUR loan from S6 to S3 is designated as part of the
group's net investment in S3 (settlement neither planned nor likely). The exchange difference that S6
recognizes on the **principal** (1250, counterparty S3) is reclassified in consolidation from 7200 to
3400 (entirely attributable to the parent). The cumulative amount recognized in S6's profit or loss in
prior years (given in the workpapers) is reclassified from 3200 to 3400 at the start of each year.

6.8 Consolidated trial balance = sum of the entity trial balances (translated where needed; for an
acquired subsidiary only post-acquisition income-statement activity, with pre-acquisition results
inside 3200) + all elimination / consolidation entries. Consolidated net income = −(sum of revenue and
expense accounts); profit attributable to the parent = consolidated net income − 3550.

## 7. Cash flow statement (direct method)

7.1 Group cash = account 1000 of consolidated entities. Cash flows between consolidated entities are
eliminated. An acquired subsidiary's cash flows are included from the acquisition date only.

7.2 Every external cash movement is classified by the nature of the transaction:

| Line | Classification rule |
|---|---|
| Receipts from customers | collections of trade receivables (1100) |
| Payments to suppliers and for operating expenses | payments of trade payables (2000) other than for capital expenditure; cash expenses (6xxx paid directly incl. rent, insurance premiums, bank charges) |
| Payments to employees | payroll and bonus payments |
| Sales taxes and VAT remitted | settlements of 2350 |
| Income taxes paid | settlements of 2300 |
| Interest paid | bank interest (7000) |
| Interest received | bank interest income (4310) |
| Purchases of property, plant and equipment | payments of trade payables to vendors of category `capex` |
| Proceeds from disposal of equipment | disposal proceeds |
| Acquisition of subsidiary, net of cash acquired | cash consideration paid less the acquiree's cash at the acquisition date |
| Proceeds from bank borrowings / Repayments of bank borrowings | movements of 2400 |
| Dividends paid to owners of the parent | P's dividend payments |
| Dividends paid to non-controlling interests | dividend payments by subsidiaries to `NCI-…` holders |

7.3 Foreign subsidiaries' cash flows are translated per month at the monthly average rate (each
line's monthly local total × average rate, rounded to cents). The effect of exchange-rate changes on
cash = closing group cash − opening group cash − net cash flow of the period.

## 8. Business combinations (S5)

8.1 The acquisition date is the first day of a month; the acquired balance sheet is S5's balance sheet
at the close of the previous day.

8.2 Consideration = cash paid + acquisition-date fair value of contingent consideration. Transaction
costs are expensed by P when incurred. Later changes in the fair value of contingent consideration go
to 4600 (booked by P).

8.3 Identifiable assets are measured at fair value (`fair_value_schedule.csv`); all other assets and
liabilities of S5 are at carrying amount. Step-up = fair value − carrying amount at the acquisition
date (for an individual fixed asset: cost − accumulated depreciation at the acquisition date; for
inventory: the carrying amount of all lots on hand). No deferred taxes are recognized.

8.4 Goodwill = consideration + fair value of NCI (if any, given in `acquisition.json`) − (carrying
amount of S5's net assets + total step-ups). In consolidation: debit S5's common stock, APIC and
retained earnings at the acquisition date, debit step-ups (to the asset's cost account 1300 / 1600 /
1610 / 1620; acquired intangibles to 1700), debit goodwill (1800), credit P's investment (1500), credit
NCI at fair value (3500, if any). S5's historical cost and accumulated depreciation are carried forward;
step-ups are added on top.

8.5 Subsequent measurement in consolidation: each fixed-asset or intangible step-up is depreciated or
amortized straight-line over the remaining life in the schedule; monthly charge = step-up ÷ remaining
life (months), rounded to cents, charged for every month from the acquisition month to the reporting
month (to 6400/1650 and 6500/1750; land is not depreciated); in the month in which a step-up becomes fully
depreciated or amortized the charge is the remaining balance, so that it is written off exactly. The inventory step-up is released to 5000
in proportion to the acquisition-date carrying amount of the acquired lots that has since been sold:
release = step-up × (1 − carrying amount still on hand of acquisition-date lots ÷ their carrying amount
at acquisition), rounded to cents.

## 9. Close, reconciliation and correction rules

9.1 Errors are corrected in the month to which the transaction belongs, in the ledger of the entity
whose records depart from the source document. Corrections of foreign-currency items in USD entities
follow 2.1 and 2.2 (record at the month's average rate, then remeasure at that month-end). Income tax
accounts are never adjusted (4.5).

Corrections of intercompany purchases are booked against inventory (1300) when the goods are still on hand
at period end (see the lot listing).

9.2 Intercompany reconciliation (period-end): the issuer's document (invoice, credit note, fee note,
interest note, dividend resolution, payment advice) in `ic_documents.csv` is authoritative. Goods are
shipped FOB shipping point: the buyer recognizes intercompany goods on the seller's invoice date
(goods in transit at period end are recorded by the buyer as inventory). Intercompany payments are
recognized by the receiving entity on the payer's payment date (cash in transit at period end is
recorded by the receiver as cash). Documents dated after the period end are not recorded in the period.

9.3 Bank reconciliation: deposits in transit and outstanding payments recorded in the ledger but
clearing the bank after month-end are timing differences and are **not** adjusted.

9.4 Purchase and expense documents at or above the approval threshold (USD 25,000; EUR 22,000;
JPY 3,500,000 net) require an approver; the approver must differ from the preparer. Sales prices must
equal the monthly list price (`price_list.csv`) unless the document notes an approved discount.

9.5 Expense coding follows the vendor master category: inventory → 1300, utilities → 6200, marketing
→ 6300, professional → 6700, other → 6900 (insurance premiums → 1400), capex → 1620.
