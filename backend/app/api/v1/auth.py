"""
Auth endpoints: login and current-user.
TODO(P2): replace the development account with a SQLAlchemy query against the
users table and add persisted refresh-token rotation.
"""
import secrets

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
)
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# TODO(P2): remove when PostgreSQL-backed authentication is implemented.
_DEVELOPMENT_USER = {
    "email": settings.DEMO_ADMIN_EMAIL,
    "id": "00000000-0000-0000-0000-000000000001",
    "full_name": "CSOS Admin",
    "role": "Admin",
}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    valid_development_login = (
        settings.ENVIRONMENT == "development"
        and secrets.compare_digest(payload.email, _DEVELOPMENT_USER["email"])
        and secrets.compare_digest(payload.password, settings.DEMO_ADMIN_PASSWORD)
    )
    if not valid_development_login:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(subject=payload.email, role=_DEVELOPMENT_USER["role"])
    refresh_token = create_refresh_token(subject=payload.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return UserOut(
        id=_DEVELOPMENT_USER["id"],
        email=current_user["sub"],
        full_name=_DEVELOPMENT_USER["full_name"],
        role=current_user["role"],
        is_active=True,
    )
