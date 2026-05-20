from sqlalchemy import Column, String, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import UUIDMixin, TimestampMixin
from sqlalchemy import Column, String, Boolean, ForeignKey, Index
from sqlalchemy.orm import relationship

class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    username = Column(String(50), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role_id = Column(String(36), ForeignKey("roles.id"), nullable=False, index=True)
    branch_id = Column(String(36), ForeignKey("branches.id"), nullable=False, index=True)

    role = relationship("Role", back_populates="users")
    branch = relationship("Branch", back_populates="users")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

Index("ix_users_username_email", User.username, User.email)