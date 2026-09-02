"""Increment II: report intake, zone resolution and the incident feed.

These run against a real PostgreSQL database with PostGIS, because the zone
resolution and the de-duplication window are both database behaviour. A fake
in memory database would test the wrong thing.
"""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.db import SessionLocal
from app.main import app
from app.models import (
    Category, Event, Incident, Report, Responder, Status, User, UserRole,
    Venue, Zone,
)

SLUG = "test-ground"
OPERATOR = "operator@test.example"
PASSWORD = "TestPassword2026"


@pytest.fixture(scope="module")
def db():
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture(scope="module")
def venue(db):
    """A venue with two gates, torn down afterwards so runs stay repeatable."""
    _purge(db)
    v = Venue(name="Test Ground", slug=SLUG,
              centre="SRID=4326;POINT(77.1216 28.5921)")
    db.add(v)
    db.flush()
    db.add_all([
        Zone(venue_id=v.id, name="Gate 1", is_exit=True,
             location="SRID=4326;POINT(77.1210 28.5925)"),
        Zone(venue_id=v.id, name="Gate 2", is_exit=True,
             location="SRID=4326;POINT(77.1230 28.5910)"),
    ])
    db.add(User(email=OPERATOR, password_hash=hash_password(PASSWORD),
                display_name="Test Operator", role=UserRole.operator,
                venue_id=v.id))
    db.commit()
    yield v
    _purge(db)
    db.commit()


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
def client(venue):
    return TestClient(app)


@pytest.fixture(scope="module")
def token(client):
    r = client.post("/api/auth/login",
                    json={"email": OPERATOR, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _post(client, **over):
    body = {"venue_slug": SLUG, "category": "medical"}
    body.update(over)
    return client.post("/api/reports", json=body)


# ------------------------------------------------------------------ intake
def test_venue_exposes_its_gates(client):
    r = client.get(f"/api/venues/{SLUG}")
    assert r.status_code == 200
    names = sorted(z["name"] for z in r.json()["zones"])
    assert names == ["Gate 1", "Gate 2"]


def test_unknown_venue_is_404(client):
    assert client.get("/api/venues/no-such-ground").status_code == 404


def test_report_with_position_resolves_to_nearest_gate(client):
    r = _post(client, lat=28.5925, lng=77.1210)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["zone"] == "Gate 1"
    assert body["merged"] is False
    assert body["reference"].startswith("AIDLY-")


def test_report_without_position_is_still_accepted(client):
    """NFR 02 and NFR 03: no optional input may block a submission."""
    r = _post(client, category="fire")
    assert r.status_code == 201, r.text
    assert r.json()["merged"] is False


def test_gate_only_report_is_accepted(client):
    """The other fallback: a gate chosen, no position at all.

    Uses a category and gate no other test in this module uses, because every
    report here lands inside the de-duplication window and would otherwise
    merge with its neighbour.
    """
    zones = client.get(f"/api/venues/{SLUG}").json()["zones"]
    gate2 = next(z for z in zones if z["name"] == "Gate 2")
    r = _post(client, category="fire", zone_id=gate2["id"])
    assert r.status_code == 201, r.text
    assert r.json()["zone"] == "Gate 2"


def test_reporter_chosen_gate_beats_gps(client):
    """A reporter who names their gate is believed over a position fix."""
    zones = client.get(f"/api/venues/{SLUG}").json()["zones"]
    gate2 = next(z for z in zones if z["name"] == "Gate 2")
    r = _post(client, category="crowd", zone_id=gate2["id"],
              lat=28.5925, lng=77.1210)          # coordinates say Gate 1
    assert r.status_code == 201
    assert r.json()["zone"] == "Gate 2"


def test_second_report_of_same_event_merges(client):
    """FR 10. Same category, same zone, inside the window."""
    first = _post(client, category="violence", lat=28.5925, lng=77.1210).json()
    second = _post(client, category="violence", lat=28.5925, lng=77.1210).json()
    assert second["merged"] is True
    assert second["incident_id"] == first["incident_id"]
    assert second["report_count"] == first["report_count"] + 1


def test_different_category_does_not_merge(client):
    a = _post(client, category="accident", lat=28.5925, lng=77.1210).json()
    b = _post(client, category="other", lat=28.5925, lng=77.1210).json()
    assert b["incident_id"] != a["incident_id"]
    assert b["merged"] is False


def test_description_over_budget_is_rejected(client):
    r = _post(client, description="x" * 151)
    assert r.status_code == 422


def test_callback_number_keeps_only_digits(client, db):
    r = _post(client, category="medical", callback_phone="+91 98110 44044",
              lat=28.5910, lng=77.1230)
    assert r.status_code == 201
    stored = db.execute(
        select(Report).order_by(Report.created_at.desc()).limit(1)
    ).scalar_one()
    assert stored.callback_phone == "919811044044"


def test_report_to_unknown_venue_is_404(client):
    r = client.post("/api/reports",
                    json={"venue_slug": "no-such-ground", "category": "fire"})
    assert r.status_code == 404


# -------------------------------------------------------------------- feed
def test_feed_requires_a_token(client):
    assert client.get("/api/incidents").status_code == 401


def test_feed_lists_the_venue_incidents(client, token):
    r = client.get("/api/incidents",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body, "expected the reports filed above to appear"
    assert all(i["reference"].startswith("AIDLY-") for i in body)
    # severity is honest: nothing has been scored by a trained model yet
    assert all(i["severity_probability"] is None for i in body)


def test_incident_detail_round_trips(client, token):
    feed = client.get("/api/incidents",
                      headers={"Authorization": f"Bearer {token}"}).json()
    one = feed[0]
    r = client.get(f"/api/incidents/{one['id']}",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["reference"] == one["reference"]


def test_incident_from_another_venue_is_404(client, token):
    r = client.get(f"/api/incidents/{uuid.uuid4()}",
                   headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
