from sqlalchemy import Column, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from .base import Base, UUIDMixin


class Camera(UUIDMixin, Base):
    __tablename__ = "cameras"

    branch_id = Column(UUID(as_uuid=True), ForeignKey("branches.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    stream_name = Column(String(255), unique=True, nullable=False)
    rtsp_channel = Column(String(50), nullable=True)
    status = Column(String(50), nullable=True)
    enabled = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Removed legacy device relationship to fix import script errors
    # device_id = Column(
    #     UUID(as_uuid=True),
    #     ForeignKey("devices.id"),
    #     nullable=True,
    #     index=True,
    # )
    #
    # device = relationship(
    #     "Device",
    #     back_populates="cameras",
    # )


# Define relationship after class definition to avoid import order issues
def _setup_relationships():
    from .branch import Branch
    Camera.branch = relationship(Branch, lazy="raise")

_setup_relationships()