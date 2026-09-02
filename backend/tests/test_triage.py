"""Rules based triage.

Most of these need no database: assess() is a pure function, and keeping it
that way is what makes the rules cheap to argue about and cheap to replace
when a trained classifier arrives.
"""
import pytest
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db import SessionLocal
from app.main import app
from app.models import (
    Category, Event, Incident, Report, Responder, User, UserRole, Venue, Zone,
)
from app.services.triage import BASELINE, assess

SLUG = "triage-ground"
OP = "op@triage.example"
PW = "TriagePass2026"


# --------------------------------------------------------------- pure rules
def test_baseline_applies_when_there_is_no_text():
    for category, expected in BASELINE.items():
        assert assess(category, None).priority == expected


def test_empty_description_is_the_same_as_none():
    assert assess(Category.medical, "").priority == \
        assess(Category.medical, None).priority


@pytest.mark.parametrize("text", [
    "he is not breathing",
    "aunty ko saans nahi aa raha",
    "person is unconscious near gate 3",
    "bhai gate 3 pe bhagdad ho rahi hai",
    "someone is trapped under the barrier",
    "there is a knife",
    "lost child near the stage",
])
def test_life_threatening_phrases_reach_p1(text):
    assert assess(Category.other, text).priority == 1


@pytest.mark.parametrize("text", [
    "someone is injured",
    "woh gir gaya hai",
    "a fight has started",
    "bahut dhakka ho raha hai",
])
def test_urgent_phrases_reach_p2(text):
    assert assess(Category.other, text).priority <= 2


def test_a_rule_never_lowers_urgency_below_the_category():
    """Fire is P1 by category. No amount of calm wording may soften it."""
    calm = assess(Category.fire, "small bin smouldering, nothing serious")
    assert calm.priority == 1


def test_word_boundaries_stop_false_matches():
    """'fire' must not fire on 'fireworks stall', which is a normal thing to
    have at a venue and not a report of a fire."""
    assert assess(Category.other, "asking about the fireworks stall").priority \
        == BASELINE[Category.other]
    assert assess(Category.other, "carrying a gunny sack").priority \
        == BASELINE[Category.other]


def test_reason_is_recorded_and_readable():
    out = assess(Category.medical, "she is unconscious")
    assert out.priority == 1
    assert "unconscious" in out.reason.lower()
    assert out.headline.startswith("Medical")


def test_harassment_has_its_own_baseline():
    """It must not fall back to the generic default: a personal safety report
    is more urgent than "other", which is what it used to be filed as."""
    from app.models import Category as C
    assert BASELINE[C.harassment] == 2
    assert assess(C.harassment, None).priority == 2
    assert assess(C.harassment, None).headline.startswith("Harassment")


@pytest.mark.parametrize("text", [
    "someone is following me",
    "a man is harassing me near the stage",
    "koi peecha kar raha hai",
])
def test_distress_wording_is_recognised(text):
    from app.models import Category as C
    out = assess(C.harassment, text)
    assert out.priority <= 2
    assert "distress" in out.reason


def test_corroboration_raises_urgency():
    one = assess(Category.crowd, "a lot of pushing", report_count=1)
    many = assess(Category.crowd, "a lot of pushing", report_count=4)
    assert many.priority < one.priority
    assert "independent reports" in many.reason


def test_corroboration_cannot_go_below_p1():
    out = assess(Category.fire, "aag lag gayi", report_count=9)
    assert out.priority == 1


# ------------------------------------------------------------- through http
@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    yield s
    s.close()


def _purge(db):
    old = db.execute(select(Venue).where(Venue.slug == SLUG)).scalar_one_or_none()
    if old:
        ids = [i.id for i in db.execute(
            select(Incident).where(Incident.venue_id == old.id)).scalars()]
        if ids:
            db.execute(delete(Event).where(Event.incident_id.in_(ids)))
        db.execute(delete(Report).where(Report.venue_id == old.id))
        db.execute(delete(Incident).where(Incident.venue_id == old.id))
        db.execute(delete(Responder).where(Responder.venue_id == old.id))
        db.execute(delete(User).where(User.venue_id == old.id))
        db.execute(delete(Zone).where(Zone.venue_id == old.id))
        db.execute(delete(Venue).where(Venue.id == old.id))
    db.commit()


@pytest.fixture(scope="module")
def client(db):
    from fastapi.testclient import TestClient
    _purge(db)
    v = Venue(name="Triage Ground", slug=SLUG,
              centre="SRID=4326;POINT(77.1216 28.5921)")
    db.add(v)
    db.flush()
    db.add(Zone(venue_id=v.id, name="Gate 1", is_exit=True,
                location="SRID=4326;POINT(77.1210 28.5925)"))
    db.add(User(email=OP, password_hash=hash_password(PW),
                display_name="Op", role=UserRole.operator, venue_id=v.id))
    db.commit()
    yield TestClient(app)
    _purge(db)
    db.commit()


@pytest.fixture(scope="module")
def op(client):
    r = client.post("/api/auth/login", json={"email": OP, "password": PW})
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def _file(client, category, description=None, **extra):
    body = {"venue_slug": SLUG, "category": category,
            "lat": 28.5925, "lng": 77.1210}
    if description:
        body["description"] = description
    body.update(extra)
    r = client.post("/api/reports", json=body)
    assert r.status_code == 201, r.text
    return r.json()


def test_incident_arrives_already_triaged(client, op, db):
    import uuid as _u
    made = _file(client, "medical", "patient is not breathing")
    inc = db.get(Incident, _u.UUID(made["incident_id"]))
    db.refresh(inc)
    assert inc.priority == 1
    assert inc.triage_source == "rules"
    # a rule is not a calibrated probability, so none is published
    assert inc.severity_probability is None


def test_the_reason_reaches_the_audit_trail(client, op):
    made = _file(client, "violence", "there is a fight near gate 1")
    events = client.get(f"/api/incidents/{made['incident_id']}/events",
                        headers=op).json()
    assert any("Triaged P" in e["message"] for e in events)


def test_harassment_report_survives_the_round_trip(client, op, db):
    """The category exists in the enum, so a report of this kind keeps its
    identity instead of being filed as other."""
    import uuid as _u
    made = _file(client, "harassment", "someone is following me near gate 1")
    inc = db.get(Incident, _u.UUID(made["incident_id"]))
    db.refresh(inc)
    assert inc.category.value == "harassment"
    assert inc.priority == 2

    feed = client.get("/api/incidents", headers=op).json()
    assert any(i["category"] == "harassment" for i in feed)


def test_operator_override_outranks_the_rules(client, op, db):
    import uuid as _u
    made = _file(client, "other", "someone asking for directions")
    iid = made["incident_id"]
    r = client.post(f"/api/incidents/{iid}/priority", headers=op,
                    json={"priority": 1, "reason": "radio says it is worse"})
    assert r.status_code == 200
    body = r.json()
    assert body["priority"] == 1
    assert body["triage_source"] == "operator"

    events = client.get(f"/api/incidents/{iid}/events", headers=op).json()
    assert any("by operator" in e["message"] for e in events)

    inc = db.get(Incident, _u.UUID(iid))
    db.refresh(inc)
    assert inc.triage_source == "operator"


def test_override_requires_a_reason(client, op):
    made = _file(client, "other", "nothing much")
    r = client.post(f"/api/incidents/{made['incident_id']}/priority",
                    headers=op, json={"priority": 1})
    assert r.status_code == 422


def test_override_rejects_a_priority_outside_the_scale(client, op):
    made = _file(client, "other", "still nothing")
    r = client.post(f"/api/incidents/{made['incident_id']}/priority",
                    headers=op, json={"priority": 9, "reason": "typo"})
    assert r.status_code == 422
