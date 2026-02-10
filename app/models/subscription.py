import uuid

from sqlalchemy import (
    Column, String, Boolean, Integer, Text, DateTime, ForeignKey, Numeric, JSON,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SubscriptionPlan(Base):
    """Subscription plans for the club."""
    __tablename__ = "subscription_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String(20), unique=True, nullable=False)
    name = Column(String(50), nullable=False)
    price_monthly = Column(Numeric(10, 2), nullable=False)
    price_yearly = Column(Numeric(10, 2), nullable=False)
    max_voicyfy_agents = Column(Integer, default=1)
    max_chatforyou_access = Column(String(20), default="limited")
    max_ai_admin_bots = Column(Integer, default=1)

    # Commission rates (% of plan price)
    commission_direct = Column(Numeric(5, 2), default=30.00)
    commission_level2 = Column(Numeric(5, 2), default=15.00)
    commission_retention = Column(Numeric(5, 2), default=10.00)
    commission_leader_pool = Column(Numeric(5, 2), default=5.00)
    owner_margin = Column(Numeric(5, 2), default=40.00)

    description = Column(Text, nullable=True)
    features = Column(JSON, nullable=True)
    is_active = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class UserSubscription(Base):
    """Active user subscriptions."""
    __tablename__ = "user_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        nullable=False,
    )

    billing_period = Column(String(10), nullable=False)  # monthly, yearly
    status = Column(String(20), default="active")  # active, cancelled, expired, trial

    started_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)

    consecutive_months = Column(Integer, default=1)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="subscriptions")
    plan = relationship("SubscriptionPlan")


class PaymentTransaction(Base):
    """All payment transactions."""
    __tablename__ = "payment_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id = Column(
        UUID(as_uuid=True),
        ForeignKey("user_subscriptions.id"),
        nullable=True,
    )

    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="RUB")

    payment_system = Column(String(50), default="robokassa")
    external_payment_id = Column(String(100), nullable=True)

    status = Column(String(20), default="pending")  # pending, success, failed, refunded

    subscription_month_number = Column(Integer, default=1)

    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="payments")
