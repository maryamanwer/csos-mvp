import uuid
from sqlalchemy import Column, DateTime, ForeignKey, String, Uuid, func
from app.core.database import Base
class Workflow(Base):
    __tablename__ = 'workflows'
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=False)
    asset_id = Column(String(100), nullable=True)
    owner_id = Column(Uuid, ForeignKey('users.id'), nullable=False)
    status = Column(String(20), nullable=False, default='open')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
