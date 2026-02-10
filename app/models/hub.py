import uuid

from sqlalchemy import (
    Column, String, Boolean, Text, Integer, DateTime, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.database import Base


class Hub(Base):
    """Hub model - stub for future implementation."""
    __tablename__ = "hubs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    leader_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    max_members = Column(Integer, default=50)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class HubMembership(Base):
    """Hub membership model - stub for future implementation."""
    __tablename__ = "hub_memberships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hub_id = Column(
        UUID(as_uuid=True), ForeignKey("hubs.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), default="member")  # member, moderator, leader
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
