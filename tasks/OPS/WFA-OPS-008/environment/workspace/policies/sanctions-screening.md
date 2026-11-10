# Sanctions screening
The sanctions register is maintained by the financial crime team. Procurement operations
reads it and never writes to it.

A screen matches where the applicant's registered legal name is **the same name** as a
listed name. A different legal entity with a similar name — a subsidiary, a regional
company, a trading name — is a different entity and is not a match; procurement operations
does not widen a listing beyond the entity named in it, and does not narrow one either.

Where the screen matches, the application stops. The applicant is not entered in the
supplier master, no bank details are held for it, and no spend ceiling is set. The
screen itself is recorded, with outcome `fail`, so that the decision is traceable.
