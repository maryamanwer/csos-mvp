"""Idempotent relational bootstrap for local and container deployments."""
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.user import Permission, Role, User


ROLE_DESCRIPTIONS = {
    "Admin": "Full system administration",
    "Executive": "Read-only strategic dashboards",
    "Analyst": "Investigate risks and vulnerabilities",
    "Engineer": "Manage assets and technical relationships",
    "SecurityArchitect": "Design controls and review security relationships",
    "ComplianceOfficer": "Manage frameworks, policies, and audits",
}

PERMISSIONS = {
    "dashboard:read": "View role-appropriate dashboards",
    "asset:read": "View assets and relationships",
    "asset:write": "Create and update assets and relationships",
    "vulnerability:read": "View vulnerabilities",
    "vulnerability:write": "Create and update vulnerabilities",
    "admin:manage": "Manage users, roles, and audit information",
    "compliance:read": "View compliance coverage and gaps",
    "compliance:write": "Manage standards and control mappings",
    "risk:read": "View calculated risk assessments",
    "report:read": "Generate and download reports",
    "chat:use": "Use role-grounded AI assistance",
    "workflow:manage": "Create and progress remediation workflows",
}

ROLE_PERMISSION_CODES = {
    "Admin": set(PERMISSIONS),
    "Executive": {"dashboard:read", "asset:read", "vulnerability:read", "risk:read", "compliance:read", "report:read", "chat:use"},
    "Analyst": {
        "dashboard:read",
        "asset:read",
        "vulnerability:read",
        "vulnerability:write",
        "risk:read",
        "chat:use",
        "workflow:manage",
    },
    "Engineer": {
        "dashboard:read",
        "asset:read",
        "asset:write",
        "vulnerability:read",
        "risk:read",
        "chat:use",
        "workflow:manage",
    },
    "SecurityArchitect": {"dashboard:read", "asset:read", "asset:write", "vulnerability:read", "risk:read", "compliance:read", "chat:use", "workflow:manage"},
    "ComplianceOfficer": {"dashboard:read", "asset:read", "compliance:read", "compliance:write", "report:read", "chat:use", "workflow:manage"},
}


def seed_identity_data(db: Session) -> None:
    roles: dict[str, Role] = {}
    new_roles: set[str] = set()
    for name, description in ROLE_DESCRIPTIONS.items():
        role = db.query(Role).filter(Role.name == name).first()
        if not role:
            new_roles.add(name)
            role = Role(name=name, description=description)
            db.add(role)
            db.flush()
        roles[name] = role

    permissions: dict[str, Permission] = {}
    new_permissions: set[str] = set()
    for code, description in PERMISSIONS.items():
        permission = db.query(Permission).filter(Permission.code == code).first()
        if not permission:
            new_permissions.add(code)
            permission = Permission(code=code, description=description)
            db.add(permission)
            db.flush()
        permissions[code] = permission

    for role_name, codes in ROLE_PERMISSION_CODES.items():
        if role_name in new_roles:
            roles[role_name].permissions = [permissions[code] for code in sorted(codes)]
        elif new_permissions:
            existing = {permission.code for permission in roles[role_name].permissions}
            roles[role_name].permissions.extend(
                permissions[code] for code in sorted(codes & new_permissions - existing)
            )

    admin = db.query(User).filter(User.email == settings.DEMO_ADMIN_EMAIL).first()
    if not admin:
        admin = User(
            email=settings.DEMO_ADMIN_EMAIL,
            hashed_password=hash_password(settings.DEMO_ADMIN_PASSWORD),
            full_name="CSOS Administrator",
            role_id=roles["Admin"].id,
            is_active=True,
        )
        db.add(admin)
    db.commit()


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_identity_data(db)
