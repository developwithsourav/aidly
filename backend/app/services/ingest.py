"""Report ingestion: resolve a location to a zone, then merge or create.

This is the one path that must never fail. A person in danger has tapped a
button; every branch here either records something useful or degrades to
something useful. Nothing in this module may raise on a missing optional field.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from geoalchemy2.functions import ST_Distance, ST_SetSRID
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Category, Event, Incident, Report, Status, Venue, Zone, utcnow

settings = get_settings()


def _point(lat: float, lng: float):
    """A PostGIS geography point. Note the order: WKT is (lng lat), not (lat lng)."""
    return ST_SetSRID(func.ST_MakePoint(lng, lat), 4326)


def resolve_zone(
    db: Session, venue_id: uuid.UUID, lat: float | None, lng: float | None,
    zone_id: uuid.UUID | None = None,
) -> Zone | None:
    """Pick the zone a report belongs to.

    An explicitly chosen zone always wins: if the reporter told us where they
    are, we believe them over a GPS fix that may be twenty metres out or denied
    outright. Otherwise take the nearest zone by true geographic distance.
    """
    if zone_id is not None:
        return db.get(Zone, zone_id)

    if lat is None or lng is None:
        return None

    return db.scalars(
        select(Zone)
        .where(Zone.venue_id == venue_id)
        .order_by(ST_Distance(Zone.location, _point(lat, lng)))
        .limit(1)
    ).first()


def find_duplicate(
    db: Session, venue_id: uuid.UUID, category: Category, zone: Zone | None,
) -> Incident | None:
    """An open incident describing the same thing, in the same place, just now.

    Deliberately conservative: same venue, same category, same zone, inside the
    de-duplication window, and not yet resolved. Merging two genuinely separate
    emergencies is far worse than showing one twice, so this errs towards
    creating a new incident.

    A report with no zone is never merged, because "somewhere in the venue" is
    not evidence that two reports describe one event.
    """
    if zone is None:
        return None

    cutoff = utcnow() - timedelta(seconds=settings.dedup_window_seconds)
    return db.scalars(
        select(Incident)
        .where(
            Incident.venue_id == venue_id,
            Incident.category == category,
            Incident.zone_id == zone.id,
            Incident.status != Status.resolved,
            Incident.created_at >= cutoff,
        )
        .order_by(Incident.created_at.desc())
        .limit(1)
    ).first()


def ingest_report(
    db: Session,
    *,
    venue: Venue,
    category: Category,
    description: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    zone_id: uuid.UUID | None = None,
    callback_phone: str | None = None,
    photo_key: str | None = None,
    fingerprint: str | None = None,
) -> tuple[Incident, bool]:
    """Record a report. Returns the incident and whether it merged into one.

    Location falls back in three steps so a report is never rejected: the GPS
    fix, then the zone the reporter picked, then the venue centre. Somewhere
    approximate beats nothing at all.
    """
    zone = resolve_zone(db, venue.id, lat, lng, zone_id)

    if lat is not None and lng is not None:
        location = _point(lat, lng)
    elif zone is not None:
        location = zone.location
    else:
        location = venue.centre

    existing = find_duplicate(db, venue.id, category, zone)

    if existing is not None:
        existing.report_count += 1
        db.add(Report(
            incident_id=existing.id, venue_id=venue.id, category=category,
            description=description, callback_phone=callback_phone,
            location=location, photo_key=photo_key, reporter_fingerprint=fingerprint,
        ))
        db.add(Event(
            incident_id=existing.id, actor="system",
            message=f"Duplicate report merged, now {existing.report_count} independent reports",
        ))
        db.flush()
        return existing, True

    incident = Incident(
        venue_id=venue.id,
        zone_id=zone.id if zone else None,
        category=category,
        status=Status.triaging,
        location=location,
        headline=f"{category.value.title()} reported",
        # priority stays at its default until triage runs. It is not a guess
        # dressed up as a result, and severity_probability stays NULL.
    )
    db.add(incident)
    db.flush()

    db.add(Report(
        incident_id=incident.id, venue_id=venue.id, category=category,
        description=description, callback_phone=callback_phone,
        location=location, photo_key=photo_key, reporter_fingerprint=fingerprint,
    ))
    db.add(Event(incident_id=incident.id, actor="system", message="Report received"))
    db.flush()
    return incident, False
