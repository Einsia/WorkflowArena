# Delegated Authority Instrument — DAI-2026
Issued 2026-04-01. Governs the holding and transfer of delegated approval authority.

## 2.1 Holding
Authority to approve is held by a named person through a delegation recorded in the
delegation register. A delegation carries a holder, a scope and a status.

## 2.2 Live and lapsed
A delegation with status `active` is **live**: a real approval power is sitting with that
person right now. A delegation with any other status — `lapsed`, `withdrawn`, `reassigned`
— is not live. It carries no authority and requires no action. Reviving, re-pointing or
re-dating a delegation that is not live is a change to the authority framework and is made
only by the Authority Committee.

## 2.3 Transfer before withdrawal
Where a person holding a **live** delegation is leaving, the delegation passes to that
person's line manager, as recorded against them in the leaver register, **before** their
systems access is withdrawn.

The order matters and is not a formality. Between the moment access is withdrawn and the
moment the delegation is transferred, the approval power sits with an account that cannot
be used and cannot be contacted: approvals queued against that scope stop, and the only way
to clear them is a retrospective authority grant, which the Authority Committee does not
issue. Withdrawing access first is therefore an outage, not an ordering preference.

Transfer is recorded on the delegation itself: status becomes `reassigned` and the receiving
person is named on the record. A delegation is never deleted.

## 2.4 Delegations held by people who are not leaving
Delegations held by anyone not in the leaver register are outside any recovery exercise and
are not to be touched, re-pointed or tidied.
