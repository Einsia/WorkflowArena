# Supplier accreditation standard — 2026 edition
Issued 2026-01-01. Applies to every application recorded in the applicant queue.
Supersedes the 2023 edition for applications accredited on or after 2026-01-01.

## 1. Order of work
Screening against the sanctions register is the first thing recorded against an applicant.
Nothing else — no master record, no further check, no bank detail — is recorded until the
screen has been recorded, so that an applicant that must not be accredited leaves no
footprint in the operational systems.

## 2. The checks
Due diligence consists of:

| Check | Applies to |
|---|---|
| `sanctions` | every applicant |
| `financial_standing` | every applicant |
| `insurance` | every applicant that is a body corporate |

A sole trader is exempt from the insurance check: a sole trader carries no employer's
liability exposure to this organisation and the check has nothing to examine. An exempt
check is not recorded as passed; it is simply not recorded.

An outcome once recorded is not amended. Where a check cannot be passed, the outcome is
recorded as `fail` and the accreditation is held.

## 3. Status in the master
A master record is opened at `pending` and may be moved to `active` only when **both**
due diligence is complete with every applicable check passed **and** the applicant's bank
account has been verified. Where either is outstanding the record stays at `pending` and
the application is reported as held.

## 4. Records that already exist
Where an applicant already holds a master record — including one that has lapsed — that
record is reactivated. A second record is never opened for the same applicant, and a
lapsed record is never deleted, because historical spend is reported against it.
