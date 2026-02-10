import uuid

from sqlalchemy import (
    Column, String, Boolean, Text, DateTime, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)

    # Profile
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    phone = Column(String(50), nullable=True)
    telegram = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)
    about = Column(Text, nullable=True)
    avatar_url = Column(String(500), nullable=True)

    # Referral system
    referral_code = Column(String(10), unique=True, nullable=False, index=True)
    referred_by_id = Column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )

    # Roles and statuses
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    email_verified = Column(Boolean, default=False)

    # Partner status (calculated automatically)
    # bronze (5+), silver (20+), gold (50+), platinum (100+)
    partner_status = Column(String(20), default="none")

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    referred_by = relationship("User", remote_side=[id], backref="referrals")
