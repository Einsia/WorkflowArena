> The working directory is `/workspace`. The business system is driven with `erp`
> (run `erp --help`); it reads and writes `/workspace/state.db`. The organisation's
> policy library is in `/workspace/policies/`. Write your deliverable to
> `/workspace/submission/`. No network access.

# Grant instalment run

You are the grants officer (`u_gm`) at a funding body that administers education
programmes. The instalment queue has not been worked since the funder confirmed this
year's allocation, and grantees are asking when their money arrives.

Disburse what should be disbursed, and leave a disbursement register in
`/workspace/submission/disbursement_register.csv` with one row per instalment:
`instalment_id`, `disposition`, `band`, `approval_refs`, `amount`.

Internal audit and the funder's assurance team will review both the outcome and how it was
reached.
