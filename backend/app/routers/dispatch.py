"""Dispatch, acknowledgement, arrival, resolution and escalation.

Increment IV. Every route here changes the state of an incident, so each one
records why in the append only trail rather than only what.

Who may do what:

* an operator or administrator dispatches, resolves, and reads the roster,
* the responder holding the assignment acknowledges and reports arrival,
* an operator may do those on a responder's behalf, because a radio call is
  still how most of this happens on the ground.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Event, Incident, Responder, User, UserRole
from app.routers.auth import current_user
from app.schemas.dispatch import (
    AssignmentOut, DispatchResult, EventOut, PriorityOverride, ResponderOut,
    StatusChange, TriageOut,
)
from app.schemas.reports import reference_for
from app.services import dispatch as svc

router = APIRouter(prefix="/api", tags=["dispatch"])


def _operator(user: User = Depends(current_user)) -> User:
    if user.role not in (UserRole.operator, UserRole.admin):
        raise HTTPException(status_code=403, detail="Operator access required")
    return user


def _incident_for(db: Session, incident_id: uuid.UUID, user: User) -> Incident:
    """An incident belonging to another venue is reported as absent, so the
    response cannot be used to discover that it exists."""
    incident = db.get(Incident, incident_id)
    if incident is None or incident.venue_id != user.venue_id:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


def _my_responder(db: Session, user: User) -> Responder | None:
    return db.execute(
        select(Responder).where(Responder.user_id == user.id)
    ).scalar_one_or_none()


def _may_act_on(db: Session, incident: Incident, user: User) -> bool:
    """The assigned responder, or any operator or administrator."""
    if user.role in (UserRole.operator, UserRole.admin):
        return True
    me = _my_responder(db, user)
    return me is not None and incident.assigned_responder_id == me.id


# ------------------------------------------------------------------ roster
@router.get("/responders", response_model=list[ResponderOut])
def roster(db: Session = Depends(get_db),
           user: User = Depends(_operator)) -> list[Responder]:
    if user.venue_id is None:
        raise HTTPException(status_code=403,
                            detail="Account is not attached to a venue")
    return list(db.execute(
        select(Responder)
        .where(Responder.venue_id == user.venue_id)
        .order_by(Responder.code)
    ).scalars())


# ---------------------------------------------------------------- dispatch
@router.post("/incidents/{incident_id}/dispatch", response_model=DispatchResult)
def dispatch_incident(incident_id: uuid.UUID,
                      db: Session = Depends(get_db),
                      user: User = Depends(_operator)) -> DispatchResult:
    """Send the nearest suitable unit.

    Two failures are reported distinctly, because they need different actions
    from the operator. An incident that already has a unit is a 409 telling
    them it is handled. No unit free at all is a 409 telling them to widen the
    net or call for outside help, and that attempt is recorded in the trail.
    """
    incident = _incident_for(db, incident_id, user)

    if incident.assigned_responder_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Incident already has a responder assigned")

    preferred = svc.PREFERRED_ROLE.get(incident.category)
    result = svc.dispatch_nearest(db, incident)
    if result is None:
        # dispatch_nearest has already written the failed attempt to the trail
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No responder is available at this venue")

    responder, eta = result
    db.commit()
    return DispatchResult(
        incident_id=incident.id,
        status=incident.status,
        responder=ResponderOut.model_validate(responder),
        eta_minutes=eta,
        role_matched=bool(preferred and responder.role == preferred),
    )


def _transition(db: Session, incident: Incident, changed: bool,
                done: str, already: str) -> StatusChange:
    if changed:
        db.commit()
    return StatusChange(
        incident_id=incident.id, status=incident.status,
        changed=changed, message=done if changed else already,
    )


@router.post("/incidents/{incident_id}/acknowledge", response_model=StatusChange)
def acknowledge(incident_id: uuid.UUID,
                db: Session = Depends(get_db),
                user: User = Depends(current_user)) -> StatusChange:
    """The responder has accepted and is moving. Stops the escalation timer."""
    incident = _incident_for(db, incident_id, user)
    if not _may_act_on(db, incident, user):
        raise HTTPException(status_code=403,
                            detail="Not the responder for this incident")
    return _transition(db, incident, svc.acknowledge(db, incident),
                       "Acknowledged, en route",
                       "Incident is not awaiting acknowledgement")


@router.post("/incidents/{incident_id}/on-scene", response_model=StatusChange)
def on_scene(incident_id: uuid.UUID,
             db: Session = Depends(get_db),
             user: User = Depends(current_user)) -> StatusChange:
    incident = _incident_for(db, incident_id, user)
    if not _may_act_on(db, incident, user):
        raise HTTPException(status_code=403,
                            detail="Not the responder for this incident")
    return _transition(db, incident, svc.mark_on_scene(db, incident),
                       "Marked on scene", "Incident is not en route")


@router.post("/incidents/{incident_id}/resolve", response_model=StatusChange)
def resolve(incident_id: uuid.UUID,
            db: Session = Depends(get_db),
            user: User = Depends(current_user)) -> StatusChange:
    """Close the incident and return the unit to the pool."""
    incident = _incident_for(db, incident_id, user)
    if not _may_act_on(db, incident, user):
        raise HTTPException(status_code=403,
                            detail="Not the responder for this incident")
    actor = "operator" if user.role in (UserRole.operator,
                                        UserRole.admin) else "responder"
    return _transition(db, incident, svc.resolve(db, incident, actor=actor),
                       "Resolved", "Incident is already resolved")


# --------------------------------------------------------------- responder
@router.get("/assignments/mine", response_model=AssignmentOut | None)
def my_assignment(db: Session = Depends(get_db),
                  user: User = Depends(current_user)) -> AssignmentOut | None:
    """A responder is told about their own job and nothing else.

    Returns null rather than 404 when there is no assignment: having nothing to
    do is a normal state, not an error.
    """
    me = _my_responder(db, user)
    if me is None:
        raise HTTPException(status_code=403,
                            detail="Account is not a responder")

    incident = db.execute(
        select(Incident)
        .where(Incident.assigned_responder_id == me.id,
               Incident.resolved_at.is_(None))
        .order_by(Incident.created_at.desc())
        .limit(1)
    ).scalar_one_or_none()
    if incident is None:
        return None

    zone_name = None
    if incident.zone_id:
        from app.models import Zone
        zone = db.get(Zone, incident.zone_id)
        zone_name = zone.name if zone else None

    latest = incident.reports[-1] if incident.reports else None
    return AssignmentOut(
        incident_id=incident.id,
        reference=reference_for(incident.id),
        category=incident.category.value,
        zone=zone_name,
        status=incident.status,
        priority=incident.priority,
        description=latest.description if latest else None,
        assigned_at=incident.created_at,
    )


# ------------------------------------------------------------------ trail
@router.get("/incidents/{incident_id}/events", response_model=list[EventOut])
def incident_events(incident_id: uuid.UUID,
                    db: Session = Depends(get_db),
                    user: User = Depends(_operator)) -> list[Event]:
    """The append only trail for one incident, oldest first."""
    incident = _incident_for(db, incident_id, user)
    return list(db.execute(
        select(Event)
        .where(Event.incident_id == incident.id)
        .order_by(Event.created_at, Event.id)
    ).scalars())


# -------------------------------------------------------------- escalation
@router.post("/incidents/escalation-sweep", response_model=list[uuid.UUID])
def escalation_sweep(db: Session = Depends(get_db),
                     user: User = Depends(_operator)) -> list[uuid.UUID]:
    """Run the overdue check now.

    The same sweep runs on a timer inside the application. This route exists so
    it can be triggered deliberately and so the behaviour is testable without
    waiting for the clock.
    """
    return [i.id for i in svc.escalation_sweep(db)]


# ---------------------------------------------------------------- triage
@router.post("/incidents/{incident_id}/priority", response_model=TriageOut)
def override_priority(incident_id: uuid.UUID,
                      payload: PriorityOverride,
                      db: Session = Depends(get_db),
                      user: User = Depends(_operator)) -> TriageOut:
    """An operator sets the priority by hand.

    This always outranks the rules. A person on the ground knows things the
    text does not contain, and the system records that a human made the call
    by setting triage_source, so nobody later mistakes it for an automatic
    assessment.
    """
    incident = _incident_for(db, incident_id, user)
    was, was_source = incident.priority, incident.triage_source

    incident.priority = payload.priority
    incident.triage_source = "operator"
    db.add(Event(
        incident_id=incident.id, actor="operator",
        message=(f"Priority set P{was} to P{payload.priority} by operator "
                 f"(was {was_source}): {payload.reason}"),
    ))
    db.commit()

    return TriageOut(
        incident_id=incident.id,
        priority=incident.priority,
        triage_source=incident.triage_source,
        severity_probability=incident.severity_probability,
        headline=incident.headline,
    )
