# AEGIS

**A venue operations layer for crowd emergencies.** Anyone inside a venue
reports in one tap; the system triages, merges duplicate reports of the same
event, and helps the venue's own control room dispatch its own responders.

Self hosted end to end. No managed backend, no proprietary app builder, no
vendor you cannot run yourself.

> This is a rebuild. AEGIS began as a hackathon entry for Cognitive Chaos 2026,
> which required a specific managed backend and a specific AI app builder. That
> entry is preserved, unmodified, at
> [`aegis-platform@v1.0-hackathon`](https://github.com/developwithsourav/aegis-platform/tree/v1.0-hackathon).
> This repository is the independent version, and it carries none of those
> requirements.

---

## What it is not

**AEGIS is not a replacement for 112.** India's ERSS already handles a citizen
reaching the state emergency system, and it does so with a call line, SMS, an
app, a panic button and location sharing. Competing with that would be silly.

112 routes a citizen to a **state control room**. It does not give the operator
of a particular venue a live picture of *their own* ground, it does not dispatch
*that venue's* marshals and medics, it does not merge thirty reports of one
crush into a single incident, and it cannot push exit guidance to the people
standing inside that venue.

AEGIS is that missing layer, and it should **escalate to 112**, not compete with
it.

---

## Why the phone call fails first

In a dense crowd you cannot hear and cannot be heard, and thousands of handsets
on one cell mean voice calls drop exactly when everybody needs them at once. A
tap is a few hundred bytes and gets through when a call will not. A call also
carries one report once; thirty callers about one crush produce thirty
conversations rather than one prioritised incident.

---

## Status

Early. The hackathon version worked end to end but leaned on managed services
and shipped one genuinely dishonest number, which the judges rightly called out.
This rebuild exists to fix both.

| | |
|---|---|
| Backend | FastAPI · PostgreSQL + PostGIS + pgvector · Redis |
| Frontend | Next.js |
| Realtime | WebSockets, served by us |
| Retrieval | pgvector over official response protocols |
| Severity | to be a trained classifier with published metrics, see `ROADMAP.md` |

### On the severity score

The hackathon build displayed a confidence percentage that came from **asking
the language model how confident it felt**. It was not calibrated against
anything, so a blank photograph scored 95%. That number is gone.

Until a trained classifier exists and has been evaluated on a held out set,
this project shows **corroboration** instead: how many independent people
reported the same thing in the same place. That is a real signal and it is
labelled as exactly what it is. Nothing here will claim to be a model
confidence until there is a calibration curve to back it.

---

## Running it

Requires Python 3.11 or 3.12, PostgreSQL 16 with PostGIS and pgvector, and
Redis. Python 3.13+ is not recommended yet because parts of the ML stack do not
ship wheels for it.

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate    # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                              # then edit DATABASE_URL
alembic upgrade head
uvicorn app.main:app --reload
```

With Docker available, `docker compose up` in `infra/` brings up Postgres and
Redis with the right extensions instead.

---

## Layout

```
backend/    FastAPI service, SQLAlchemy models, Alembic migrations
frontend/   Next.js client
ml/         datasets, training and evaluation for the severity model
infra/      compose files and deployment
docs/       design notes and decisions
```

## Licence

MIT. See `LICENSE`.
