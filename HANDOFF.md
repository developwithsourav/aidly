# AEGIS — complete handoff

Written 27 July 2026, at the end of the Claude Code sessions that built this.
Everything a person or an AI assistant needs to pick this up cold.

If you are an AI assistant reading this: the last section has a prompt you can
be given. Read the whole file first anyway. The most important parts are
**"Principles that must not be undone"** and **"Exact state right now"**.

---

> **Credentials are never written in this repository.** They belong in the
> environment, or in a password manager. An earlier revision of this file did
> contain them, so anything that was listed here should be treated as exposed
> and rotated.

# 1. What AEGIS is

A **venue operations layer for crowd emergencies**.

Someone inside a crowded venue taps once on their phone to report an emergency.
The system works out where they are, merges their report with other reports of
the same event, and gives the venue's own control room a live picture so it can
dispatch its own marshals, medics or fire team to the right place.

**One sentence:** *in a crowd you cannot hear, cannot be heard, and the network
is jammed, so a tap is a better way to call for help than a phone call.*

## What it is not

**It is not a replacement for 112.** India's ERSS already has a call line, SMS,
an app, a panic button and location sharing, and it does the citizen-to-state
path well. Trying to beat it is a losing argument and a judge will say so.

112 routes a citizen to a **state police control room**. It does not:

- give a specific venue a live picture of its *own* ground
- dispatch *that venue's* marshals, medics and fire team
- merge thirty reports of one crush into one incident
- broadcast exit guidance to the people standing inside that venue

AEGIS is that missing layer and should **escalate to 112**, not compete with it.
This framing was a direct response to judge feedback and it is much stronger
than the original pitch. Do not go back to "we replace 112".

---

# 2. History

## The hackathon

Built for **Cognitive Chaos 2026** (Hack Briven), Convex Open Innovation track,
finale on 25 July 2026 at Microsoft Office, Sovereign Noida.

Team **Ninja Coders** (`team-E463B7B2DF54`): Sourav Kumar, Manish Joshi,
Siddharth Singh, Rajat Kushwaha.

The competition mandated two third-party services:

- the frontend had to be built and deployed on **EnterPro** (an AI app builder)
- the Convex track required **Convex** as the backend

**Result: reached the final rounds, did not win.** The problem was taken
seriously by judges. Three specific criticisms sank it, all fair, all now
addressed (section 4).

## What happened on the day

The EnterPro deployment went down on the morning of the finale with
`ERR_CONNECTION_RESET` — TLS handshake refused. Their platform was up, our
instance was not. Verified from outside the venue network, so it was not local
wifi. The demo ran instead from an identical local build against the same live
Convex backend, which never went down.

Lesson worth keeping: **the backend having its own uptime, independent of the
frontend host, is what saved the demo.**

## Where the hackathon version lives

Repository: **`github.com/developwithsourav/aegis-platform`**

- tag **`v1.0-hackathon`** — exactly what was judged, frozen, never changes
- branch **`hackathon-submission`** — same commit, easier to check out
- `SUBMISSION.md` on `main` records what was entered

```bash
git checkout v1.0-hackathon    # what the judges saw
```

Show this to the organisers or teammates if anyone asks what was submitted.
Post-event fixes are on `main` from commit `f525ae5` onward; the tag
deliberately still contains the bugs, because that is what was judged.

Live at time of writing (may not persist, these are third-party accounts):

| | |
|---|---|
| App | `https://490cbec14e504e7aa506bc0208460713.prod.enterapp.pro` |
| Routes | `/` reporter · `/command` operator · `/responder` staff |
| Convex backend | deployment `judicious-oyster-529`, team `sourav-741ab` |
| Convex account | souravkumar.coder@gmail.com |
| Operator login | `control@aegis.live`, password held outside this repository |
| Responder passcode | held outside this repository |

Those credentials are **not** in either repository, on purpose. They are here
because this file is for you.

---

# 3. What the hackathon version actually did

Worth understanding before rebuilding it, because the behaviour is correct even
though the platform is being replaced.

```
REPORT ──▶ TRIAGE ──▶ COORDINATE ──▶ LEARN
```

1. **Report.** One tap on a category submits immediately with GPS attached. No
   login, no OTP. Photo, description and callback number offered afterwards,
   while help is already moving. GPS denied falls back to a zone dropdown.
2. **Triage.** An LLM scored severity P1–P4, wrote an operator summary, and
   response steps were retrieved from real NDMA and Indian Red Cross guidance.
3. **De-duplication.** Same category, same zone, within 120 seconds merged into
   one incident with a rising report count.
4. **Dispatch.** Nearest available responder whose role matched the category —
   medic for medical, fire unit for fire — chosen by haversine distance.
5. **Escalation.** An unacknowledged P1 escalated after 60 seconds, on a
   scheduled job.
6. **Tracking.** The reporter watched the assigned unit approach with a live
   ETA. No polling; Convex reactive queries pushed updates.
7. **Broadcast.** The operator could push exit guidance to every phone at once.
8. **Audit.** Append-only timeline per incident.

Verified end to end, including 50 simultaneous reports with zero failures
(which de-duplicated down to 14 incidents).

### Convex features used

Reactive queries (live subscriptions, no websocket code written), actions (the
LLM call — actions are the only Convex function type allowed to reach the
internet), vector search (1536-dim over the protocol corpus), scheduler
(escalation), file storage (photos), plus mutations for atomic ingest.

### Three access tiers

- `/` reporter — **open by design.** An OTP wall is exactly what a panicking
  person cannot get through.
- `/responder` — shared passcode
- `/command` — operator login

---

# 4. The three criticisms, and what was done

This section matters more than any other. These are the reasons it did not win.

## 4.1 Photo upload failed on mobile

**Cause:** the file input carried `capture="environment"`. On Android that
forces the camera and **removes the gallery picker entirely**; on some browsers
it fails outright.

**Fixed:** attribute removed. The browser now offers camera and gallery.

## 4.2 The confidence score was fabricated — the important one

The UI showed a percentage that came from **asking the language model how
confident it felt about itself**:

```js
confidence: Number(out.confidence)   // the model made this number up
confidence: description ? 62 : 50    // the fallback just hardcoded one
```

A judge submitted a **blank photo and got 95%**. There was no calibration, no
ground truth, no held-out evaluation anywhere. It was decoration pretending to
be a metric, and in an emergency tool that is genuinely dangerous, because an
operator might act on it.

**Fixed, in two steps:**

1. Confidence removed from the model prompt entirely.
2. The displayed number replaced with **corroboration** — how many independent
   people reported the same thing in the same place. 25% for one report, +20 per
   additional report, capped at 90. Computed in one place so it stays
   explainable. The UI now says *"Corroboration, not a model confidence score."*

Verified: the exact case that broke on stage — an empty report with no
description — now scores **25%** instead of 95%, rising to 45% on a second
independent report.

**This is the single most valuable thing to finish properly.** See Phase 2.

## 4.3 "112 already does this"

**Fixed** by repositioning rather than arguing. See section 1.

---

# 5. The rebuild

## Why

Three reasons, in order of importance:

1. **Ownership.** Convex and EnterPro were competition requirements, not
   choices. This is a personal project now and should not depend on either.
2. **The severity model.** Doing it properly needs Python, training code and
   published metrics.
3. **Public and reusable.** MIT licensed, self-hostable by anyone.

## Where it lives

**`github.com/developwithsourav/aegis`** — public, MIT. Local at `G:\Claude\aegis`.

## Stack, and why each piece

| Layer | Choice | Reason |
|---|---|---|
| API | FastAPI | Python, so the ML work lives in the same language as the service |
| Database | PostgreSQL 18 | one process instead of three |
| Geo | PostGIS | "nearest available responder" becomes one indexed query instead of loading every row and computing haversine in Python |
| Vectors | pgvector | protocol retrieval without a separate vector database |
| Cache/queue | Redis | escalation timers, rate limiting later |
| Frontend | Next.js | not started yet |
| Realtime | WebSockets, ours | replaces Convex reactive queries |

Everything is open source and self-hostable. Nothing here has a vendor you
cannot run yourself.

## Layout

```
aegis/
├── README.md          what it is, and what it is not
├── ROADMAP.md         phased plan
├── HANDOFF.md         this file
├── LICENSE            MIT
├── backend/
│   ├── pyproject.toml
│   ├── .env.example
│   └── app/
│       ├── config.py      settings; refuses to boot on a placeholder secret
│       ├── db.py          engine and session
│       ├── models.py      the schema
│       ├── routers/       EMPTY — not written yet
│       └── services/
│           ├── ingest.py    report intake, zone resolution, de-duplication
│           └── dispatch.py  dispatch, lifecycle, escalation
├── frontend/          EMPTY
├── ml/                EMPTY
├── infra/
│   ├── docker-compose.yml   Postgres + Redis (optional, see section 7)
│   └── init-db.sql
└── docs/decisions.md
```

---

# 6. Principles that must not be undone

If you change nothing else about how this project thinks, keep these.

## 6.1 Never display a number you cannot defend

`Incident.severity_probability` is **nullable**. It stays NULL until a trained
classifier with a calibration curve fills it. `triage_source` records whether a
priority came from `model`, `llm` or `rules`.

**An absent number is honest. An invented one is worse than useless**, because
someone may act on it during an emergency. This is enforced in the schema, not
just in a comment, precisely so it cannot quietly regress.

Corroboration lives in a **separate** property with a **different name** so the
two can never be conflated again.

## 6.2 Reporting must never be blocked

Ingestion cannot reject a report. Location falls back GPS → chosen zone → venue
centre. Somewhere approximate beats nothing when a person has tapped for help.
No login, no OTP on the reporting path, ever.

## 6.3 De-duplication is deliberately conservative

Same venue, category and zone, within the window, still open. A report with no
zone never merges. **Merging two genuinely separate emergencies is far worse
than showing one twice.**

## 6.4 Dispatch is deterministic

Triage may be probabilistic. Who gets sent is not. Nobody wants a model
deciding whether the medic goes, and an operator must be able to explain the
choice afterwards. Preferred role first, then anyone available.

## 6.5 Resolve must free the responder

Forgetting this is how a venue slowly runs out of units that are not busy.

## 6.6 The AI may not invent procedure

Response steps are retrieved from real published guidance and the source is
shown on screen. The model composes only from what was retrieved.

## 6.7 A phone number is never a location

Only a carrier can locate a handset. The callback field exists so a control room
can ring back. Say this out loud before anyone asks.

## 6.8 Degrade, do not fail

If the LLM is unavailable, fall back to deterministic rules and **say so on
screen**. The hackathon build did this and it was genuinely admired. Keep it.

---

# 7. Exact state right now

Be precise about this. Do not assume more is done than is.

## Done and verified against a real database

- Alembic set up. `alembic upgrade head` builds the schema from nothing,
  installs PostGIS and pgvector, and the down and up round trip is tested.
- **Increment I, authentication.** bcrypt hashing, signed tokens carrying the
  role, one failure message for every cause, and the account reloaded on each
  request so deactivating a user takes effect immediately.
- **Increment II, report intake.** Public reporting with no account. Zone from
  the device position, else a gate the reporter picks, else the venue centre.
  De-duplication by category, zone and time window with a corroboration count.
  Operator feed scoped to the operator's own venue.
- **Increment III in part, triage.** Deterministic rules assign a priority and
  write the reason into the trail. Handles code mixed Hindi and English.
  `severity_probability` stays null: a rule is not a calibrated probability.
- **Increment IV, dispatch.** Nearest available responder whose role matches
  the category, chosen by a PostGIS distance query. Acknowledgement, arrival
  and resolution. Resolving returns the unit to the pool. Escalation runs on a
  timer inside the application and is idempotent.
- `scripts/seed_demo.py` brings up a venue with zones, responders and accounts.
- **59 tests**, all against PostgreSQL with PostGIS. No mocked database.

## Not started

- Trained severity classifier. There is no labelled data, which is the real
  blocker, not the model. Rules are the baseline it has to beat.
- Protocol retrieval for the "what to do next" guidance. The `protocols` table
  and its pgvector column exist and hold zero rows.
- Broadcast, discreet reporting, photo storage, evidence chain of custody.
- WebSocket hub. Screens would have to poll today.
- Any frontend beyond the sign in page.

## Environment notes

- **Python 3.14 is the system default. Do not use it** for the machine learning
  work: PyTorch and transformers publish no wheels for it. Use `py -3.12`.
- Postgres runs in WSL. `localhost` forwarding from Windows does not work, but
  **the WSL IP does**. Get it with `wsl hostname -I`. This was the blocker
  recorded in earlier revisions of this file and it has a workaround now.
- Docker was abandoned on purpose. `infra/docker-compose.yml` is kept for
  anyone who does have it working.


# 8. Roadmap

## Phase 1 — a backend we own (in progress)

- [x] Repo, licence, layout, schema, ingestion, dispatch
- [ ] Alembic migrations, create the schema for real
- [ ] Fix or sidestep the WSL connectivity problem (consider moving the whole
      backend into WSL)
- [ ] `main.py` and routers: reports, incidents, responders, auth, broadcasts
- [ ] Pydantic request/response schemas
- [ ] Auth: JWT, password hashing, role dependencies
- [ ] WebSocket hub so screens stay live without polling
- [ ] Photo upload, local disk or S3-compatible
- [ ] Triage service with the same three-tier fallback as before
- [ ] Protocol corpus loaded and embedded with a local sentence-transformer
- [ ] Next.js frontend for the three roles
- [ ] End-to-end test mirroring the hackathon demo run

**Done when** the full demo flow works with no managed service involved.

## Phase 2 — a severity score that means something

The part the judges were right about, and the part worth putting on a CV.

- [ ] Build a labelled dataset of emergency reports across P1–P4. **Write down
      the labelling rules** so the labels are defensible when questioned.
- [ ] Hold out a genuine test set *before* any training
- [ ] Baselines first — keyword rules, then TF-IDF + logistic regression — so
      there is something to beat
- [ ] Fine-tune a small transformer (DistilBERT class)
- [ ] Report **macro-F1 and per-class recall**, not accuracy. Missing a P1
      matters far more than mislabelling a P4, so **recall on P1 is the number
      that counts.**
- [ ] Plot a **calibration curve**. A confidence score is only meaningful if
      predicted probability matches observed frequency. This is the thing whose
      absence lost the hackathon.
- [ ] Compare honestly against LLM zero-shot on the same test set, including
      latency and cost
- [ ] Serve the model, fill `severity_probability`, show it in the UI
- [ ] Publish the evaluation notebook in `ml/`

**Done when** the number on screen can be defended with a plot.

Needs Python 3.11/3.12. On a CV this reads as: *trained and calibrated a
severity classifier, macro-F1 X, P1 recall Y, replacing an uncalibrated LLM
self-report.* That is a real ML contribution.

## Phase 3 — something a venue could run

- [ ] Real auth with roles, replacing the shared passcode
- [ ] Rate limiting and abuse controls on the open reporting path, without an
      OTP wall
- [ ] Offline queueing on the reporter, syncing when signal returns
- [ ] Real facility data from data.gov.in and OpenStreetMap instead of
      hand-placed coordinates
- [ ] Formal escalation path to 112
- [ ] Monitoring, structured logs, CI
- [ ] Load testing with published numbers

## Deliberately deferred

Vision verification of photographs, crowd density from CCTV, and voice
reporting are all interesting and all sit **behind** the severity model. Doing
them first would repeat the original mistake: shipping something that looks
intelligent without being measured.

---

# 9. Things that were tried, and how they turned out

Saves you rediscovering them.

- **`anyApi` is a Proxy.** In the Convex client, `api.x.y` returns a *new
  object every access*. Passing it straight into a subscription hook makes the
  effect dependency change every render, so the subscription tears down and
  rebuilds forever and data never settles. Resolve references once.
- **htm forwards props verbatim** but React needs a style *object*, not a
  string, and `className` not `class`. A string style throws.
- **Gemini free tier is not dependable.** `gemini-flash-latest` intermittently
  returns 503; `gemini-2.0-flash` reported a free quota of literally 0. Walking
  a chain of three models before falling back to rules fixed it.
- **Geolocation with `enableHighAccuracy: true` times out on laptops** with no
  GPS chip. Retry coarsely before giving up, and watch the Permissions API for
  a later grant.
- **Convex validators treat `null` and `undefined` as different.** Browsers send
  `null` for empty optional fields, so `v.optional(v.number())` rejected every
  GPS-less report while the UI optimistically advanced.
- **Both auth gates once accepted any input** because the code did
  `if (result)` on a `{ok: boolean}` object, which is always truthy. Check
  `result.ok === true`.
- **`capture="environment"`** breaks mobile photo upload. Covered above.

---

# 10. Prompt for a fresh AI session

Paste this into a new Claude, ChatGPT or Cursor session, with this repository
open or this file attached.

```
I'm continuing work on AEGIS, my personal project. Read HANDOFF.md in the repo
root first — it has the full history, the architecture, the current state and
the principles.

Short version: AEGIS is a venue operations layer for crowd emergencies. Someone
in a crowd taps once to report; the system resolves their location to a venue
zone, merges duplicate reports of the same event, and lets the venue's control
room dispatch its own responders. It is NOT a 112 replacement — it is the
venue's internal layer and escalates to 112.

It began as a hackathon entry that reached the finals but did not win. The
judges' main criticism was that the confidence score was fabricated: it came
from asking an LLM how confident it felt, so a blank photo scored 95%. I am
rebuilding it self-hosted, off the managed services the competition required,
and replacing that number with a properly trained and calibrated classifier.

Stack: FastAPI, PostgreSQL 18 with PostGIS and pgvector, Redis, Next.js.
Python 3.12 (NOT 3.14 — no PyTorch wheels).

The rules I care most about:
- Never show a number we cannot defend. severity_probability stays NULL until a
  trained model with a calibration curve fills it.
- Reporting must never be blocked. No login, no OTP, always a location fallback.
- De-duplication stays conservative — merging two real emergencies is far worse
  than showing one twice.
- Dispatch stays deterministic and explainable.
- The AI may not invent procedure; steps are retrieved from real guidance with
  the source shown.
- Degrade rather than fail, and say so on screen.

Please tell me what you understand the current state to be before writing code,
and flag anything in HANDOFF.md that looks wrong or out of date.
```

---

# 11. If you only do three things

1. **Finish Phase 1 so it runs end to end self-hosted.** Consider moving the
   backend into WSL to sidestep the connectivity problem entirely.
2. **Do Phase 2 properly, with a calibration curve.** It answers the criticism
   that cost the competition, and it is the part that makes this a real ML
   project rather than an app that calls an API.
3. **Keep the honesty.** The most respected thing about this project, in the
   room and afterwards, was stating its own limits before being asked. Do not
   trade that for a better-sounding number.
