# Aidly

**A venue operations layer for crowd emergencies.**

Someone inside a crowded venue taps once on their phone. The system works out
which zone they are in, decides how urgent it is, merges their report with
other reports of the same event, and gives the venue's own control room a live
picture so it can send its own marshals, medics or fire team to the right
place.

> In a crowd you cannot hear, cannot be heard, and the network is jammed. A tap
> is a few hundred bytes and gets through when a voice call will not.

**Aidly does not replace 112.** India's ERSS already handles the citizen to
state path. It does not give one venue a live picture of its own ground, does
not dispatch that venue's own responders, does not merge thirty reports of one
crush into a single incident, and cannot push exit guidance to the people
standing inside. Aidly is that missing layer, and it **escalates to 112**
rather than competing with it.

Self hosted end to end. No managed backend, no proprietary app builder, no
vendor you cannot run yourself.

---

## Status

| Increment | Scope | State |
|---|---|---|
| I | Database, schema, authentication | **Done** |
| II | Report intake, zone resolution, incident feed | **Done** |
| III | Triage and severity | **Rules done.** Trained classifier not started |
| IV | Dispatch, acknowledgement, escalation | **Done** |
| V | Broadcast, discreet reporting, evidence chain | Not started |

**59 tests pass** against a real PostgreSQL database with PostGIS. There is no
frontend yet beyond the sign in screen; everything is exercised through the
API and the tests.

---

## What works today

```
Report received
Triaged P1 by rules: breathing reported to have stopped
medic M-02 dispatched (role matched), ETA 1 min
Accepted, en route
On scene
Resolved, audit log closed
```

That transcript is real output, not an illustration. The whole path from a tap
to a closed incident runs.

- **Reporting is public.** An attendee in an emergency cannot be asked to hold
  an account. Everything operational is authenticated.
- **Location never blocks a report.** Device position, else a gate the reporter
  picks, else the venue centre. A report is never rejected for missing an
  optional field.
- **Duplicate reports merge.** Same category, same zone, inside a time window
  becomes one incident with a corroboration count, not thirty incidents.
- **Triage explains itself.** Rules assign a priority and write the reason into
  the audit trail in words. `severity_probability` stays null, because a rule
  is not a calibrated probability.
- **Dispatch is deterministic.** Nearest available responder whose role matches
  the category, chosen by a PostGIS distance query. No model decides who goes.
- **Nothing fails silently.** No responder available is an error the operator
  sees and an entry in the trail, never a success with nothing attached.

---

## Running it

Requires PostgreSQL 18 with **PostGIS** and **pgvector**, and Python 3.12.

```bash
createdb aegis
export DATABASE_URL="postgresql+psycopg://USER:PASSWORD@localhost/aegis"
export JWT_SECRET="a random string of at least 32 characters"

pip install -e .
alembic upgrade head          # creates the schema and both extensions
python -m scripts.seed_demo   # one venue, 5 zones, 6 responders, 3 accounts
uvicorn app.main:app --reload
```

Open `http://localhost:8000/login` for the control room sign in screen, or
`http://localhost:8000/docs` for the generated API reference.

Neither the connection string nor the signing secret has a working default. If
either is missing the application refuses to start rather than falling back to
something insecure.

```bash
pytest            # 59 tests, needs a reachable database
```

---

## The API

| Method | Path | Access |
|---|---|---|
| `POST` | `/api/auth/login` | public |
| `GET` | `/api/auth/me` | any signed in account |
| `GET` | `/api/venues/{slug}` | public |
| `POST` | `/api/reports` | **public, by design** |
| `GET` | `/api/incidents` | operator |
| `GET` | `/api/incidents/{id}` | operator |
| `GET` | `/api/incidents/{id}/events` | operator |
| `POST` | `/api/incidents/{id}/dispatch` | operator |
| `POST` | `/api/incidents/{id}/acknowledge` | assigned responder or operator |
| `POST` | `/api/incidents/{id}/on-scene` | assigned responder or operator |
| `POST` | `/api/incidents/{id}/resolve` | assigned responder or operator |
| `POST` | `/api/incidents/{id}/priority` | operator |
| `POST` | `/api/incidents/escalation-sweep` | operator |
| `GET` | `/api/responders` | operator |
| `GET` | `/api/assignments/mine` | responder |

The incident feed is scoped to the operator's own venue from their account, not
from a query parameter, so one venue's operator cannot read another's ground by
editing a URL. An incident belonging to another venue returns 404 rather than
403, so the response cannot be used to discover that it exists.

---

## Layout

```
backend/
  alembic/            migrations, including the PostGIS and pgvector setup
  app/
    core/security.py  bcrypt hashing, token issue and verify
    routers/          auth, reports, dispatch
    services/         ingest, triage, dispatch, auth
    models.py         the whole schema in one file
  scripts/seed_demo.py
  tests/              59 tests, all against a real database
docs/
  Aidly_SE_Report.pdf     the project report
  report_src/             the report is generated from source, not written in Word
```

---

## Design decisions worth knowing

**Severity and corroboration are kept apart.** `severity_probability` is what a
model claims about one report. `report_count` is how many people independently
described the same thing. Combining them would let a weak model look like
corroborated fact. The probability stays null until a trained classifier
exists, because an absent number is honest and an invented one is not. An
earlier build scored a blank photograph at 95 per cent; this is the fix.

**Triage rules may raise urgency and never lower it.** A wrongly raised
incident costs a wasted walk. A wrongly lowered one costs the thing the system
exists for.

**The callback number is never used to locate anyone.** Only a carrier can do
that. The field exists so a control room can ring back, nothing more.

**Events are append only.** The trail is never updated and never deleted, so an
incident can be reconstructed afterwards from the record alone.

More of the reasoning is in [`docs/decisions.md`](docs/decisions.md) and
[`HANDOFF.md`](HANDOFF.md).

---

## History

Aidly began as **AEGIS**, a hackathon entry for Cognitive Chaos 2026, built on a
managed backend and a proprietary app builder the competition required. That
entry is preserved unmodified at
[`aegis-platform@v1.0-hackathon`](https://github.com/developwithsourav/aegis-platform/tree/v1.0-hackathon),
in a separate repository.

This repository is the independent rebuild. It carries none of those
requirements, and it exists because the interesting parts of the problem, the
merging and the severity judgement, were the parts the prototype only mimed.

## Licence

MIT. See [LICENSE](LICENSE).
