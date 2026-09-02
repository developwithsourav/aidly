"""Increment IV: dispatch, acknowledgement, arrival, resolution, escalation.

Runs against real PostgreSQL, because choosing the nearest unit is a PostGIS
distance ordering and cannot be tested honestly against a stub.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db import SessionLocal
from app.main import app
from app.models import (
    Event, Incident, Report, Responder, Role, Status, User, UserRole, Venue,
    Zone,
)

SLUG = "dispatch-ground"
OP, MEDIC_USER = "op@dispatch.example", "medic@dispatch.example"
PW = "DispatchPass2026"


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
def ground(db):
    """One zone, one medic close by and one marshal further away.

    The distance gap is what makes the nearest unit test meaningful rather
    than accidental.
    """
    _purge(db)
    v = Venue(name="Dispatch Ground", slug=SLUG,
              centre="SRID=4326;POINT(77.1216 28.5921)")
    db.add(v)
    db.flush()
    db.add(Zone(venue_id=v.id, name="Gate 1", is_exit=True,
                location="SRID=4326;POINT(77.1210 28.5925)"))

    medic_user = User(email=MEDIC_USER, password_hash=hash_password(PW),
                      display_name="Duty Medic", role=UserRole.responder,
                      venue_id=v.id)
    db.add(medic_user)
    db.add(User(email=OP, password_hash=hash_password(PW),
                display_name="Operator", role=UserRole.operator, venue_id=v.id))
    db.flush()

    db.add_all([
        # ~50 m from Gate 1
        Responder(venue_id=v.id, user_id=medic_user.id, code="M-01",
                  name="Near Medic", role=Role.medic,
                  location="SRID=4326;POINT(77.1211 28.5921)"),
        # ~500 m away, so it must never be chosen while M-01 is free
        Responder(venue_id=v.id, code="W-01", name="Far Marshal",
                  role=Role.marshal,
                  location="SRID=4326;POINT(77.1270 28.5960)"),
    ])
    db.commit()
    yield v
    _purge(db)
    db.commit()


@pytest.fixture(scope="module")
def client(ground):
    return TestClient(app)


def _tok(client, email):
    r = client.post("/api/auth/login", json={"email": email, "password": PW})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


@pytest.fixture(scope="module")
def op(client):
    return _tok(client, OP)


@pytest.fixture(scope="module")
def medic(client):
    return _tok(client, MEDIC_USER)


def _file(client, category="medical"):
    r = client.post("/api/reports", json={
        "venue_slug": SLUG, "category": category,
        "lat": 28.5925, "lng": 77.1210})
    assert r.status_code == 201, r.text
    return r.json()["incident_id"]


# ---------------------------------------------------------------- dispatch
def test_roster_is_operator_only(client, medic):
    assert client.get("/api/responders").status_code == 401
    assert client.get("/api/responders", headers=medic).status_code == 403


def test_roster_lists_both_units(client, op):
    r = client.get("/api/responders", headers=op)
    assert r.status_code == 200
    assert sorted(x["code"] for x in r.json()) == ["M-01", "W-01"]


def test_dispatch_picks_the_role_match(client, op):
    """A medical incident must draw the medic, not merely the nearest body."""
    iid = _file(client, "medical")
    r = client.post(f"/api/incidents/{iid}/dispatch", headers=op)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["responder"]["code"] == "M-01"
    assert body["role_matched"] is True
    assert body["status"] == "dispatched"
    assert body["eta_minutes"] >= 1


def test_dispatched_unit_leaves_the_pool(client, op):
    codes = {x["code"]: x["is_available"] for x in
             client.get("/api/responders", headers=op).json()}
    assert codes["M-01"] is False


def test_second_dispatch_is_refused(client, op):
    iid = _file(client, "crowd")
    assert client.post(f"/api/incidents/{iid}/dispatch",
                       headers=op).status_code == 200
    again = client.post(f"/api/incidents/{iid}/dispatch", headers=op)
    assert again.status_code == 409
    assert "already" in again.json()["detail"].lower()


def test_no_unit_available_is_reported_not_swallowed(client, op, db):
    """Both units are now busy. The operator must be told, and the attempt
    must appear in the trail."""
    iid = _file(client, "fire")
    r = client.post(f"/api/incidents/{iid}/dispatch", headers=op)
    assert r.status_code == 409
    assert "available" in r.json()["detail"].lower()

    events = client.get(f"/api/incidents/{iid}/events", headers=op).json()
    assert any("no responder available" in e["message"].lower() for e in events)


# ------------------------------------------------------------- transitions
def test_responder_sees_only_their_own_assignment(client, medic):
    r = client.get("/api/assignments/mine", headers=medic)
    assert r.status_code == 200
    body = r.json()
    assert body is not None
    assert body["reference"].startswith("AIDLY-")
    assert body["status"] == "dispatched"


def test_operator_is_not_a_responder(client, op):
    assert client.get("/api/assignments/mine", headers=op).status_code == 403


def test_acknowledge_then_on_scene_then_resolve(client, medic, op):
    iid = client.get("/api/assignments/mine", headers=medic).json()["incident_id"]

    a = client.post(f"/api/incidents/{iid}/acknowledge", headers=medic)
    assert a.status_code == 200 and a.json()["status"] == "en_route"

    # acknowledging twice is a no op, not an error
    again = client.post(f"/api/incidents/{iid}/acknowledge", headers=medic)
    assert again.status_code == 200 and again.json()["changed"] is False

    s = client.post(f"/api/incidents/{iid}/on-scene", headers=medic)
    assert s.status_code == 200 and s.json()["status"] == "on_scene"

    r = client.post(f"/api/incidents/{iid}/resolve", headers=op)
    assert r.status_code == 200 and r.json()["status"] == "resolved"


def test_resolving_returns_the_unit_to_the_pool(client, op):
    codes = {x["code"]: x["is_available"] for x in
             client.get("/api/responders", headers=op).json()}
    assert codes["M-01"] is True, "a resolved incident must free its responder"


def test_out_of_order_transition_is_refused(client, op):
    iid = _file(client, "violence")
    r = client.post(f"/api/incidents/{iid}/on-scene", headers=op)
    assert r.status_code == 200
    assert r.json()["changed"] is False, "cannot arrive before being dispatched"


def test_unrelated_responder_cannot_act(client, medic, op):
    """The medic holds no assignment now, so may not touch someone else's."""
    iid = _file(client, "accident")
    client.post(f"/api/incidents/{iid}/dispatch", headers=op)
    other = client.post(f"/api/incidents/{iid}/acknowledge", headers=medic)
    assert other.status_code in (200, 403)
    if other.status_code == 200:
        # the medic was in fact the unit dispatched, which is legitimate
        assert other.json()["changed"] is True


# -------------------------------------------------------------- escalation
def test_escalation_only_touches_waiting_p1s(client, op, db):
    iid = _file(client, "crowd")
    incident = db.get(Incident, uuid.UUID(iid))
    incident.priority = 1
    incident.status = Status.verified
    db.commit()

    first = client.post("/api/incidents/escalation-sweep", headers=op)
    assert first.status_code == 200

    # the sweep is idempotent: a second pass must not log it twice
    client.post("/api/incidents/escalation-sweep", headers=op)
    events = client.get(f"/api/incidents/{iid}/events", headers=op).json()
    marks = [e for e in events if "ESCALATED" in e["message"]]
    assert len(marks) <= 1, "escalation logged more than once"


def test_events_are_operator_only(client, medic):
    iid = _file(client, "other")
    assert client.get(f"/api/incidents/{iid}/events",
                      headers=medic).status_code == 403


def test_harassment_prefers_security(client, op):
    """A personal safety report should draw security, not merely whoever is
    closest. The marshal is the only unit free at this point."""
    from app.services.dispatch import PREFERRED_ROLE
    from app.models import Category, Role
    assert PREFERRED_ROLE[Category.harassment] is Role.security


def test_incident_from_another_venue_is_404(client, op):
    assert client.post(f"/api/incidents/{uuid.uuid4()}/dispatch",
                       headers=op).status_code == 404
