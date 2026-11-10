> The working directory is `/workspace`. The business systems are driven with `sys`
> (run `sys --help`); it reads and writes `/workspace/state.db`, whose layout is in
> `/workspace/schema.sql`. The organisation's policy library is in `/workspace/policies/`.
> Write your deliverable to `/workspace/submission/`. No network access.

# New starter provisioning

You are the HR operations officer (`u_hrops`) at a shared corporate services centre.
Six new starters are sitting in the joiner register and nothing has been set up for any of them.

Get each of them set up across the HR, payroll, access and asset systems, and leave an
onboarding report at `/workspace/submission/onboarding_report.csv` with one row per joiner:
`joiner_id`, `hr_status`, `payroll`, `access_systems`, `asset_class`, `hold_reason`.

Internal audit will review both the end state of the systems and how it was reached.
