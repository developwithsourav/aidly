# Problem statement and project description

For the final-year software engineering submission, University of Delhi.
Written 31 August 2026. Reference text — paste into the synopsis and edit freely.

> **Working title.** The product name is still open (see
> `SAFETY-MODULE-HANDOFF.md` §10). Everywhere below, `<NAME>` is a placeholder.
> The submission title should read:
> *<NAME>: A Venue Operations Layer for Crowd Emergency Response and Responder
> Dispatch.*

---

## 1. Problem statement

In a densely crowded venue, the established way to summon help — a voice call to
an emergency number — fails at precisely the moment it is needed. Ambient noise
makes speech unusable, cell congestion drops calls when thousands of handsets
contend for one tower, and a call carries one person's account of an event that
dozens may be witnessing.

India's Emergency Response Support System (112) handles the citizen-to-state
path well, and this project does not attempt to replace it. But 112 routes a
caller to a **state** control room. It does not give the operator of a
particular venue a live picture of their own ground, it does not dispatch that
venue's own marshals, medics or fire team, it does not merge thirty reports of
one crush into a single prioritised incident, and it cannot push exit guidance
to the people standing inside that venue.

The result is a gap. At a college fest, a stadium or a religious gathering,
trained responders are frequently within a hundred metres of an incident, yet no
system routes a report to them, resolves where that report came from, or tells
the control room that thirty messages describe one event rather than thirty.

A second failure sits inside the same gap. Harassment at crowded events is
common and heavily under-reported, and a visible or audible alert can increase
the reporter's risk rather than reduce it. Existing tools alert either a state
control room or a pool of unvetted volunteers — neither is the venue's own
on-duty staff, and neither is discreet.

**The problem, stated once:** a crowded venue has responders, zones and an
operations room, but no channel that turns what attendees can see into
something that room can act on — quickly, without a voice call, without
duplication, and without exposing a reporter who cannot afford to be seen.

---

## 2. Description

`<NAME>` is a web-based venue operations layer for crowd emergencies.

Anyone inside a venue reports in one tap, optionally attaching a short
description or a photograph. The system resolves the report to a venue zone,
classifies it, merges it with other reports describing the same event, and
presents the control room with a live, de-duplicated picture of its own ground.
The operator dispatches the venue's own responders — the nearest available unit
whose capability matches the incident — tracks acknowledgement and arrival, and
broadcasts guidance to attendees where needed.

The central design premise is that **the network is unreliable exactly when the
system matters**. A tap is a few hundred bytes and gets through when a voice
call will not. Where location services fail, the reporter selects the nearest
gate instead of being blocked. Where no trained classifier has scored an
incident, the system reports the absence of a confidence value rather than
inventing one.

Personal safety is handled as a first-class incident category rather than a
separate application. A report of harassment can be submitted **discreetly** —
no sound, no vibration, no visible change of screen state — and is matched to a
responder by attribute as well as role, so that a request needing a female
responder is dispatched accordingly. Evidence is retained in an append-only
record with a chain of custody, so that a report can support a formal complaint
later if the reporter chooses to make one.

The system escalates to 112 rather than competing with it. Escalation is a
documented, deliberate handoff performed by the control room or triggered by an
unacknowledged high-severity timer.

---

## 3. Objectives

1. Provide a single-tap, low-bandwidth reporting channel that functions without
   a voice call and degrades gracefully when GPS or network is unavailable.
2. Resolve every report to a venue zone, by device location where available and
   by reporter selection where it is not.
3. Merge independent reports describing the same event — matched on category,
   zone and time window — into one incident carrying a corroboration count.
4. Assign a severity tier to each incident, and expose the method that produced
   it, reporting no confidence value where no trained model has scored it.
5. Dispatch the nearest available responder whose role and attributes match the
   incident category, with a documented fallback when none matches.
6. Escalate unacknowledged high-severity incidents automatically on a timer, and
   provide a documented escalation path to 112.
7. Support discreet submission for personal-safety incidents, where a visible or
   audible alert would increase the reporter's risk.
8. Maintain an append-only audit trail per incident, recording every state
   change and every access to attached evidence.
9. Broadcast advisories and exit guidance from the control room to attendees.

---

## 4. Scope

### In scope

- A single venue with multiple zones, configured by an administrator.
- Four actors: reporter (an unauthenticated attendee), responder, control room
  operator, and venue administrator.
- Incident categories: fire, medical, crowd, accident, violence, harassment,
  and other.
- A mobile-first web application; no native app.
- Real-time updates to operator and responder screens without polling.

### Out of scope — stated deliberately

- **This is not a replacement for 112,** and makes no claim to be.
- **No API integration with ERSS.** No public integration path is documented for
  third-party systems. Escalation is therefore a specified handoff — dialling,
  messaging and location transfer — not a backend connection.
- No hardware, wearables or panic buttons.
- No nationwide consumer deployment; the system is scoped to a venue that has
  its own responders on the system.
- No carrier-level handset location. A callback number exists so an operator can
  ring the reporter back, and is never used to locate them.

---

## 5. Modules

Numbered to match the Level 1 data flow diagram.

| # | Module | Responsibility |
|---|---|---|
| 1.0 | Report Intake | Capture, zone resolution, discreet handling, photo attachment |
| 2.0 | Triage | Categorisation and severity assignment, with an honest confidence signal |
| 3.0 | De-duplication and Incident Merge | Match and merge concurrent reports; maintain corroboration |
| 4.0 | Dispatch | Match responder by role and attribute, nearest-available assignment |
| 5.0 | Escalation | Unacknowledged-incident timer, handoff to 112 |
| 6.0 | Broadcast | Advisories and exit guidance to attendees |
| 7.0 | Audit and Evidence | Append-only incident record and chain of custody |

---

## 6. Tools and technologies

| Layer | Choice |
|---|---|
| Backend | Python 3.12, FastAPI |
| Database | PostgreSQL with PostGIS (geospatial) and pgvector (retrieval) |
| Migrations | Alembic |
| Cache and pub/sub | Redis |
| Real time | WebSockets |
| Frontend | React, mobile-first |
| Licence | MIT, self-hostable end to end |

Every component is self-hosted. The system depends on no managed backend and no
proprietary application builder — a deliberate change from the earlier prototype.

---

## 7. Expected outcome

A working, self-hosted system demonstrating the full path from report to
resolution: an attendee submits a report, it is zone-resolved and triaged,
duplicate reports collapse into one incident with a visible corroboration count,
the control room dispatches a matched responder, the responder acknowledges and
resolves, and the entire sequence is recoverable from the audit trail.

Evaluated by a **structured drill** — scripted scenarios run with volunteers,
with response times and de-duplication accuracy measured and reported as
numbers rather than claims.

Accompanied by the required software engineering documentation: data flow
diagrams at Levels 0, 1 and 2, and a use case diagram with written case
descriptions.

---

## 8. Prior work by the team

An earlier prototype was built for the Cognitive Chaos 2026 hackathon and
reached the finale. It established the reporting flow and the incident category
set, both of which carry forward. It ran on a managed backend and a proprietary
app builder required by the competition, used hardcoded data for a small number
of zones, and had no trained model behind its triage.

The present work is an independent rebuild that removes those dependencies and
implements the logic the prototype only demonstrated. Citing this honestly is a
strength: the repositioning away from "a 112 replacement" came directly out of
judge feedback, and the current framing is the result.
