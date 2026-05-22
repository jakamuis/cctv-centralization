import uuid

from sqlalchemy import Column, String, DateTime, func, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from .base import Base


class Branch(Base):
    __tablename__ = "branches"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False
    )

    name = Column(String, nullable=False)

    code = Column(
        String,
        nullable=False,
        unique=True
    )

    location = Column(
        String,
        nullable=True
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Removed region_id as Region support was removed
    # region_id = Column(
    #     Integer,
    #     ForeignKey("regions.id", ondelete="SET NULL"),
    #     nullable=True
    # )

    #cameras = relationship(
     #   "Camera",
      #  back_populates="branch",
       # cascade="all, delete-orphan"
    #)
