# On-ground safety, and the final-year submission

Written 31 August 2026. This document folds a second idea — personal and
women's safety at crowded venues — into AEGIS, and sets AEGIS up to be submitted
as a University of Delhi final-year software engineering project.

Read `HANDOFF.md` first. It explains what AEGIS is and what state the code is
in. This file only covers what is **new** and what is **graded**.

---

# 1. The idea, as it arrived

> At a fest, a stadium, any crowded event, there are many exits, too many
> people, and you cannot call anyone. So: text for help, attach a photo, or one
> tap for SOS — ambulance, first aid, police, fire, medical, whatever is needed.
> And if a woman feels unsafe in that area, she can reach someone nearby.

Two thirds of that is already AEGIS. The last sentence is not, and it is the
part worth building.

---

# 2. The decision

**This is AEGIS. It is not a new project.**

The crowded venue, the jammed network, the tap instead of the call, the photo,
the routing to medical or fire or police, the escalation to 112 — all of that is
already specified, already has a schema, and already has ingestion and dispatch
written. Starting again would mean rebuilding the two hardest services from
scratch to arrive back where the repository already is.

**Personal safety becomes a first-class incident category inside the venue
layer**, alongside medical, fire and crowd. It does not become a separate app.

That choice is not just about saving work. It is what makes the idea
defensible — see the next section.

**This is about the codebase, not the name.** The name is open and is being
reconsidered. See section 10.

---

# 3. Positioning: two questions you will be asked

## 3.1 "112 already does this"

Answered already, and the answer must not be undone. AEGIS is the layer 112 does
not provide: **one venue's own ground, its own responders, its own broadcasts.**
It escalates to 112 rather than competing with it. `HANDOFF.md` §1 has the full
argument. Do not go back to "we replace 112".

The reason this matters here: a pan-India, citizen-facing, one-tap-for-an-
ambulance app **is** the position the judges rejected. If the safety idea is
built that way, the strongest thing about AEGIS is thrown away. Building it as a
venue incident category keeps the position intact.

## 3.2 "The 112 India app already has SHOUT" — the new one

This will come up, especially in Delhi. Know it before someone tells you.

- **112 India (ERSS)** ships a **SHOUT** feature: a woman triggers it and
  registered volunteers nearby are alerted.
- **Delhi Police** runs **Himmat / Himmat Plus** for the same purpose.

So "she can alert people nearby" is already shipped by the government, and it
cannot be your differentiator. Verify the current behaviour of both yourself
before you write it into the report — do not cite this document for it.

**The honest difference, and the one to build:**

| | 112 SHOUT / Himmat | AEGIS safety category |
|---|---|---|
| Who is alerted | Registered volunteers near you, and a state control room | The **venue's own** trained marshals and security, on duty, on site |
| At a 50,000-person fest | Volunteer alerts are noise; the control room is off-site | The control room is **inside the venue**, watching its own zones |
| Response distance | Unknown, unbounded | Zone-resolved, nearest available, typically metres |
| Accountability | None on the volunteer | Named responder, timestamped acknowledgement, audit trail |
| Duplicate reports | Thirty alerts stay thirty alerts | Merged into one incident with corroboration |

That is a real difference, it is measurable, and it survives a hostile question.
It is also only true if the venue actually has responders on the system — which
is exactly why AEGIS is a venue product and not a consumer one.

---

# 4. What the safety category actually means

Not a label on the existing form. Four concrete behaviours, none of which the
current code has.

### 4.1 Discreet reporting

Someone reporting harassment often cannot be seen doing it. A siren, a flash, a
full-screen red alert — any of these can make the situation worse.

- Silent submission. No sound, no vibration, no visible state change.
- The screen must remain unremarkable after sending.
- A confirmation the reporter can dismiss instantly.
- No push notification back to that handset by default.

This is a genuine engineering constraint and it is the most interesting thing in
the module.

### 4.2 Escort and companion requests

Not every safety need is an emergency. "Walk me to Gate 2." "Walk me to my car."
A low-severity, high-frequency request the venue can actually serve, and one
that 112 will never handle. This is likely the most *used* feature and the
easiest to demonstrate working.

### 4.3 Responder attribute matching

Current dispatch matches **category → role**. A harassment or escort request
often needs a *female* responder, and that is an attribute, not a role.
`services/dispatch.py` must learn to match on role **and** attributes, with a
documented fallback when no matching responder is free — the fallback must never
be "no one goes".

### 4.4 Evidence that could survive a complaint

If a report may later support an FIR, the record has to be worth something.

- Photo and optional audio, timestamped, tied to the zone.
- Append-only — the audit trail already exists in the schema; use it.
- Chain of custody: who viewed the evidence, and when.
- Reporter identity visible to the control room, **not** to every responder.

---

# 5. Schema changes — make these before the first migration

**Time-sensitive.** Per `HANDOFF.md`, the schema has never been created in a real
database and Alembic has not been set up. These fields are free right now and
cost a migration later.

In `backend/app/models.py`:

| Where | Change |
|---|---|
| `Category` | Add `harassment`. Consider `escort` as a separate low-severity category rather than overloading `other`. |
| `Responder` | Add attribute flags for matching — at minimum a female-responder flag and an escort-capable flag. Prefer explicit boolean columns over a free-form tag array; they index cleanly and the dispatch query stays one statement. |
| `Report` | Add `is_discreet` (bool). It changes API behaviour, not just presentation, so it belongs on the row. |
| `Incident` | Add a sensitivity or visibility field controlling which responder fields are exposed. |
| Indexes | Extend `ix_responders_dispatch` to cover the new matching attributes. |

Decide **before** writing the migration whether escort is a category or a
severity tier. Changing it afterwards means touching triage, dispatch and every
diagram in section 6.

Also add a note to `docs/decisions.md` explaining why discreet mode suppresses
return notifications. That is the kind of choice a future reader will
otherwise undo.

---

# 6. The graded part — DFDs and use cases

Your college requires **DFD Level 0, Level 1 (and Level 2)** and a **use case
diagram with written descriptions**. No ERD, class, sequence or SRS.

**Draw these in weeks 1–2, not at the end.** Two reasons: the marks are attached
to the documents, and drawing a Level 1 forces the scope decisions in section 5
into the open before you write a migration you regret.

## 6.1 External entities (for Level 0)

| Entity | Notes |
|---|---|
| Reporter (attendee) | Anyone inside the venue. Not authenticated. |
| Responder | Marshal, medic, fire, security. On duty, on site. |
| Control Room Operator | Sees everything, dispatches, broadcasts. |
| Venue Administrator | Configures venue, zones, responders. |
| 112 / ERSS | External system. Escalation target only — never a data source. |

Keep 112 as an external entity, never a process. It is outside your boundary and
drawing it inside will earn a question you cannot answer.

## 6.2 Level 1 processes

Numbered so Level 2 decomposition is unambiguous:

| # | Process |
|---|---|
| 1.0 | Report Intake — capture, zone resolution, discreet handling |
| 2.0 | Triage — categorise and assign severity |
| 3.0 | De-duplication and Incident Merge — corroboration |
| 4.0 | Dispatch — match responder by role and attributes, assign |
| 5.0 | Escalation — unacknowledged P1 timer, handoff to 112 |
| 6.0 | Broadcast — exit guidance and advisories to the venue |
| 7.0 | Audit and Evidence — append-only record, chain of custody |

## 6.3 Data stores

`D1 Reports`, `D2 Incidents`, `D3 Responders`, `D4 Venues and Zones`,
`D5 Protocols`, `D6 Audit Log`, `D7 Broadcasts`.

These map one-to-one onto the tables that already exist in `models.py`, which
means your diagrams describe the real system rather than a parallel fiction.
Say that in your report — examiners notice.

## 6.4 Level 2 — decompose these two

Pick the processes with real logic, not the ones that are easy to draw.

- **2.0 Triage** — the three-tier fallback, and why `severity_probability` is
  nullable. `docs/decisions.md` already argues this and it is a strong point in
  a viva: an absent confidence number is honest, an invented one is dangerous.
- **4.0 Dispatch** — role match, attribute match, availability, nearest by
  PostGIS distance, and the documented fallback when nothing matches.

## 6.5 Use cases

**Actors:** Reporter, Responder, Control Room Operator, Venue Administrator,
System (timer-driven escalation), 112/ERSS.

| Use case | Primary actor |
|---|---|
| Submit emergency report | Reporter |
| Submit discreet safety report | Reporter |
| Request escort | Reporter |
| Attach photo evidence | Reporter |
| Triage and verify incident | Operator |
| Dispatch responder | Operator |
| Acknowledge assignment | Responder |
| Mark on-scene / resolve | Responder |
| Escalate to 112 | Operator, System |
| Broadcast exit guidance | Operator |
| Manage venue, zones, responders | Administrator |
| Export incident record | Operator |

Write full descriptions for at least **Submit discreet safety report** and
**Dispatch responder** — preconditions, main flow, alternate flows, exceptions.
Those two carry the novel logic; the rest can be summarised.

---

# 7. Twelve weeks

Assumes part-time alongside coursework. The ordering is dependency-driven: each
phase must leave the project working.

| Weeks | Work |
|---|---|
| 1–2 | Unblock WSL — move the backend into WSL rather than bridging the port. Add the section 5 schema fields. Alembic set up, **schema created in a real database for the first time**. Draw DFD L0 and L1. |
| 3–5 | `main.py`, routers, Pydantic schemas, auth with JWT and role dependencies. Reports and incidents endpoints working end to end. |
| 6–8 | WebSocket hub. Frontend for the three roles. Photo upload. The system becomes demonstrable here — this is the milestone that matters most. |
| 9–10 | Safety category proper: discreet mode, escort flow, attribute matching, evidence chain. DFD L2 and full use case descriptions. |
| 11 | Evaluation. A structured drill — scripted scenarios, volunteers, measured response times. Numbers, not adjectives. |
| 12 | Report, diagrams finalised, demo video, viva preparation, submission. |

**The single highest-risk item is week 1.** Nothing else can start until the
schema exists in a real database. If WSL resists for more than a few days,
consider SQLite with a PostGIS-free fallback for development only — but say so
explicitly in the report rather than hiding it.

Do not leave the drill in week 11 to chance. Book the volunteers in week 8.

---

# 8. Government integration — what is real

Be precise here, because the plan currently depends on something that may not be
available.

**ERSS/112 has no public API.** There is no documented integration path for a
third-party application to file into the state emergency system. Verify this
yourself; do not take it from this document. But plan as if it is true.

**Tier 1 — buildable, this term.** A `tel:112` dial with context shown on screen
for the caller to read out. An SMS fallback carrying location. A deep link into
the 112 India app. A location payload the operator can hand over. This is a real
escalation path and it is honest.

**Tier 2 — the actual contribution.** Write a formal *Escalation Interface
Specification*: what AEGIS would send, in what format, under what authority,
with what guarantees. Research the ERSS architecture from published government
sources and cite them. This is a deliverable you fully control, it demonstrates
systems thinking, and it is far more impressive in a viva than a screenshot of a
dialler.

**Tier 3 — outreach, low probability.** Writing to a state police body or a
venue operator is worth doing and should not be planned around. An MoU inside
three months, as a student, would be exceptional. Send the letters; make the
project complete without a reply.

> Outreach means contacting real organisations from your accounts. I will draft
> anything you want, but I will not send an email, file a form or contact any
> body without you asking me to in that moment.

---

# 9. Duty of care

An application that invites someone to report harassment, and that may fail, has
obligations. This section belongs in the report; examiners and judges both ask.

- **Never promise what the system cannot deliver.** If no responder is
  available, say so, and offer 112 immediately. Silence is the worst outcome.
- **Data protection.** Reports contain location, photographs and possibly
  identity. India's DPDP Act 2023 applies. Collect the minimum, state the
  retention period, and delete on schedule.
- **Minors.** Fests and college events have attendees under 18. Consent and
  handling differ, and the report should acknowledge it.
- **False and malicious reports.** Dispatching security to a named person on an
  anonymous report can cause real harm. The audit trail and the operator
  verification step are what stand between the system and misuse — design that
  deliberately, do not treat it as an afterthought.
- **The reporter's identity is not the responder's business.** Control room
  sees it; the marshal walking over does not need it.

---

# 10. Naming — open

Continuing the codebase is not the same as keeping the name. Section 2 says the
*code* continues; the name is a separate decision and it is currently open,
because the name is not liked.

**Rename now or not at all.** The rebuild has no users, no release, no
migrations and no external dependents. The cost today is: two repository
renames, a find-and-replace across the docs, and the Python package directory.
That cost only rises. This is the same argument as section 5 — do the cheap
thing while it is still cheap.

**What is wrong with AEGIS:** it is a crowded name. It is a Greek shield, which
puts it in the same undifferentiated bucket as Sentinel, Bastion, Citadel and
Guardian, and it is already the name of a well-known naval combat system and
several security firms. It says nothing about crowds, venues, or India.

**Directions worth exploring**, rather than a shortlist to pick from:

- *The call that gets through.* The core insight is that you cannot be heard, so
  you tap instead. A name meaning a call, a shout or a summons carries the whole
  product in one word.
- *The venue's own eyes.* The differentiator is that the control room sees its
  own ground. Names around sight, watch or vigil fit the argument you actually
  win on.
- *Many voices, one signal.* De-duplication is the genuinely novel engineering.
  Nothing in the current name gestures at it.
- *Plainly functional.* A descriptive product name is not a failure. For a tool
  sold to venue operators it may outperform a mythological one.

**One trap:** *Kavach* is the obvious Hindi choice and it is taken — Indian
Railways' anti-collision system carries that name nationally. Check any Indian
candidate against existing government and public-sector systems before
committing, and check the GitHub and domain availability in the same sitting.

## The submission title is a separate thing

Whatever the product is called, the DU title should be descriptive:

> *<Name>: A Venue Operations Layer for Crowd Emergency Response and Responder
> Dispatch*

If the safety module is central to the pitch, extend it with *"— with Discreet
On-Ground Safety Reporting"*. Do not put "women's safety" in the title while the
system is a general venue layer; it invites the SHOUT question from section 3.2
before you have had a chance to answer it.

---

# 11. Risks

| Risk | Likelihood | Response |
|---|---|---|
| WSL/Postgres blocker persists | Medium | Move backend fully into WSL. Time-box to one week, then fall back and document it. |
| Scope creep back toward a consumer SOS app | **High** | Re-read section 3. The venue boundary is the whole argument. |
| No pilot venue agrees | High | A structured drill with volunteers is a valid substitute and already the plan. |
| Diagrams drift from the code | Medium | Draw them from `models.py`, and revisit at week 9. |
| Safety module ships without discreet mode | Medium | Then it is a label, not a feature. Build 4.1 first, not last. |
| Government reply never arrives | High | Tier 2 specification is the deliverable. Do not block. |

---

# 12. Open questions

1. Is escort a category or a severity tier? Decide before the first migration.
2. What is the retention period for photographic evidence, and who approved it?
3. Does the drill happen at ARSD, and who authorises it?
4. Does the report cite the hackathon build as prior work? It should — the
   repositioning story after judge feedback is a genuine strength, not a
   weakness to hide.
5. Which venue is the realistic pilot, if any?
