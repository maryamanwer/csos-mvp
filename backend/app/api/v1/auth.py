"""
Auth endpoints: login, refresh, current-user.
TODO(M2): replace the in-memory MOCK_USERS lookup with a real
SQLAlchemy query against the users table.
"""
from fastapi import APIRouter, Depends, HTTPException

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_password,
)
from app.schemas.auth import LoginRequest, TokenResponse, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

# TODO(M2): remove — placeholder only so the endpoint is runnable before DB wiring.
_MOCK_USERS = {
    "admin@csos.local": {
        "id": "00000000-0000-0000-0000-000000000001",
        "full_name": "CSOS Admin",
        "role": "Admin",
        "hashed_password": "$2b$12$replace-with-real-hash",
    }
}


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    user = _MOCK_USERS.get(payload.email)
    if not user:  # TODO(M2): real verify_password() check against DB
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(subject=payload.email, role=user["role"])
    refresh_token = create_refresh_token(subject=payload.email)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserOut)
def me(current_user: dict = Depends(get_current_user)):
    return UserOut(
        id="00000000-0000-0000-0000-000000000001",
        email=current_user["sub"],
        full_name="CSOS Admin",
        role=current_user["role"],
        is_active=True,
    )
