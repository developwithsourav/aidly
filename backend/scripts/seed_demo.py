"""Creates one venue with zones, responders and staff accounts.

Enough to click through the whole reporting path against a real database. Safe
to run repeatedly: it looks for the venue by slug and leaves an existing one
alone rather than creating a second copy.

    python -m scripts.seed_demo
"""
import os
import sys

from sqlalchemy import select

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import hash_password  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import Responder, Role, User, UserRole, Venue, Zone  # noqa: E402

SLUG = "arsd-main"

# Approximate positions around one ground. Longitude first in WKT.
ZONES = [
    ("Gate 1", 77.1210, 28.5925, True),
    ("Gate 2", 77.1230, 28.5910, True),
    ("Main Stage", 77.1218, 28.5921, False),
    ("Food Court", 77.1225, 28.5928, False),
    ("Medical Post", 77.1205, 28.5915, False),
]

RESPONDERS = [
    ("M-01", "Anita Rao", Role.medic, 77.1206, 28.5916),
    ("M-02", "Vikram Shah", Role.medic, 77.1224, 28.5927),
    ("F-01", "Rakesh Nair", Role.fire, 77.1212, 28.5923),
    ("S-01", "Priya Menon", Role.security, 77.1229, 28.5911),
    ("S-02", "Imran Qureshi", Role.security, 77.1219, 28.5920),
    ("W-01", "Deepa Iyer", Role.marshal, 77.1215, 28.5924),
]

STAFF = [
    ("control@arsd.example", "Control Room One", UserRole.operator),
    ("admin@arsd.example", "Venue Administrator", UserRole.admin),
    ("marshal@arsd.example", "Duty Marshal", UserRole.responder),
]

# Development only. A real deployment sets these through the environment and
# never ships a known value.
DEV_PASSWORD = os.environ.get("SEED_PASSWORD", "ChangeMe2026!")


def main() -> None:
    db = SessionLocal()
    try:
        venue = db.execute(
            select(Venue).where(Venue.slug == SLUG)
        ).scalar_one_or_none()
        if venue is not None:
            print(f"venue {SLUG!r} already exists, nothing to do")
            return

        venue = Venue(name="ARSD Main Ground", slug=SLUG,
                      centre="SRID=4326;POINT(77.1216 28.5921)")
        db.add(venue)
        db.flush()

        for name, lng, lat, is_exit in ZONES:
            db.add(Zone(venue_id=venue.id, name=name, is_exit=is_exit,
                        location=f"SRID=4326;POINT({lng} {lat})"))

        for code, name, role, lng, lat in RESPONDERS:
            db.add(Responder(venue_id=venue.id, code=code, name=name, role=role,
                             location=f"SRID=4326;POINT({lng} {lat})"))

        for email, display, role in STAFF:
            db.add(User(email=email, password_hash=hash_password(DEV_PASSWORD),
                        display_name=display, role=role, venue_id=venue.id))

        db.commit()
        print(f"seeded {SLUG!r}: {len(ZONES)} zones, "
              f"{len(RESPONDERS)} responders, {len(STAFF)} accounts")
        print("staff password comes from SEED_PASSWORD, "
              "currently " + ("set" if "SEED_PASSWORD" in os.environ
                              else "the development default"))
    finally:
        db.close()


if __name__ == "__main__":
    main()
