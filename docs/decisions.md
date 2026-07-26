# Decisions

Short notes on choices that are not obvious, so future me does not undo them.

## Postgres with PostGIS and pgvector, rather than a managed backend

The hackathon build used a managed reactive database because the track required
it. It was genuinely good, but it is not something you can run yourself, and
the point of this rebuild is to own the whole stack.

Postgres covers all three needs in one process: relational data, geospatial
queries through PostGIS, and vector retrieval through pgvector. "Nearest
available responder whose role matches this category" becomes one indexed
query instead of loading every responder and computing haversine in Python.

## severity_probability is nullable, on purpose

The previous build always had a confidence number because it asked the language
model to produce one. That is how a blank photograph came to score 95%.

Here the column is NULL until a trained classifier fills it, and the API says
which path produced the triage via `triage_source`. An absent number is honest.
An invented one is worse than useless in an emergency tool, because an operator
may act on it.

## Corroboration is separate from severity

`Incident.corroboration` counts how many independent people reported the same
thing in the same place. It is evidence about the report, not a claim about the
model. Keeping it in a different field, with a different name, is what stops the
two being conflated again.

## Callback number is never used for location

Only a telecom carrier can locate a handset from its number. The field exists so
a control room can ring the reporter back, nothing more. Location comes from the
browser's geolocation API or from the zone the reporter picks.
