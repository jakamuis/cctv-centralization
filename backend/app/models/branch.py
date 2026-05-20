from sqlalchemy import Column, String, Boolean, Text, Index
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import UUIDMixin, TimestampMixin

class Branch(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "branches"

    branch_code = Column(String(20), unique=True, nullable=False, index=True)
    branch_name = Column(String(100), nullable=False)
    address = Column(Text, nullable=True)
    timezone = Column(String(50), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    users = relationship("User", back_populates="branch", cascade="all, delete-orphan")
    devices = relationship("Device", back_populates="branch", cascade="all, delete-orphan")

Index("ix_branches_branch_code", Branch.branch_code)