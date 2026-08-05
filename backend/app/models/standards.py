import uuid

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text, Uuid, func

from app.core.database import Base


class StandardsUpload(Base):
    __tablename__ = "standards_uploads"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    uploaded_by = Column(Uuid, ForeignKey("users.id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    file_type = Column(String(20), nullable=False)  # csv, xlsx, docx, json, manual
    status = Column(String(20), default="pending")  # pending, processed, failed
    controls_parsed = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Report(Base):
    __tablename__ = "reports"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    generated_by = Column(Uuid, ForeignKey("users.id"), nullable=False)
    report_type = Column(String(50), nullable=False)  # risk, compliance, asset
    format = Column(String(10), nullable=False)  # pdf, xlsx
    file_path = Column(Text, nullable=False)
    filters = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
