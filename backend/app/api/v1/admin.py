"""
Administration Portal endpoints: users, roles, audit log.
TODO(M2): implement full CRUD against the users/roles tables.
"""
from fastapi import APIRouter, Depends

from app.core.security import require_role

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(user: dict = Depends(require_role("Admin"))):
    # TODO(M2): query the users table via SQLAlchemy session
    return []


@router.get("/audit-log")
def audit_log(user: dict = Depends(require_role("Admin"))):
    # TODO(M2): query audit_logs table, paginated, filterable by action/date
    return []
