import uuid

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.core.database import Base


class StandardsUpload(Base):
    __tablename__ = "standards_uploads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # csv, xlsx, docx, json, manual
    status = Column(String(20), default="pending")  # pending, processed, failed
    controls_parsed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    generated_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    report_type = Column(String(50), nullable=False)  # risk, compliance, asset
    format = Column(String(10), nullable=False)  # pdf, xlsx
    file_path = Column(Text, nullable=False)
    filters = Column(JSONB, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
