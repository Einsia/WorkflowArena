# Joiner Provisioning
Issued 2026-04-01. Governs the opening of records for people arriving. The mirror of
recovery, and separately governed.

## 1. Sequence
A personnel record is opened first. Payroll, access and equipment follow from it; none of
them is opened against a person who has no personnel record.

## 2. Start date
Access is not provisioned before the start date. A joiner whose start falls in a future
period has their personnel and payroll records opened and nothing else.

## 3. Returners
Where a dormant personnel record already exists for the person it is reactivated. A second
record is not opened. Two records for one person break year-end reconciliation.

## 4. Clearance
Access to `corefin` requires clearance status `granted`. A joiner whose clearance is
`pending` receives everything else and is reported as held.

## 5. Engagement
A `contractor` receives no payroll entry. Equipment and access follow the role in the usual
way.

## 6. Stock
Equipment is issued only from available stock. Where the required class is unavailable the
joiner is reported as held and no issue record is raised against a negative balance.
