"""Shapes for dispatch, acknowledgement and resolution."""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models import Role, Status


class ResponderOut(BaseModel):
    """One unit on the roster, as the control room sees it."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    role: Role
    is_available: bool


class DispatchResult(BaseModel):
    """The outcome of a dispatch attempt.

    Always carries a responder, because a failed attempt is reported as an
    error rather than as a success with nothing attached. An operator must not
    have to inspect a field to discover that nobody is coming.
    """

    incident_id: uuid.UUID
    status: Status
    responder: ResponderOut
    eta_minutes: int
    role_matched: bool


class StatusChange(BaseModel):
    """Result of acknowledging, arriving or resolving."""

    incident_id: uuid.UUID
    status: Status
    changed: bool
    message: str


class EventOut(BaseModel):
    """One line of the append only audit trail."""

    model_config = ConfigDict(from_attributes=True)

    actor: str
    message: str
    created_at: datetime


class AssignmentOut(BaseModel):
    """What a responder is told: their own job, and nothing else."""

    incident_id: uuid.UUID
    reference: str
    category: str
    zone: str | None
    status: Status
    priority: int
    description: str | None
    assigned_at: datetime


class PriorityOverride(BaseModel):
    """An operator disagreeing with the rules.

    A reason is required. A priority change with no stated reason is the kind
    of thing nobody can defend afterwards, and this incident record may end up
    supporting a formal complaint.
    """

    priority: int = Field(ge=1, le=4)
    reason: str = Field(min_length=3, max_length=200)


class TriageOut(BaseModel):
    incident_id: uuid.UUID
    priority: int
    triage_source: str
    severity_probability: float | None
    headline: str
