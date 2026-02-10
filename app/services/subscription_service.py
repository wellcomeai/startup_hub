from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.subscription import PaymentTransaction, SubscriptionPlan, UserSubscription
from app.models.user import User
from app.services.referral_service import process_referral_commissions


def get_active_subscription(db: Session, user_id) -> UserSubscription | None:
    """Get user's active subscription."""
    return (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == user_id,
            UserSubscription.status == "active",
        )
        .first()
    )


def activate_subscription_test(
    db: Session, user: User, plan: SubscriptionPlan, months: int = 1
) -> dict:
    """
    Test activation of a subscription without payment.
    Creates subscription + transaction + processes commissions.
    """
    now = datetime.now(timezone.utc)

    # Check for existing active subscription
    existing = get_active_subscription(db, user.id)
    consecutive = 1
    if existing:
        consecutive = existing.consecutive_months + months
        existing.status = "expired"
        db.flush()

    # Create subscription
    subscription = UserSubscription(
        user_id=user.id,
        plan_id=plan.id,
        billing_period="monthly",
        status="active",
        started_at=now,
        expires_at=now + timedelta(days=30 * months),
        consecutive_months=consecutive,
    )
    db.add(subscription)
    db.flush()

    # Determine price
    amount = plan.price_monthly * months

    # Create payment transaction
    transaction = PaymentTransaction(
        user_id=user.id,
        subscription_id=subscription.id,
        amount=Decimal(str(amount)),
        currency="RUB",
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
        "commissions_created": len(commissions),
        "consecutive_months": consecutive,
    }
