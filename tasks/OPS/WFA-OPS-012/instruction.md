> The working directory is `/workspace`. The records systems are driven with `sys`
> (run `sys --help`); it reads and writes `/workspace/state.db`, and the table layout is in
> `/workspace/schema.sql`. The organisation's policy library is in `/workspace/policies/`.
> Write your deliverable to `/workspace/submission/`. No network access.

# Information rights desk

You are the information rights officer (`u_inforights`) at a shared services body. Six data
subject requests are sitting in the inbox and the response clock is running.

Deal with each one and close it off in the case system, then leave a log in
`/workspace/submission/dsar_log.csv` with one row per request — `request_id`,
`disposition`, `identity_outcome`, `records_considered`, `records_released`,
`records_withheld`, `withhold_grounds` — followed by a final `TOTAL` row carrying the
three record counts added up across the whole batch.

The regulator can ask us to account for both what we disclosed and how we arrived at it.
