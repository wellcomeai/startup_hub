"""
Subscription service — handles activation, expiration, and payment processing.
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.subscription import PaymentTransaction, SubscriptionPlan, UserSubscription
from app.models.user import User
from app.services.referral_service import process_referral_commissions

logger = logging.getLogger(__name__)


def get_active_subscription(db: Session, user_id) -> UserSubscription | None:
    """Get user's active (non-expired) subscription."""
    now = datetime.now(timezone.utc)
    sub = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active",
        )
        .first()
    )
    # Auto-expire if past expiration date
    if sub and sub.expires_at and sub.expires_at < now:
        sub.status = "expired"
        db.flush()
        logger.info(f"Auto-expired subscription {sub.id} for user {user_id}")
        return None
    return sub


def calculate_subscription_period(
    billing_period: str,
    now: datetime | None = None,
) -> tuple[datetime, datetime, int]:
    """
    Calculate start, end dates, and months count for a billing period.

    Returns
    -------
    tuple of (started_at, expires_at, months_count)
    """
    if now is None:
        now = datetime.now(timezone.utc)

    if billing_period == "yearly":
        return now, now + timedelta(days=365), 12
    else:
        return now, now + timedelta(days=30), 1


def activate_subscription_from_payment(
    db: Session,
    transaction: PaymentTransaction,
) -> UserSubscription:
    """
    Activate a subscription after successful Robokassa payment.

    This is called from the Result URL callback handler.
    """
    user = db.query(User).filter(User.id == transaction.user_id).first()
    if not user:
        raise ValueError(f"User {transaction.user_id} not found")

    plan = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.code == transaction.plan_code)
        .first()
    )
    if not plan:
        raise ValueError(f"Plan {transaction.plan_code} not found")

    now = datetime.now(timezone.utc)
    months_count = transaction.months_count
    billing_period = transaction.billing_period

    # Handle existing active subscription
    existing = get_active_subscription(db, user.id)
    consecutive = months_count
    if existing:
        consecutive = existing.consecutive_months + months_count
        existing.status = "expired"
        db.flush()

    # Calculate period
    started_at, expires_at, _ = calculate_subscription_period(billing_period, now)

    # Create subscription
    subscription = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        billing_period=billing_period,
        status="active",
        started_at=started_at,
        expires_at=expires_at,
        consecutive_months=consecutive,
    )
    db.add(subscription)
    db.flush()

    # Link transaction to subscription
    transaction.subscription_id = subscription.id
    transaction.subscription_month_number = consecutive
    db.flush()

    # Process referral commissions (lump sum for yearly)
    commissions = process_referral_commissions(
        db, transaction, user, plan, subscription
    )

    logger.info(
        f"Activated subscription for user {user.id}: "
        f"plan={plan.code}, period={billing_period}, "
        f"months={months_count}, commissions={len(commissions)}"
    )

    return subscription


def activate_subscription_test(
    db: Session, user: User, plan: SubscriptionPlan, months: int = 1
) -> dict:
    """
    Test activation of a subscription without payment.
    Creates subscription + transaction + processes commissions.
    """
    now = datetime.now(timezone.utc)

    # Determine billing period
    billing_period = "yearly" if months >= 12 else "monthly"
    months_count = 12 if months >= 12 else months

    # Check for existing active subscription
    existing = get_active_subscription(db, user.id)
    consecutive = months_count
    if existing:
        consecutive = existing.consecutive_months + months_count
        existing.status = "expired"
        db.flush()

    # Calculate dates
    if billing_period == "yearly":
        expires_at = now + timedelta(days=365)
    else:
        expires_at = now + timedelta(days=30 * months)

    # Create subscription
    subscription = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        billing_period=billing_period,
        status="active",
        started_at=now,
        expires_at=expires_at,
        consecutive_months=consecutive,
    )
    db.add(subscription)
    db.flush()

    # Determine price
    if billing_period == "yearly":
        amount = plan.price_yearly
    else:
        amount = plan.price_monthly * months

    # Create payment transaction
    transaction = PaymentTransaction(
        user_id=user.id,
        subscription_id=subscription.id,
        amount=Decimal(str(amount)),
        currency="RUB",
        billing_period=billing_period,
        months_count=months_count,
        plan_code=plan.code,
        payment_system="test",
        status="success",
        subscription_month_number=consecutive,
        paid_at=now,
    )
    db.add(transaction)
    db.flush()

    # Process referral commissions
    commissions = process_referral_commissions(
        db, transaction, user, plan, subscription
    )

    db.commit()

    return {
        "subscription_id": str(subscription.id),
        "transaction_id": str(transaction.id),
        "amount": float(amount),
        "billing_period": billing_period,
        "months_count": months_count,
        "commissions_created": len(commissions),
        "consecutive_months": consecutive,
    }
