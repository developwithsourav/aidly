"""Request and response shapes for report intake and the incident feed.

The constraints here are the ones the prototype established, so a client that
worked against the prototype behaves the same way against this API.
"""
import base64
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import Category, Status

# Matches the character budget the prototype showed to the reporter.
MAX_DESCRIPTION = 150


def reference_for(incident_id: uuid.UUID) -> str:
    """A short reference a person can read out over a radio.

    Derived from the identifier rather than stored, so it needs no column and
    can never drift from the row it names. Crockford style alphabet: no I, L,
    O or U, so it cannot be misheard as a digit or misread as a word.
    """
    raw = base64.b32encode(incident_id.bytes)[:8].decode("ascii")
    table = str.maketrans("ILOU", "8901")
    return "AIDLY-" + raw.translate(table)


class ReportCreate(BaseModel):
    """One submission from one person inside the venue."""

    venue_slug: str = Field(min_length=1, max_length=80)
    category: Category

    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION)
    lat: float | None = Field(default=None, ge=-90, le=90)
    lng: float | None = Field(default=None, ge=-180, le=180)
    zone_id: uuid.UUID | None = None
    callback_phone: str | None = Field(default=None, max_length=20)
    photo_key: str | None = Field(default=None, max_length=500)

    @field_validator("description")
    @classmethod
    def _blank_is_absent(cls, v: str | None) -> str | None:
        """An empty box and an untouched box mean the same thing."""
        if v is None:
            return None
        v = v.strip()
        return v or None

    @field_validator("callback_phone")
    @classmethod
    def _digits_only(cls, v: str | None) -> str | None:
        """Testers typed spaces and country codes. Keep the digits, drop the
        rest, and treat a field with no digits as not filled in."""
        if v is None:
            return None
        digits = "".join(c for c in v if c.isdigit())
        return digits or None


class ReportAccepted(BaseModel):
    """What the reporter gets back. Deliberately small: on a saturated network
    this is the response that has to arrive."""

    incident_id: uuid.UUID
    reference: str
    merged: bool
    report_count: int
    status: Status
    zone: str | None
    message: str


class ZoneOut(BaseModel):
    """A gate or stand the reporter can pick when the device has no position."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    is_exit: bool


class VenueOut(BaseModel):
    """What the reporting screen needs before anyone taps anything."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    zones: list[ZoneOut]


class IncidentOut(BaseModel):
    """One incident as the control room sees it.

    reference, zone and corroboration are derived rather than stored, so this
    model is built explicitly in the router instead of from attributes.
    """

    id: uuid.UUID
    reference: str
    category: Category
    status: Status
    priority: int
    headline: str
    zone: str | None
    report_count: int
    corroboration: int
    triage_source: str
    # Null until a trained classifier exists. An absent number is honest.
    severity_probability: float | None
    created_at: datetime
