"""Login endpoints.

POST /api/auth/login  issues an access token
GET  /api/auth/me     returns the account the token belongs to
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import create_access_token, decode_access_token
from app.db import get_db
from app.models import User
from app.schemas.auth import LoginRequest, TokenResponse, UserOut
from app.services.auth import authenticate

router = APIRouter(prefix="/api/auth", tags=["auth"])
bearer = HTTPBearer(auto_error=False)

INVALID = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Incorrect email or password",
    headers={"WWW-Authenticate": "Bearer"},
)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = authenticate(db, payload.email, payload.password)
    if user is None:
        raise INVALID

    token, expires_in = create_access_token(
        subject=str(user.id),
        role=user.role.value,
        venue_id=str(user.venue_id) if user.venue_id else None,
    )
    return TokenResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserOut.model_validate(user),
    )


def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    """Dependency for every protected route.

    The account is reloaded on each request rather than trusted from the token,
    so deactivating a user takes effect immediately instead of when their token
    happens to expire.
    """
    if creds is None:
        raise INVALID

    claims = decode_access_token(creds.credentials)
    if claims is None or "sub" not in claims:
        raise INVALID

    user = db.get(User, claims["sub"])
    if user is None or not user.is_active:
        raise INVALID

    return user


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)) -> UserOut:
    return UserOut.model_validate(user)
