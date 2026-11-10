# Master data governance
The supplier master is the organisation's record of who it trades with. The data
governance team owns its structure; operational teams own the records.

Statuses in use: `pending` (opened, not yet tradeable), `active` (tradeable), `suspended`
(a decision has stopped trading, the record remains), `lapsed` (dormant through inactivity,
the record remains).

Records are not deleted. A record that has lapsed is retained so that historical spend
remains attributable, and is the record reactivated if the counterparty returns. Opening a
duplicate record for an existing counterparty is a reportable data quality incident, and
is corrected by merging to the earlier record, never by deleting either.
