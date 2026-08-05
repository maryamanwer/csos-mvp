import uuid

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    action: str,
    user_id: str | uuid.UUID | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    parsed_user_id = None
    if user_id:
        parsed_user_id = (
            user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        )
    entry = AuditLog(
        user_id=parsed_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_=metadata,
        ip_address=ip_address,
    )
    db.add(entry)
    return entry
