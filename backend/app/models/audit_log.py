from sqlalchemy import Column, String, ForeignKey, Text, DateTime, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import UUIDMixin, TimestampMixin

class AuditLog(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "audit_logs"

    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    action = Column(Text, nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(36), nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    user = relationship("User", back_populates="audit_logs")

Index("ix_audit_logs_user_action", AuditLog.user_id, AuditLog.action)