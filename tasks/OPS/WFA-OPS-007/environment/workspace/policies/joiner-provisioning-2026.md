# Joiner provisioning standard — 2026 edition
Issued 2026-01-01. Applies to every new starter recorded in the joiner register.
Supersedes the 2024 edition for starters whose start date falls on or after 2026-01-01.

## 1. One person, one HR record
A person holds exactly one HR record for the whole of their relationship with the
organisation. Where a returning starter already has a record in a dormant state, that
record is reactivated. Opening a second record for someone who already has one is a data
quality incident and is reported as such, even if the second record is correct in itself.

## 2. Start dates
Provisioning is aligned to the start date. An HR record and a payroll entry are created in
advance of the start date; the HR record of a starter whose start date falls in a later
period is held at `pending_start` and the payroll entry carries the later effective date.
System access and equipment are not issued ahead of the start date — a starter who is not
yet in post has no business need for either.

## 3. Access and the clearance gate
Two systems are provisioned at onboarding: `intranet` for everyone, and `corefin` for staff
whose duties require it. `corefin` holds financial records and may be opened only for a
person whose clearance is recorded as `granted`. Where clearance is still pending, the
`intranet` grant proceeds and the `corefin` grant waits; it is not opened "pending
clearance", and clearance is not recorded by this team.

## 4. Payroll
A payroll entry is opened for each starter engaged as an employee. Engagement type is taken
from the joiner register and is not reinterpreted.
