"""Durable conversations and grounded agent traces."""
import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, String, Text, Uuid, func

from app.core.database import Base


class AIConversation(Base):
    __tablename__ = "ai_conversations"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class AIMessage(Base):
    __tablename__ = "ai_messages"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    conversation_id = Column(
        Uuid, ForeignKey("ai_conversations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    agent_trace = Column(JSON, nullable=True)
    citations = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
