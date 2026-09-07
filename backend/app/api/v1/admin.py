"""Administration Portal APIs for users, roles, permissions, and audit history."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import hash_password, require_role
from app.models.audit import AuditLog
from app.models.user import Permission, Role, User
from app.schemas.auth import (
    AuditLogOut,
    RoleOut,
    RoleUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services.audit import record_audit
from app.core.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/settings")
def system_settings(user: dict = Depends(require_role("Admin"))):
    """Return non-secret effective settings for deployment verification."""
    return {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "access_token_minutes": settings.ACCESS_TOKEN_EXPIRE_MINUTES,
        "refresh_token_days": settings.REFRESH_TOKEN_EXPIRE_DAYS,
        "max_import_rows": settings.MAX_IMPORT_ROWS,
        "ai_provider": settings.AI_PROVIDER,
        "ai_default_model": settings.AI_DEFAULT_MODEL,
        "ai_available_models": list(settings.available_ai_models),
        "api_documentation": "/docs",
    }


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


def _role_out(role: Role) -> RoleOut:
    return RoleOut(
        id=role.id,
        name=role.name,
        description=role.description,
        permission_codes=sorted(permission.code for permission in role.permissions),
    )


@router.get("/users", response_model=list[UserOut])
def list_users(
    search: str | None = Query(default=None, max_length=100),
    user: dict = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    query = db.query(User).options(joinedload(User.role))
    if search:
        term = f"%{search.lower()}%"
        query = query.filter(
            (User.email.ilike(term)) | (User.full_name.ilike(term))
        )
    return [_user_out(item) for item in query.order_by(User.full_name).all()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    current_user: dict = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.email == payload.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email is already registered")
    role = db.query(Role).filter(Role.name == payload.role).first()
    if not role:
        raise HTTPException(status_code=400, detail="Unknown role")
    new_user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name.strip(),
        is_active=payload.is_active,
        role_id=role.id,
    )
    db.add(new_user)
    db.flush()
    new_user.role = role
    record_audit(
        db,
        "USER_CREATED",
        user_id=current_user["id"],
        entity_type="User",
        entity_id=str(new_user.id),
        metadata={"email": new_user.email, "role": role.name},
    )
    db.commit()
    db.refresh(new_user)
    return _user_out(new_user)


@router.put("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    current_user: dict = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    target = (
        db.query(User)
        .options(joinedload(User.role))
        .filter(User.id == user_id)
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    updates = payload.model_dump(exclude_unset=True)
    if "email" in updates:
        email = str(updates["email"]).lower()
        duplicate = db.query(User).filter(User.email == email, User.id != user_id).first()
        if duplicate:
            raise HTTPException(status_code=409, detail="Email is already registered")
        target.email = email
    if updates.get("password"):
        target.hashed_password = hash_password(updates["password"])
    if "full_name" in updates:
        target.full_name = updates["full_name"].strip()
    if "is_active" in updates:
        if str(user_id) == current_user["id"] and not updates["is_active"]:
            raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
        target.is_active = updates["is_active"]
    if updates.get("role"):
        role = db.query(Role).filter(Role.name == updates["role"]).first()
        if not role:
            raise HTTPException(status_code=400, detail="Unknown role")
        target.role = role
        target.role_id = role.id
    record_audit(
        db,
        "USER_UPDATED",
        user_id=current_user["id"],
        entity_type="User",
        entity_id=str(target.id),
        metadata={"fields": sorted(updates)},
    )
    db.commit()
    db.refresh(target)
    return _user_out(target)


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_user(
    user_id: uuid.UUID,
    current_user: dict = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    if str(user_id) == current_user["id"]:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.is_active = False
    record_audit(
        db,
        "USER_DEACTIVATED",
        user_id=current_user["id"],
        entity_type="User",
        entity_id=str(target.id),
    )
    db.commit()


@router.get("/roles", response_model=list[RoleOut])
def list_roles(
    user: dict = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    roles = db.query(Role).options(joinedload(Role.permissions)).order_by(Role.name).all()
    return [_role_out(role) for role in roles]


@router.put("/roles/{role_id}", response_model=RoleOut)
def update_role(
    role_id: uuid.UUID,
    payload: RoleUpdate,
    current_user: dict = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    role = (
        db.query(Role)
        .options(joinedload(Role.permissions))
        .filter(Role.id == role_id)
        .first()
    )
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    if payload.description is not None:
        role.description = payload.description
    if payload.permission_codes is not None:
        permissions = (
            db.query(Permission)
            .filter(Permission.code.in_(payload.permission_codes))
            .all()
        )
        if len(permissions) != len(set(payload.permission_codes)):
            raise HTTPException(status_code=400, detail="One or more permissions are unknown")
        role.permissions = permissions
    record_audit(
        db,
        "ROLE_UPDATED",
        user_id=current_user["id"],
        entity_type="Role",
        entity_id=str(role.id),
        metadata={"role": role.name},
    )
    db.commit()
    db.refresh(role)
    return _role_out(role)


@router.get("/audit-log", response_model=list[AuditLogOut])
def audit_log(
    action: str | None = Query(default=None, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    user: dict = Depends(require_role("Admin")),
    db: Session = Depends(get_db),
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    rows = (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        AuditLogOut(
            id=row.id,
            user_id=row.user_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            metadata=row.metadata_,
            ip_address=row.ip_address,
            created_at=row.created_at,
        )
        for row in rows
    ]
