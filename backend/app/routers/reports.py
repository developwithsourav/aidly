"""Report intake and the control room incident feed.

Two audiences with opposite requirements meet in this module.

Filing a report is public: an attendee in an emergency cannot be asked to hold
an account, so POST /api/reports carries no authentication at all. Reading the
incident feed is the opposite, because it exposes where every incident in the
venue is and who has been sent to it, so every read is behind an operator
token.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db import get_db
from app.models import Incident, Status, User, UserRole, Venue, Zone
from app.routers.auth import current_user
from app.schemas.reports import (
    IncidentOut, ReportAccepted, ReportCreate, VenueOut, reference_for,
)
from app.services.ingest import ingest_report

router = APIRouter(prefix="/api", tags=["reports"])

OPEN_STATUSES = (
    Status.triaging, Status.verified, Status.dispatched,
    Status.en_route, Status.on_scene,
)


def _venue_or_404(db: Session, slug: str) -> Venue:
    venue = db.execute(
        select(Venue).where(Venue.slug == slug, Venue.is_active.is_(True))
    ).scalar_one_or_none()
    if venue is None:
        raise HTTPException(status_code=404, detail="Unknown venue")
    return venue


def _to_out(db: Session, incident: Incident) -> IncidentOut:
    """Builds the response for one incident.

    The zone name is looked up rather than joined because an incident may have
    no zone at all: a report filed with no position and no gate selected is
    still a valid report, and must still be readable by the control room.
    """
    zone_name = None
    if incident.zone_id:
        zone = db.get(Zone, incident.zone_id)
        zone_name = zone.name if zone else None
    return IncidentOut(
        id=incident.id,
        reference=reference_for(incident.id),
        category=incident.category,
        status=incident.status,
        priority=incident.priority,
        headline=incident.headline,
        zone=zone_name,
        report_count=incident.report_count,
        corroboration=incident.corroboration,
        triage_source=incident.triage_source,
        severity_probability=incident.severity_probability,
        created_at=incident.created_at,
    )


# ------------------------------------------------------------------ public
@router.get("/venues/{slug}", response_model=VenueOut)
def venue_detail(slug: str, db: Session = Depends(get_db)) -> Venue:
    """The reporting screen calls this before anything else.

    It needs the zone list up front so that the gate fallback is already on
    screen when the browser refuses a position, rather than being fetched at
    the moment the reporter is least able to wait for it.
    """
    venue = db.execute(
        select(Venue)
        .where(Venue.slug == slug, Venue.is_active.is_(True))
        .options(selectinload(Venue.zones))
    ).scalar_one_or_none()
    if venue is None:
        raise HTTPException(status_code=404, detail="Unknown venue")
    return venue


@router.post("/reports", response_model=ReportAccepted,
             status_code=status.HTTP_201_CREATED)
def create_report(payload: ReportCreate,
                  db: Session = Depends(get_db)) -> ReportAccepted:
    """File one report. Deliberately unauthenticated.

    Everything optional stays optional here. The service resolves a zone from
    the position, or from the gate the reporter chose, or falls back to the
    venue centre, so no combination of missing inputs can reject the report.
    """
    venue = _venue_or_404(db, payload.venue_slug)

    incident, merged = ingest_report(
        db,
        venue=venue,
        category=payload.category,
        description=payload.description,
        lat=payload.lat,
        lng=payload.lng,
        zone_id=payload.zone_id,
        callback_phone=payload.callback_phone,
        photo_key=payload.photo_key,
    )

    zone_name = None
    if incident.zone_id:
        zone = db.get(Zone, incident.zone_id)
        zone_name = zone.name if zone else None

    return ReportAccepted(
        incident_id=incident.id,
        reference=reference_for(incident.id),
        merged=merged,
        report_count=incident.report_count,
        status=incident.status,
        zone=zone_name,
        message=("Your report was added to one already being handled."
                 if merged else "Your report has been received."),
    )


# --------------------------------------------------------------- protected
def _operator(user: User = Depends(current_user)) -> User:
    """Reading the feed requires an operator or an administrator.

    A responder is authenticated but is deliberately not allowed here: they are
    told about their own assignment, not about every incident in the venue.
    """
    if user.role not in (UserRole.operator, UserRole.admin):
        raise HTTPException(status_code=403, detail="Operator access required")
    return user


@router.get("/incidents", response_model=list[IncidentOut])
def incident_feed(
    open_only: bool = Query(True, description="Hide resolved incidents"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: User = Depends(_operator),
) -> list[IncidentOut]:
    """The control room feed, scoped to the operator's own venue.

    The scope is taken from the account rather than from a query parameter, so
    one venue's operator cannot read another venue's ground by editing a URL.
    """
    if user.venue_id is None:
        raise HTTPException(status_code=403,
                            detail="Account is not attached to a venue")

    stmt = select(Incident).where(Incident.venue_id == user.venue_id)
    if open_only:
        stmt = stmt.where(Incident.status.in_(OPEN_STATUSES))
    stmt = stmt.order_by(Incident.priority.asc(),
                         Incident.created_at.desc()).limit(limit)

    return [_to_out(db, i) for i in db.execute(stmt).scalars()]


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
def incident_detail(incident_id: uuid.UUID,
                    db: Session = Depends(get_db),
                    user: User = Depends(_operator)) -> IncidentOut:
    incident = db.get(Incident, incident_id)
    # An incident belonging to another venue is reported as absent rather than
    # forbidden, so the response cannot be used to discover that it exists.
    if incident is None or incident.venue_id != user.venue_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _to_out(db, incident)
