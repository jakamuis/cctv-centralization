from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.base import UUIDMixin, TimestampMixin

class Role(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "roles"

    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)

    users = relationship("User", back_populates="role", cascade="all, delete-orphan")