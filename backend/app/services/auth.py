"""Authentication against the users table.

The login endpoint is the one place an attacker can guess at, so the rules
here matter more than the amount of code:

* one failure message for every failure cause, so the response cannot be used
  to discover which email addresses exist,
* the password hash is verified even when no user was found, so the time taken
  does not reveal the answer either,
* a deactivated account fails exactly like a wrong password.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models import User

# Verified when the email is unknown, purely to keep the timing flat. This is a
# real bcrypt hash of a value no one holds.
_DUMMY_HASH = (
    "$2b$12$C6UzMDM.H6dfI/f/IKcEe.rJXQnGDDPFHOCkCcTLB0P9C7dQKrHQO"
)


def authenticate(db: Session, email: str, password: str) -> User | None:
    """Returns the user on success, None on every kind of failure."""
    normalised = email.strip().lower()
    user = db.execute(
        select(User).where(User.email == normalised)
    ).scalar_one_or_none()

    if user is None:
        verify_password(password, _DUMMY_HASH)
        return None

    if not verify_password(password, user.password_hash):
        return None

    if not user.is_active:
        return None

    return user
