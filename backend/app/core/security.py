"""Password hashing, rotating JWTs, database identity lookup, and RBAC."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(
    subject: str,
    role: str,
    email: str | None = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload = {
        "sub": subject,
        "role": role,
        "email": email,
        "iss": settings.JWT_ISSUER,
        "aud": [settings.JWT_PLATFORM_AUDIENCE, settings.JWT_MCP_AUDIENCE],
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(subject: str, token_id: str | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "jti": token_id or str(uuid.uuid4()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_PLATFORM_AUDIENCE,
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def token_fingerprint(token: str) -> str:
    """Store a non-reversible refresh-token fingerprint, never the raw token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            audience=settings.JWT_PLATFORM_AUDIENCE,
            issuer=settings.JWT_ISSUER,
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> dict:
    """Resolve an access token to an active PostgreSQL user and current role."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token subject")

    user = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_id)
        .first()
    )
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account is unavailable")
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.name,
        "is_active": user.is_active,
    }


def require_role(*allowed_roles: str):
    """FastAPI dependency factory for RBAC-protected endpoints.

    Usage: `@router.get(...)  def handler(user=Depends(require_role("Admin"))): ...`
    """

    async def _checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return _checker
