# Access Recertification — annual cycle
Issued 2026-01-15. Governs the annual review of standing systems access. This is a
periodic assurance exercise and has nothing to do with departures.

## 1. Scope
Every `active` grant in the access register is reviewed once a year by the system owner.
The review asks whether the holder's current role still requires the grant.

## 2. Dormancy
A grant with no recorded use for 90 consecutive days is treated as dormant and is withdrawn
at the next recertification point. Dormancy is measured from the access log, not from the
grant date.

## 3. Privileged systems
Grants to `corefin` and `approvals` are recertified twice a year rather than once, and
require the system owner's countersignature.

## 4. Outcome
Withdrawals arising from recertification are recorded with reason code `RECERT` and are
notified to the holder fourteen days in advance. A holder may appeal to the system owner
within that window.

## 5. Relationship to other exercises
Recertification does not withdraw access from anyone on the basis of a leaver record, and
a recovery exercise does not substitute for recertification. The two run independently and
are reported separately.
