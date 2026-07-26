"""Database models.

Geography is stored as PostGIS geography(Point, 4326) so that "nearest
available responder" is an indexed database query rather than something we
compute in Python over every row. Protocol embeddings use pgvector for the same
reason: retrieval belongs in the database.
"""
from __future__ import annotations

import enum
import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geography
from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean, CheckConstraint, DateTime, Enum, Float, ForeignKey, Index,
    Integer, String, Text, func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBED_DIM = 384  # all-MiniLM-L6-v2; small enough to run locally, no API needed


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class PkMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), index=True)


# ── enums ────────────────────────────────────────────────────────────────
class Category(str, enum.Enum):
    fire = "fire"
    medical = "medical"
    crowd = "crowd"
    accident = "accident"
    violence = "violence"
    other = "other"


class Role(str, enum.Enum):
    """Responder capability. Category maps to a preferred role at dispatch."""
    medic = "medic"
    fire = "fire"
    marshal = "marshal"
    security = "security"


class Status(str, enum.Enum):
    triaging = "triaging"
    verified = "verified"
    dispatched = "dispatched"
    en_route = "en_route"
    on_scene = "on_scene"
    resolved = "resolved"


class UserRole(str, enum.Enum):
    operator = "operator"     # control room: sees everything, dispatches
    responder = "responder"   # a unit in the field
    admin = "admin"


# ── venue ────────────────────────────────────────────────────────────────
class Venue(Base, PkMixin):
    __tablename__ = "venues"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    centre: Mapped[str] = mapped_column(Geography("POINT", srid=4326))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    zones: Mapped[list[Zone]] = relationship(back_populates="venue", cascade="all, delete-orphan")
    responders: Mapped[list[Responder]] = relationship(back_populates="venue", cascade="all, delete-orphan")


class Zone(Base, PkMixin):
    """A named place inside a venue: a gate, a stand, a stage, a food court.

    Reports resolve to the nearest zone, which is what an operator and a
    responder actually navigate by. "Near Gate 3" beats a decimal coordinate.
    """
    __tablename__ = "zones"

    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[str] = mapped_column(Geography("POINT", srid=4326))
    is_exit: Mapped[bool] = mapped_column(Boolean, default=False)

    venue: Mapped[Venue] = relationship(back_populates="zones")

    __table_args__ = (Index("ix_zones_location", "location", postgresql_using="gist"),)


# ── people ───────────────────────────────────────────────────────────────
class User(Base, PkMixin):
    """Replaces the shared passcode the hackathon build used."""
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    display_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(Enum(UserRole, name="user_role"))
    venue_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("venues.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Responder(Base, PkMixin):
    __tablename__ = "responders"

    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    code: Mapped[str] = mapped_column(String(20))            # M-07, E-02
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[Role] = mapped_column(Enum(Role, name="responder_role"), index=True)
    location: Mapped[str] = mapped_column(Geography("POINT", srid=4326))
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    venue: Mapped[Venue] = relationship(back_populates="responders")

    __table_args__ = (
        Index("ix_responders_location", "location", postgresql_using="gist"),
        Index("ix_responders_dispatch", "venue_id", "role", "is_available"),
    )


# ── incidents ────────────────────────────────────────────────────────────
class Incident(Base, PkMixin):
    __tablename__ = "incidents"

    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"), index=True)
    zone_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("zones.id", ondelete="SET NULL"))
    category: Mapped[Category] = mapped_column(Enum(Category, name="incident_category"), index=True)
    status: Mapped[Status] = mapped_column(
        Enum(Status, name="incident_status"), default=Status.triaging, index=True)

    priority: Mapped[int] = mapped_column(Integer, default=3)   # 1 critical .. 4 logged
    headline: Mapped[str] = mapped_column(String(200), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(Geography("POINT", srid=4326))
    report_count: Mapped[int] = mapped_column(Integer, default=1)

    # How the priority was arrived at, so the UI never has to guess.
    #   "model"  a trained classifier, probability is calibrated
    #   "llm"    a language model read the text
    #   "rules"  deterministic fallback, used when the others are unavailable
    triage_source: Mapped[str] = mapped_column(String(16), default="rules")
    # Calibrated P(priority is correct) from a trained model. NULL until Phase 2
    # exists. Deliberately nullable: an absent number is honest, an invented one
    # is not. This is what the hackathon build got wrong.
    severity_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    assigned_responder_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("responders.id", ondelete="SET NULL"))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    reports: Mapped[list[Report]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    events: Mapped[list[Event]] = relationship(back_populates="incident", cascade="all, delete-orphan")
    protocol_steps: Mapped[list[dict]] = mapped_column(JSONB, default=list)

    __table_args__ = (
        CheckConstraint("priority BETWEEN 1 AND 4", name="ck_incidents_priority"),
        CheckConstraint(
            "severity_probability IS NULL OR (severity_probability >= 0 AND severity_probability <= 1)",
            name="ck_incidents_severity_probability"),
        Index("ix_incidents_location", "location", postgresql_using="gist"),
        # the de-duplication lookup: same venue, category and zone, recent
        Index("ix_incidents_dedup", "venue_id", "category", "zone_id", "created_at"),
    )

    @property
    def corroboration(self) -> int:
        """Independent reports of the same incident, as a percentage.

        This is evidence, not model confidence: it only says how many separate
        people described the same thing in the same place. Kept explicitly
        distinct from severity_probability so the two are never confused.
        """
        return min(90, 25 + max(0, self.report_count - 1) * 20)


class Report(Base, PkMixin):
    """One submission from one person. Several can merge into one incident."""
    __tablename__ = "reports"

    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True)
    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"), index=True)
    category: Mapped[Category] = mapped_column(Enum(Category, name="incident_category", create_type=False))
    description: Mapped[str | None] = mapped_column(Text)
    # Callback only. Never used to locate anyone; only a carrier can do that.
    callback_phone: Mapped[str | None] = mapped_column(String(20))
    location: Mapped[str | None] = mapped_column(Geography("POINT", srid=4326))
    photo_key: Mapped[str | None] = mapped_column(String(500))
    reporter_fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)  # rate limiting

    incident: Mapped[Incident | None] = relationship(back_populates="reports")


class Event(Base, PkMixin):
    """Append only audit trail. Never updated, never deleted."""
    __tablename__ = "events"

    incident_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text)
    actor: Mapped[str | None] = mapped_column(String(120))   # who or what caused it

    incident: Mapped[Incident] = relationship(back_populates="events")


# ── knowledge base ───────────────────────────────────────────────────────
class Protocol(Base, PkMixin):
    """A response step from published emergency guidance.

    Every step shown to an operator must be traceable to a real document, so
    source and citation are not optional.
    """
    __tablename__ = "protocols"

    category: Mapped[Category] = mapped_column(
        Enum(Category, name="incident_category", create_type=False), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(300))
    citation: Mapped[str | None] = mapped_column(String(500))   # section or URL
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBED_DIM))


class Broadcast(Base, PkMixin):
    """Venue wide message, for example exit guidance during a crush."""
    __tablename__ = "broadcasts"

    venue_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("venues.id", ondelete="CASCADE"), index=True)
    message: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
