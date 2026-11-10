> The working directory is `/workspace`. The business system is driven with `erp`
> (run `erp --help`); it reads and writes `/workspace/state.db`. The organisation's
> policy library is in `/workspace/policies/`. Write your deliverable to
> `/workspace/submission/`. No network access.

# Contract variations

You are the quantity surveyor (`u_qs`) in the estates team of a shared corporate services
centre. Variation orders have been accumulating against the live works contracts and the
contracts manager wants the file cleared before the next certification.

Deal with the variations, and leave a variation register in
`/workspace/submission/variation_register.csv` with one row per variation:
`variation_id`, `disposition`, `band`, `approval_refs`, `amount`.

Internal audit will review both the outcome and how it was reached.
