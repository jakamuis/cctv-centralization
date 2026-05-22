from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, ForeignKey

from app.models.base import Base


class AuditLog(Base):
    """Audit log entries for security-relevant actions.

    NOTE: This model is aligned with how AuditLog is used in
    `backend/app/api/v1/api.py` (fields: user_id, action, target_type,
    target_id, ip_address, created_at) and with the integer primary key
    used by `User.id`.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(255), nullable=False)
    target_type = Column(String(100), nullable=True)
    target_id = Column(String(100), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)