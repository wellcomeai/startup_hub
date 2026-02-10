import uuid

from sqlalchemy import (
    Column, String, Integer, DateTime, ForeignKey, Numeric,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class ReferralCommission(Base):
    """
    Commission entries for partners.

    Created on each successful payment.
    One user payment can produce up to 3 commission records:
    1. direct  (30%) - direct referrer
    2. level2  (15%) - referrer's referrer
    3. retention (10%) - direct referrer if consecutive_months >= 2
    """
    __tablename__ = "referral_commissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    partner_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payer_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    transaction_id = Column(
        UUID(as_uuid=True),
        ForeignKey("payment_transactions.id"),
        nullable=False,
    )

    commission_type = Column(String(20), nullable=False)  # direct, level2, retention
    referral_level = Column(Integer, nullable=False)

    payment_amount = Column(Numeric(10, 2), nullable=False)
    commission_rate = Column(Numeric(5, 2), nullable=False)
    commission_amount = Column(Numeric(10, 2), nullable=False)

    status = Column(String(20), default="accrued")  # accrued, pending_payout, paid

    accrued_at = Column(DateTime(timezone=True), server_default=func.now())
    paid_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    partner = relationship("User", foreign_keys=[partner_id], backref="commissions_received")
    payer = relationship("User", foreign_keys=[payer_id])
    transaction = relationship("PaymentTransaction", backref="commissions")


class LeaderPoolEntry(Base):
    """
    Leader pool entries (5%).
    Distributed manually by admin each month.
    """
    __tablename__ = "leader_pool_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    period_year = Column(Integer, nullable=False)
    period_month = Column(Integer, nullable=False)

    total_pool_amount = Column(Numeric(10, 2), default=0)

    partner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    amount = Column(Numeric(10, 2), nullable=True)
    rank_position = Column(Integer, nullable=True)

    status = Column(String(20), default="accumulated")  # accumulated, distributed, paid

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    distributed_at = Column(DateTime(timezone=True), nullable=True)
