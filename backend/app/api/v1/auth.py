"""PostgreSQL-backed login, identity, refresh rotation, and logout."""
from datetime import datetime, timedelta, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    token_fingerprint,
    verify_password,
)
from app.models.user import RefreshToken, User
from app.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserOut,
)
from app.services.audit import record_audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role.name,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
    )


def _issue_token_pair(user: User, db: Session) -> TokenResponse:
    access_token = create_access_token(
        subject=str(user.id),
        role=user.role.name,
        email=user.email,
    )
    refresh_token = create_refresh_token(subject=str(user.id))
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=token_fingerprint(refresh_token),
            expires_at=datetime.now(timezone.utc)
            + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.email == payload.email.lower())
        .first()
    )
    if not user or not user.is_active or not verify_password(payload.password, user.hashed_password):
        record_audit(
            db,
            "LOGIN_FAILED",
            entity_type="User",
            entity_id=str(payload.email),
            metadata={"reason": "invalid_credentials"},
            ip_address=request.client.host if request.client else None,
        )
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")

    user.last_login_at = datetime.now(timezone.utc)
    tokens = _issue_token_pair(user, db)
    record_audit(
        db,
        "LOGIN_SUCCESS",
        user_id=user.id,
        entity_type="User",
        entity_id=str(user.id),
        ip_address=request.client.host if request.client else None,
    )
    db.commit()
    return tokens


@router.post("/refresh", response_model=TokenResponse)
def refresh_tokens(payload: RefreshTokenRequest, db: Session = Depends(get_db)):
    token_payload = decode_token(payload.refresh_token)
    if token_payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    try:
        user_id = uuid.UUID(str(token_payload.get("sub")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")

    stored = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_fingerprint(payload.refresh_token),
            RefreshToken.user_id == user_id,
        )
        .first()
    )
    now = datetime.now(timezone.utc)
    stored_expiry = stored.expires_at if stored else None
    if stored_expiry and stored_expiry.tzinfo is None:
        stored_expiry = stored_expiry.replace(tzinfo=timezone.utc)
    if not stored or stored.revoked or not stored_expiry or stored_expiry <= now:
        raise HTTPException(status_code=401, detail="Refresh token is unavailable")

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_id, User.is_active.is_(True))
        .first()
    )
    if not user:
        raise HTTPException(status_code=401, detail="User account is unavailable")

    stored.revoked = True
    tokens = _issue_token_pair(user, db)
    record_audit(
        db,
        "REFRESH_TOKEN_ROTATED",
        user_id=user.id,
        entity_type="User",
        entity_id=str(user.id),
    )
    db.commit()
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: LogoutRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stored = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_fingerprint(payload.refresh_token),
            RefreshToken.user_id == uuid.UUID(current_user["id"]),
        )
        .first()
    )
    if stored:
        stored.revoked = True
    record_audit(
        db,
        "LOGOUT",
        user_id=current_user["id"],
        entity_type="User",
        entity_id=current_user["id"],
    )
    db.commit()


@router.get("/me", response_model=UserOut)
def me(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == uuid.UUID(current_user["id"]))
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _user_out(user)
