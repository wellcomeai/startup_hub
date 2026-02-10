import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.referral import LeaderPoolEntry, ReferralCommission
from app.models.subscription import PaymentTransaction, SubscriptionPlan, UserSubscription
from app.models.user import User

logger = logging.getLogger(__name__)


def process_referral_commissions(
    db: Session,
    transaction: PaymentTransaction,
    user: User,
    plan: SubscriptionPlan,
    subscription: UserSubscription,
) -> List[ReferralCommission]:
    """
    Called after each successful payment.
    Walks up the referral tree and accrues commissions.
    """
    commissions = []
    payment_amount = transaction.amount

    # Level 1 - Direct referrer (30%)
    if user.referred_by_id is not None:
        partner = db.query(User).filter(User.id == user.referred_by_id).first()
        if partner:
            rate = plan.commission_direct
            amount = Decimal(str(payment_amount)) * rate / Decimal("100")
            c = ReferralCommission(
                partner_id=partner.id,
                payer_id=user.id,
                transaction_id=transaction.id,
                commission_type="direct",
                referral_level=1,
                payment_amount=payment_amount,
                commission_rate=rate,
                commission_amount=amount,
            )
            db.add(c)
            commissions.append(c)

            # Level 2 - Referrer's referrer (15%)
            if partner.referred_by_id is not None:
                level2_partner = db.query(User).filter(
                    User.id == partner.referred_by_id
                ).first()
                if level2_partner:
                    rate2 = plan.commission_level2
                    amount2 = Decimal(str(payment_amount)) * rate2 / Decimal("100")
                    c2 = ReferralCommission(
                        partner_id=level2_partner.id,
                        payer_id=user.id,
                        transaction_id=transaction.id,
                        commission_type="level2",
                        referral_level=2,
                        payment_amount=payment_amount,
                        commission_rate=rate2,
                        commission_amount=amount2,
                    )
                    db.add(c2)
                    commissions.append(c2)

            # Retention bonus (10%) - only if consecutive_months >= 2
            if subscription.consecutive_months >= 2:
                rate_ret = plan.commission_retention
                amount_ret = Decimal(str(payment_amount)) * rate_ret / Decimal("100")
                c_ret = ReferralCommission(
                    partner_id=partner.id,
                    payer_id=user.id,
                    transaction_id=transaction.id,
                    commission_type="retention",
                    referral_level=1,
                    payment_amount=payment_amount,
                    commission_rate=rate_ret,
                    commission_amount=amount_ret,
                )
                db.add(c_ret)
                commissions.append(c_ret)

    # Leader pool (5%)
    pool_rate = plan.commission_leader_pool
    pool_amount = Decimal(str(payment_amount)) * pool_rate / Decimal("100")
    now = datetime.now(timezone.utc)

    pool_entry = (
        db.query(LeaderPoolEntry)
        .filter(
            LeaderPoolEntry.period_year == now.year,
            LeaderPoolEntry.period_month == now.month,
            LeaderPoolEntry.partner_id.is_(None),
        )
        .first()
    )
    if pool_entry:
        pool_entry.total_pool_amount = (
            Decimal(str(pool_entry.total_pool_amount)) + pool_amount
        )
    else:
        pool_entry = LeaderPoolEntry(
            period_year=now.year,
            period_month=now.month,
            total_pool_amount=pool_amount,
        )
        db.add(pool_entry)

    logger.info(
        f"Processed {len(commissions)} commissions for transaction {transaction.id}"
    )
    return commissions


def update_partner_status(db: Session, user_id: UUID):
    """
    Recalculate partner status based on direct referral count.
    Called after a new referral registers.
    """
    count = db.query(User).filter(User.referred_by_id == user_id).count()

    if count >= 100:
        status = "platinum"
    elif count >= 50:
        status = "gold"
    elif count >= 20:
        status = "silver"
    elif count >= 5:
        status = "bronze"
    else:
        status = "none"

    user = db.query(User).filter(User.id == user_id).first()
    if user and user.partner_status != status:
        user.partner_status = status
        db.flush()
