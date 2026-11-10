> The working directory is `/workspace`. The business systems are driven with `sys`
> (run `sys --help`); it reads and writes `/workspace/state.db`, whose layout is in
> `/workspace/schema.sql`. The organisation's policy library is in `/workspace/policies/`.
> Write your deliverable to `/workspace/submission/`. No network access.

# Complaint inbox

You are the duty officer (`u_complaints`) in customer operations. The inbound complaints
register has not been worked since the last period and the service desk, the referral
register and the payments ledger all need to end up consistent with it.

Deal with the inbox, then leave a routing report at
`/workspace/submission/routing_report.csv` with one row per complaint —
`complaint_id`, `account_id`, `disposition`, `case_ref`, `queue`, `sla_due_step`,
`referral_scheme`, `compensation` — followed by a final row whose `complaint_id` is
`TOTAL`, carrying in `account_id` the number of complaints you took forward, in `case_ref`
the number of cases you opened, in `referral_scheme` the number of referrals you made and
in `compensation` the total goodwill you authorised.

Quality assurance samples this work and looks at both the end state and the route taken to
it.
