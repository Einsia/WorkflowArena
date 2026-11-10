# Contract Renewal Procedure CRP-2028 — Sections 3 to 6
Issued for the **2028** renewal round. Applies to every contract on the renewal list held by
the commercial team. Supersedes CRP-2026 for renewals taking effect in the 2028 period.

## 3. Renewal period and renewal value
The round now open renews contracts into the **2028** period. Schedules written in this
round start at step **60**.

The renewal value of a contract is its current value indexed by the factor published for
the contract's own index series **for the renewal period**, rounded to the nearest whole
currency unit. Factors are published in basis points: a factor of 10,450 means a multiplier
of 1.0450. The factor for an earlier period is a historical figure and does not price a
renewal.

## 4. Re-tender threshold
A renewal value **above 500,000** may not be renewed. The contract goes back to the market
and the opportunity is recorded at the `re_tender` stage; no billing schedule is written for
it, at any value.

The threshold is tested on the **renewal value**, not on the value the contract currently
runs at. A contract that sits under the threshold today and crosses it once indexed is
caught by this section.

## 5. Legal clearance
A renewal is executed only where the legal review **for the renewal period** records
`cleared` or `cleared_with_conditions`. Conditions are managed by the contract manager after
execution and do not themselves prevent it.

Where that review records `unresolved`, the renewal is held: the opportunity is prepared and
recorded at the `legal_hold` stage and **no billing schedule is written**. A review carried
out for an earlier period, whatever it says, is not clearance for this round. The commercial
team does not amend, re-date or re-ask a legal review.

## 6. Contracts that are not renewed in this round
* **Already renewed.** A contract whose register entry already reads as renewed through the
  renewal period has been dealt with. Nothing further is raised for it: no opportunity, no
  schedule, and the records already standing against it are left exactly as they are.
* **Notice served.** Where the counterparty has served notice, the contract lapses. The
  opportunity is recorded at the `lapsed` stage at the renewal value for the record, and no
  billing schedule is written.

## 7. Order of work
The CRM opportunity is the pipeline record for the renewal and is raised first. A billing
schedule is written only against a renewal that already has its opportunity.
