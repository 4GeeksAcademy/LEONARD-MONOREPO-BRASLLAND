# Shared Brasaland Incident Rules

`incidents.py` is the shared source for incident categories, lifecycle states,
origins, branch IDs, model-field validation, and the historical CSV rules and
status mapping. The analyzer and seed script reuse the CSV validator; the API
model and seeder reuse the incident-field validator.

The CSV locations are `COL-01` through `COL-10` and `FLA-01` through `FLA-04`.
The manager additionally accepts `central` for incidents not tied to a location.
Historical `OPEN`, `CLOSED`, and `DISCARDED` statuses map to `open`, `resolved`,
and `discarded`; imported records use `customer` origin.