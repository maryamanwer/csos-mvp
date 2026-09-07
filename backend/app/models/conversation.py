import uuid
from sqlalchemy import Column, ForeignKey, Uuid, JSON, DateTime, func
from app.core.database import Base
class Conversation(Base):
    __tablename__ = 'conversations'
    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    messages = Column(JSON, nullable=False, default=list)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
