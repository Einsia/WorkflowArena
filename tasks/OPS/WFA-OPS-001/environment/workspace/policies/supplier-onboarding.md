# Supplier master data
A supplier carries a status in the supplier master. Only a supplier whose status is
`active` may be settled. A supplier placed under `suspended` remains in the master so that
historical settlements stay traceable; new settlements against it are not permitted and the
invoice is held pending resolution.

Changes to the supplier master are made by data governance, not by the payments team.
