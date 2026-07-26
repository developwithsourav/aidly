"""Dispatch: choose and assign the responder who should go.

Deterministic on purpose. Triage may be probabilistic; who gets sent is not.
Nobody wants a model deciding whether the medic goes, and an operator has to be
able to explain the choice afterwards.
"""
from __future__ import annotations

import uuid

from geoalchemy2.functions import ST_Distance
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Event, Incident, Responder, Role, Status, utcnow

# Which capability each category wants. If none of that role is free we widen
# to anyone available rather than leaving the incident unattended: a marshal who
# can start crowd control now beats the right specialist who is busy.
PREFERRED_ROLE: dict[Category, Role] = {
    Category.medical: Role.medic,
    Category.fire: Role.fire,
    Category.crowd: Role.marshal,
    Category.violence: Role.security,
    Category.accident: Role.marshal,
}

WALKING_SPEED_M_PER_MIN = 84.0   # ~1.4 m/s, a brisk walk through a crowd


def eta_minutes(distance_m: float) -> int:
    """Minutes on foot, never less than one. Honest about being an estimate:
    it is straight line distance, so it under-reads where a crowd blocks the
    direct path. Routing is on the roadmap."""
    return max(1, round(distance_m / WALKING_SPEED_M_PER_MIN))


def _nearest(db: Session, incident: Incident, role: Role | None) -> tuple[Responder, float] | None:
    """Nearest available responder, optionally restricted to one role.

    Ordering happens in the database against a GiST index, so this stays one
    query no matter how many responders a venue has.
    """
    distance = ST_Distance(Responder.location, incident.location).label("distance")
    stmt = (
        select(Responder, distance)
        .where(
            Responder.venue_id == incident.venue_id,
            Responder.is_available.is_(True),
        )
        .order_by(distance)
        .limit(1)
    )
    if role is not None:
        stmt = stmt.where(Responder.role == role)

    row = db.execute(stmt).first()
    return (row[0], float(row[1])) if row else None


def dispatch_nearest(db: Session, incident: Incident) -> tuple[Responder, int] | None:
    """Assign the best available responder. Returns the unit and its ETA.

    Returns None when nothing is free, which the caller must surface to the
    operator rather than swallow. "No unit available" is information a control
    room needs immediately.
    """
    if incident.assigned_responder_id is not None:
        return None   # already assigned; re-dispatching would strand the first unit

    preferred = PREFERRED_ROLE.get(incident.category)
    chosen = _nearest(db, incident, preferred) or _nearest(db, incident, None)
    if chosen is None:
        db.add(Event(
            incident_id=incident.id, actor="system",
            message="Dispatch attempted, no responder available",
        ))
        return None

    responder, distance_m = chosen
    eta = eta_minutes(distance_m)

    responder.is_available = False
    incident.assigned_responder_id = responder.id
    incident.status = Status.dispatched

    matched = "role matched" if preferred and responder.role == preferred else "nearest available"
    db.add(Event(
        incident_id=incident.id, actor="operator",
        message=f"{responder.role.value} {responder.code} dispatched ({matched}), ETA {eta} min",
    ))
    db.flush()
    return responder, eta


def acknowledge(db: Session, incident: Incident) -> bool:
    """Responder accepted. First acknowledgement wins; later ones are no-ops."""
    if incident.status != Status.dispatched:
        return False
    incident.status = Status.en_route
    incident.acknowledged_at = utcnow()
    db.add(Event(incident_id=incident.id, actor="responder", message="Accepted, en route"))
    db.flush()
    return True


def mark_on_scene(db: Session, incident: Incident) -> bool:
    if incident.status != Status.en_route:
        return False
    incident.status = Status.on_scene
    db.add(Event(incident_id=incident.id, actor="responder", message="On scene"))
    db.flush()
    return True


def resolve(db: Session, incident: Incident, actor: str = "operator") -> bool:
    """Close the incident and return its unit to the pool.

    Freeing the responder here is what keeps the pool honest; forgetting it is
    how a venue slowly runs out of units that are not actually busy.
    """
    if incident.status == Status.resolved:
        return False

    if incident.assigned_responder_id:
        responder = db.get(Responder, incident.assigned_responder_id)
        if responder:
            responder.is_available = True

    incident.status = Status.resolved
    incident.resolved_at = utcnow()
    db.add(Event(incident_id=incident.id, actor=actor, message="Resolved, audit log closed"))
    db.flush()
    return True


def escalate_if_unhandled(db: Session, incident_id: uuid.UUID) -> bool:
    """Called on a timer. A critical nobody has picked up must become loud.

    Only escalates P1s that are still waiting: anything already dispatched has
    a unit moving towards it and does not need the control lead woken up.
    """
    incident = db.get(Incident, incident_id)
    if incident is None:
        return False
    if incident.priority != 1 or incident.status not in (Status.triaging, Status.verified):
        return False

    db.add(Event(
        incident_id=incident.id, actor="system",
        message="ESCALATED to control lead, P1 unacknowledged",
    ))
    db.flush()
    return True
