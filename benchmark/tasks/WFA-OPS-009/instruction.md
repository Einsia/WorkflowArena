> The working directory is `/workspace`. The business systems are driven with `sys`
> (run `sys --help`); it reads and writes `/workspace/state.db`, and `sys show <table>`
> lists any table. The organisation's policy library is in `/workspace/policies/`.
> Write your deliverable to `/workspace/submission/`. No network access.

# This period's leaver recovery

You are the IT and HR operations officer (`u_itops`) at a shared corporate services centre.
The leaver register has not been worked since the last audit and the recovery queue is
sitting untouched.

Settle the register, and leave a recovery report at
`/workspace/submission/offboarding_report.csv` with one row per person —
`person_id`, `access_action`, `payroll_action`, `assets_returned`, `handover_ref`,
`hold_reason` — plus a final `TOTAL` row reconciling the exercise.

Internal audit will review both the outcome and how it was reached.
