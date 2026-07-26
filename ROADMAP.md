# Roadmap

Ordered by dependency, not by ambition. Each phase should leave the project in
a working state.

---

## Phase 1 — a backend we own

Replace the managed backend with a stack that runs anywhere.

- [x] Repository, licence, layout
- [ ] SQLAlchemy models: venues, zones, responders, reports, incidents, events,
      protocols, broadcasts, users
- [ ] Alembic migrations, PostGIS and pgvector enabled
- [ ] Report ingestion, with de-duplication by category, zone and time window
- [ ] Dispatch: nearest available responder whose role matches the category
- [ ] Escalation: unacknowledged P1 escalates on a timer
- [ ] Append only audit trail per incident
- [ ] WebSocket hub so every screen stays live without polling
- [ ] Photo upload to local or S3 compatible storage
- [ ] Next.js frontend for the three roles
- [ ] End to end test that mirrors the hackathon demo run

**Done when** the full demo flow works against the new stack with no managed
service involved.

---

## Phase 2 — a severity score that means something

The part the judges were right about, and the part worth putting on a CV.

- [ ] Build a labelled dataset of emergency reports across P1–P4. Start from
      public incident reports and NDMA case material, augment carefully, and
      **write down the labelling rules** so the labels are defensible
- [ ] Hold out a genuine test set before any training happens
- [ ] Baselines first: keyword rules, then TF-IDF and logistic regression, so
      there is something to beat
- [ ] Fine tune a small transformer (DistilBERT class) for severity
- [ ] Report **macro F1 and per class recall**, not accuracy. Missing a P1
      matters far more than mislabelling a P4, so recall on P1 is the number
      that counts
- [ ] Plot a **calibration curve**. A confidence score is only meaningful if
      predicted probability matches observed frequency
- [ ] Compare against LLM zero shot on the same test set, honestly, including
      latency and cost
- [ ] Serve the model in the API and show the calibrated probability in the UI
- [ ] Publish the evaluation notebook in `ml/`

**Done when** the number on screen is one that can be defended with a plot.

**Note:** this needs Python 3.11 or 3.12. PyTorch and transformers do not
publish wheels for 3.14 yet.

---

## Phase 3 — something a venue could actually run

- [ ] Real authentication with roles, replacing the shared passcode
- [ ] Rate limiting and abuse controls on the open reporting path, without
      putting an OTP wall in front of someone in danger
- [ ] Offline queueing on the reporter, syncing when signal returns
- [ ] Real facility data from data.gov.in and OpenStreetMap rather than
      hand placed coordinates
- [ ] Formal escalation path to 112
- [ ] Monitoring, structured logs, CI
- [ ] Load testing with published numbers

---

## Deliberately out of scope for now

Vision verification of incident photographs, crowd density estimation from
CCTV, and voice reporting are all interesting and all sit behind the severity
model. Doing them before Phase 2 would repeat the original mistake: shipping
something that looks intelligent without being measured.
