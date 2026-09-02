"""Password hashing and access token issue/verify.

Kept separate from the router so the hashing scheme can change without
touching the HTTP layer, and so tests can exercise it without a request.

bcrypt is used directly rather than through passlib. passlib 1.7.4 reads
bcrypt.__about__, which modern bcrypt releases no longer define, and its
backend probe raises on the 72 byte limit described below.
"""
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()

# bcrypt silently ignores anything past the 72nd byte of the password. Left
# implicit, two different long passwords could share a hash, so the limit is
# applied here where it is visible.
BCRYPT_MAX_BYTES = 72


def _prepare(plain: str) -> bytes:
    """Encode and truncate on a character boundary, never mid codepoint."""
    raw = plain.encode("utf-8")
    if len(raw) <= BCRYPT_MAX_BYTES:
        return raw
    return raw[:BCRYPT_MAX_BYTES].decode("utf-8", "ignore").encode("utf-8")


def hash_password(plain: str) -> str:
    # gensalt carries its own random salt and cost factor, so the users table
    # needs no separate salt column.
    return bcrypt.hashpw(_prepare(plain), bcrypt.gensalt()).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    """Constant time comparison. Returns False on a malformed stored hash
    rather than raising, so one corrupt row cannot break the login endpoint."""
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


def create_access_token(subject: str, role: str,
                        venue_id: str | None = None) -> tuple[str, int]:
    """Returns the encoded token and its lifetime in seconds.

    The role travels inside the token so routine authorisation checks need no
    database round trip. Anything that must be current, such as whether the
    account is still active, is read from the database instead.
    """
    expires_in = settings.access_token_minutes * 60
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "venue_id": venue_id,
        "iat": now,
        "exp": now + timedelta(seconds=expires_in),
    }
    token = jwt.encode(payload, settings.jwt_secret,
                       algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str) -> dict[str, Any] | None:
    """None on any invalid or expired token. The caller decides the response."""
    try:
        return jwt.decode(token, settings.jwt_secret,
                          algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None
