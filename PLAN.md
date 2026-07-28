# AEGIS — the 12 week plan

Goal: in three months, AEGIS should be something you can put in front of a
venue operator, a hiring manager or a judge and defend with **measurements**,
not adjectives.

The bar is not "more features". The bar is:

> Every claim on the landing page has a number behind it, and every number has
> a method behind it that survives a hostile question.

No sponsorships, no partner data, no paid API you cannot replace. Everything
here is buildable from public data and your own machine.

---

# The strategic problem to solve first

Right now AEGIS is *a good app that calls an LLM*. That is not defensible.
Anyone can rebuild it in a weekend, and 112 already owns "citizen reports an
emergency".

There are exactly **three** things that could make it genuinely hard to copy:

### 1. It reads Indian emergency text properly

Real reports at an Indian venue are code-mixed:

> "bhai gate 3 pe bhagdad ho rahi hai, log gir rahe hain"
> "aunty ko saans nahi aa raha, medical chahiye jaldi"

An English-only model, or a generic LLM prompt, handles this badly and nobody
has published a calibrated severity classifier for Hindi-English emergency
reports. **That gap is real, it is Indian-specific, and it is yours to fill.**

### 2. It can see a crush forming before anyone reports a crush

This is the actual innovation and it is nearly free.

A single 112 call carries one person's view. AEGIS receives **many reports from
many phones with timestamps and coordinates**. That is a spatial-temporal point
process, and the shape of it changes before the emergency is named:

- report rate in a zone rising faster than baseline
- reports clustering tighter geographically
- categories drifting from "other" toward "crowd" and "medical"

You can estimate crush risk **from the report geometry alone**. No CCTV, no
sensors, no partnership, no hardware. Just the data the system already has.

*Nobody in the 112 stack can do this, because they never see the reports as a
population.* This is the thing to build.

### 3. Its advice is auditable

Every step traceable to a published document, with the citation on screen.
Already true. Keep it and make it stronger with a retrieval evaluation.

**Everything in this plan serves one of those three.** If a task does not, cut
it.

---

# Month 1 — foundation and real data

## Week 1 · Finish the backend, self-hosted

Finish Phase 1 from `ROADMAP.md`. No new ideas until the old system runs on
your own stack.

- Move the backend **into WSL**. One Linux host removes the connectivity
  problem and matches your future deploy target.
- Alembic migrations, schema created for real
- Routers: reports, incidents, responders, broadcasts, auth
- JWT auth with roles, replacing the shared passcode
- WebSocket hub
- Photo upload to disk, S3-compatible interface
- Triage service with the three-tier fallback preserved
- **Pytest suite that reproduces the whole hackathon demo flow**

**Exit criterion:** `pytest` green, and the full report → triage → dedup →
dispatch → resolve flow works with no managed service.

## Week 2 · Ingest real data, properly

This is what separates a demo from a product. All free, all public.

| Source | What you get | How |
|---|---|---|
| **data.gov.in** | Hospitals, police stations, fire stations across India | free API key, REST |
| **OpenStreetMap Overpass** | Venue footprints, gates, exits, roads, nearby `amenity=hospital` | Overpass QL, no key |
| **NDMA publications** | Crowd management, fire safety, first aid guidance | public PDFs |
| **IMD / OpenWeatherMap** | Temperature and humidity → heat index | free tier |
| **Wikipedia + EM-DAT** | Historical Indian stampedes: place, date, deaths, cause | scrape, then hand-verify |

Build:

- `ml/data/ingest_facilities.py` — pull real facilities, store with PostGIS
  points, keep the source and fetch date on every row
- `ml/data/ingest_venue.py` — given an OSM relation ID, generate a venue with
  real gates and exits. **A venue should take one command, not hand-typed
  coordinates.**
- `ml/data/protocols.py` — chunk the NDMA PDFs into protocol records with real
  citations (document, section, page)

**Exit criterion:** you can stand up any Indian venue from its OSM ID with real
surrounding hospitals, police and fire stations, and every protocol on screen
cites a page number.

> **Honesty rule:** store `source` and `fetched_at` on every ingested row. When
> someone asks "is this real data?", you show the row, not your memory.

## Week 3–4 · The dataset (the hardest part, do not rush it)

Everything in Month 2 depends on this. A weak dataset means a meaningless model
and you are back where the hackathon left you.

### Write the labelling rubric first

Before a single label. A one-page document defining P1–P4 with **decision
rules and edge cases**:

```
P1  Immediate risk to life. Not breathing, unresponsive, active fire,
    crush with people down, severe bleeding.
P2  Serious, deteriorating without intervention. Injury, smoke without
    fire, violence in progress, missing child.
P3  Needs response, not time-critical. Missing adult, minor hazard,
    non-urgent medical.
P4  Log only. Complaints, lost property.

Edge cases:
  Missing child is P2 not P3, because abduction risk is time-bound.
  "Feeling dizzy" is P3 unless the text implies collapse or breathing.
  Any crush wording is P1 regardless of stated injuries, because density
    kills faster than the reporter can perceive.
```

**Publish this rubric in the repo.** It is what makes your labels defensible,
and it is exactly what a serious interviewer will ask for.

### Build the corpus — target 3,000–5,000 labelled reports

Four sources, deliberately mixed:

1. **Seeded from reality (~300).** Descriptions from real Indian incident
   reporting: Hathras, Bengaluru, Kumbh, temple stampedes, festival fires.
   Hand-label against the rubric. These become your **gold set**.
2. **Template expansion (~1,500).** Realistic phrasings per category and
   severity, varied by venue type, time of day, reporter panic level.
3. **LLM augmentation (~2,000).** Generate paraphrases *from your labelled
   seeds*, never labels themselves. **The model never assigns a label.** You
   augment text, the rubric assigns the label.
4. **Code-mixed variants (~1,000).** Hindi, Hinglish, romanised Hindi,
   misspellings, no punctuation, ALL CAPS, voice-to-text artefacts. This is
   what real reports look like and it is your differentiator.

### Rules that keep it honest

- **Hold out the test set before you train anything.** Stratified by class.
  Lock it. Do not look at it until the end.
- **The gold set goes entirely in test**, never in train. Real text is what you
  are ultimately measured on.
- Augmented paraphrases of a seed must stay in the **same split** as their
  seed, or you leak.
- Get a second person to label 200 items independently and report
  **Cohen's kappa**. If agreement is poor, your rubric is ambiguous — fix the
  rubric, not the labels.

**Exit criterion:** a versioned dataset with a datasheet — size, sources, class
balance, splits, inter-annotator agreement, and known biases stated plainly.

---

# Month 2 — the models, and the innovation

## Week 5 · Severity classifier, done properly

### Baselines first, always

You cannot claim a transformer helped without something to beat.

| Baseline | Why |
|---|---|
| Keyword rules | your current fallback; the honest floor |
| TF-IDF + logistic regression | shockingly strong, near-zero cost |
| LLM zero-shot | what the hackathon used; the thing to beat |

### Then the real model

**Use MuRIL** (`google/muril-base-cased`) rather than DistilBERT. It is trained
on 17 Indian languages including transliterated Hindi, which is exactly your
code-mixed problem. IndicBERT is a reasonable second choice.

Choosing MuRIL over an English model **is** the technical story. Be able to
explain why, and show the ablation.

### Report these, not accuracy

Accuracy is the wrong metric for imbalanced, asymmetric-cost classes.

| Metric | Why it matters |
|---|---|
| **Macro-F1** | headline, treats rare classes fairly |
| **P1 recall** | *the* number. Missing a critical is the failure that kills someone |
| Per-class precision/recall | shows where it actually breaks |
| Confusion matrix | which classes it confuses, and whether that is dangerous |
| **Cost-weighted error** | define a matrix where P1→P4 costs far more than P4→P1 |

**Tune the decision threshold for P1 recall, not for accuracy.** A false P1
costs an operator ten seconds. A missed P1 costs a life. Say this out loud —
it shows you understand the domain, not just the library.

## Week 6 · Calibration — the thing that lost the hackathon

Do this properly and it becomes the strongest slide you own.

- Fit **temperature scaling** on a validation split
- Compute **Expected Calibration Error** before and after
- Plot a **reliability diagram** — predicted probability against observed
  frequency, with the diagonal
- Only then write `severity_probability`, and only from the calibrated model

**The slide that wins the argument:**

> *"Last time our confidence was the LLM's opinion of itself, and a blank photo
> scored 95%. Here is the same input now. Here is our reliability diagram. When
> this model says 80%, it is right about 80% of the time — measured on data it
> has never seen."*

Then show the ECE number. That is a real ML engineer's answer.

## Week 7 · Crush risk from report geometry — the innovation

The part nobody else can do. Cheap, novel, and the reason this is not just a
CRUD app.

### The idea

Reports are a spatial-temporal point process. Before a crush is *named*, the
pattern already changes.

### Features per zone, per rolling window

```
report_rate            reports per minute, this zone
rate_z_score           against that zone's own baseline for that time of day
spatial_dispersion     mean pairwise distance between recent report locations
                       (tightening = compression)
category_entropy       falling entropy = everyone reporting the same thing
category_drift         share shifting toward crowd/medical
inter_arrival_variance bursts, not steady trickle
unique_reporters       distinct fingerprints; separates one panicking person
                       from many independent people
```

### Model

Start with **a transparent scoring function, not a neural net.** You cannot get
labelled crush events at your scale, so an unsupervised or rule-shaped detector
you can explain beats a black box you cannot validate.

1. Per-zone baseline from normal operation
2. Multivariate anomaly score (robust z-scores, or an isolation forest)
3. Three states: `normal` → `watch` → `alert`
4. Every alert carries **why**: "report rate 6× baseline, dispersion halved in
   90 seconds, 80% of reports now crowd category"

### Validate honestly

You will not have real crush data. Do not pretend otherwise.

- **Simulate** using published crowd-crush dynamics; generate report streams for
  normal, gathering and crush scenarios
- Report **lead time** — how many seconds before the first explicit "crush"
  report does the detector fire?
- Report **false alert rate** on normal traffic. An alert every ten minutes gets
  ignored, which makes it worse than nothing.
- **State plainly: validated in simulation, not in a real crush.** That sentence
  earns more credibility than any claim you could make instead.

**Exit criterion:** a plot with time on the x-axis, the risk score rising, and a
marker where the first human "crush" report arrives — with the gap labelled in
seconds.

## Week 8 · Retrieval and de-duplication, measured

Two things currently asserted without evidence.

**Retrieval:** build 100 report → correct-protocol pairs. Report Recall@1,
Recall@3, MRR. Compare embedding models. Compare against keyword search. If
pgvector semantic search does not beat BM25, say so and use BM25 — that is a
legitimate, publishable result.

**De-duplication:** label ~500 report pairs as same-incident or not. Report
precision and recall. Then test whether adding text similarity to the current
category+zone+time rule actually helps. **It might not** — and demonstrating
that a simpler rule wins is a stronger result than adding a model that does not.

---

# Month 3 — product, proof, packaging

## Week 9 · Production hardening

- Rate limiting: per-fingerprint and per-IP, on the open path, **without an OTP
  wall**
- Abuse handling: an operator can mark a report false; feed that back as a
  reporter reputation signal
- Offline queueing in the reporter — service worker, IndexedDB, sync on
  reconnect. **This is what makes it work when 112 does not**, so it is worth
  the effort.
- Structured logging, request IDs, Sentry
- GitHub Actions: lint, type check, tests, migration check
- Deploy: Hetzner CX22 (~₹450/month) or Fly.io. Domain ~₹800/year. Caddy for
  TLS. **Total under ₹1,000/month.**

## Week 10 · Load and reliability evidence

Numbers you can put on a slide.

- **k6 load test**: sustained reports/second, p50/p95/p99 latency, error rate
  under load. Do a real stampede-shaped burst: 500 reports in 60 seconds.
- **Chaos**: kill the LLM, kill Redis, saturate the database. Show it degrades
  and says so.
- **Recovery**: kill Postgres mid-write; verify no incident is lost or corrupted.
- Publish results in `docs/benchmarks.md` with the exact command used.

## Week 11 · The pilot, or an honest substitute

**Try for a real one.** A college fest, a marathon, a temple event, a society
Diwali function. Even 50 real users for four hours produces something no amount
of simulation can: real messy text, real GPS behaviour, real network conditions.

Offer it free. You need the data more than they need to pay.

If nothing lands, run a **structured drill**: 20 volunteers, scripted scenarios,
2 hours, on a real campus with real GPS. Record everything. Report what broke.

**"Tested with 20 people in a live drill on a real campus"** beats
**"designed for 10,000 users"** in every conversation that matters.

## Week 12 · Package it so it can be judged

- **`docs/benchmarks.md`** — every number, with method and command
- **`ml/notebooks/`** — evaluation notebooks that run top to bottom
- **`docs/model-card.md`** — intended use, training data, metrics, **limitations
  and failure modes**, ethical considerations
- **`docs/datasheet.md`** — dataset provenance, composition, bias
- **README** with real screenshots and real numbers
- A **3-minute video** of a live drill, not a staged demo
- A **written case study**: what failed, what you measured, what you changed

---

# The numbers you should be able to quote

Fill these in as you go. This table *is* the project.

| Claim | Metric | Evidence |
|---|---|---|
| Severity is accurate | macro-F1, **P1 recall** | held-out test, gold set included |
| Confidence is meaningful | **ECE**, reliability diagram | validation, post-calibration |
| Handles Indian text | F1 on code-mixed subset vs English-only model | ablation |
| Beats an LLM | F1, latency, cost per 1k | same test set |
| Sees a crush early | **lead time (s)**, false alert rate | simulation, stated as such |
| Advice is relevant | Recall@3, MRR | 100 labelled pairs |
| Dedup works | precision, recall | 500 labelled pairs |
| Scales | reports/s, p95 latency | k6 |
| Survives failure | behaviour under LLM/Redis/DB loss | chaos runs |
| Real people used it | users, reports, issues found | drill or pilot |

---

# What to spend money on

Roughly ₹8,000–15,000 total for three months.

| Item | Cost | Verdict |
|---|---|---|
| Colab Pro | ~₹900/mo | **Yes.** MuRIL fine-tuning needs a GPU. |
| VPS (Hetzner CX22) | ~₹450/mo | **Yes**, from Week 9 |
| Domain | ~₹800/yr | **Yes.** `aegis.<something>.in` |
| LLM API credits | ~₹800 total | Yes, for augmentation and the baseline |
| Managed Postgres | ~₹1,200/mo | **No.** Run it on the VPS. |
| Paid map API | — | **No.** OSM is fine and has no billing risk. |
| Sentry | free tier | Yes |

---

# Risks, and what to do about them

| Risk | Likelihood | Mitigation |
|---|---|---|
| Dataset is weak, so the model means nothing | **High** | Do not rush weeks 3–4. Rubric first, kappa measured, gold set held out. |
| Crush detector has no real validation data | **Certain** | Simulate, state it plainly as simulation, report lead time and false alert rate. Never imply field validation. |
| Scope creep into CCTV and voice | High | Both are deferred until the severity model is calibrated. Written into `ROADMAP.md` for a reason. |
| No pilot venue says yes | Medium | Structured drill with volunteers is a valid substitute. |
| Fine-tuned model does not beat the LLM | Medium | **That is a publishable result.** Report it honestly and use the LLM with your calibration layer on top. |
| Burnout over 12 weeks | Medium | Weeks 1, 5, 9 are the load-bearing ones. Everything else can slip a week. |

---

# What "innovative and reliable" actually means here

Not more features. Three specific claims, each with evidence:

1. **"We built the first calibrated severity classifier for code-mixed Indian
   emergency reports, and here is the reliability diagram."**
2. **"We detect a forming crush from the geometry of incoming reports, N seconds
   before anyone reports a crush — something a phone-call system structurally
   cannot do."**
3. **"Every piece of advice cites a government document, and we measured
   retrieval quality rather than assuming it."**

Plus the thing that already earns respect: **it states its own limits before
being asked.** The corroboration fix, the "AI unavailable — manual mode" banner,
"validated in simulation, not in a real crush". Keep every one of those.

That is a product. The rest is scaffolding.
