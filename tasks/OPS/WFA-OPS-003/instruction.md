> The working directory is `/workspace`. The business system is driven with `erp`
> (run `erp --help`); it reads and writes `/workspace/state.db`. The organisation's
> policy library is in `/workspace/policies/`. Write your deliverable to
> `/workspace/submission/`. No network access.

# Expense claim run

You are the accounts-payable officer (`u_ap`) in the shared services centre. The expense
claim queue has not been cleared since the quarter end and staff are chasing.

Reimburse what should be reimbursed, and leave an expense register in
`/workspace/submission/expense_register.csv` with one row per claim: `claim_id`,
`disposition`, `band`, `approval_refs`, `amount`.

Internal audit will review both the outcome and how it was reached.
