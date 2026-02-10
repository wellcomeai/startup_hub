"""
Subscription endpoints — plans, current subscription, payment creation, test activation.
"""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.subscription import PaymentTransaction, SubscriptionPlan, UserSubscription
from app.models.user import User
from app.schemas.subscription import ActivateTestRequest, CreatePaymentRequest
from app.services.auth_service import get_current_user
from app.services.payment_service import build_receipt_items, generate_payment_url
from app.services.subscription_service import activate_subscription_test, get_active_subscription

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])


@router.get("/plans")
def get_plans(db: Session = Depends(get_db)):
    plans = (
        db.query(SubscriptionPlan)
        .filter(SubscriptionPlan.is_active.is_(True))
        .order_by(SubscriptionPlan.sort_order)
        .all()
    )

    return {
        "plans": [
            {
                "code": p.code,
                "name": p.name,
                "price_monthly": float(p.price_monthly),
                "price_yearly": float(p.price_yearly),
                "yearly_savings": float(p.price_monthly * 12 - p.price_yearly),
                "features": p.features or [],
                "max_voicyfy_agents": p.max_voicyfy_agents,
                "max_chatforyou_access": p.max_chatforyou_access,
                "max_ai_admin_bots": p.max_ai_admin_bots,
                "description": p.description,
            }
            for p in plans
        ]
    }


@router.get("/my")
def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = get_active_subscription(db, current_user.id)
    if not sub:
        return {"has_subscription": False, "subscription": None}

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    days_remaining = (sub.expires_at - now).days if sub.expires_at else 0

    return {
        "has_subscription": True,
        "subscription": {
            "plan_code": sub.plan.code,
            "plan_name": sub.plan.name,
            "status": sub.status,
            "billing_period": sub.billing_period,
            "started_at": sub.started_at.isoformat() if sub.started_at else None,
            "expires_at": sub.expires_at.isoformat() if sub.expires_at else None,
            "consecutive_months": sub.consecutive_months,
            "days_remaining": max(0, days_remaining),
        },
    }


@router.post("/create-payment")
def create_payment(
    body: CreatePaymentRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a payment and return the Robokassa payment URL.

    The user should be redirected to the returned URL to complete payment.
    After payment, Robokassa calls /api/payments/result to confirm.
    """
    # --- Validate plan ---
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.code == body.plan_code,
            SubscriptionPlan.is_active.is_(True),
        )
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тариф не найден",
        )

    if body.billing_period not in ("monthly", "yearly"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="billing_period должен быть 'monthly' или 'yearly'",
        )

    # --- Calculate amount ---
    if body.billing_period == "yearly":
        amount = plan.price_yearly
        months_count = 12
    else:
        amount = plan.price_monthly
        months_count = 1

    # --- Check Robokassa config ---
    if not settings.ROBOKASSA_MERCHANT_LOGIN or not settings.ROBOKASSA_PASSWORD_1:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Платёжная система не настроена. Используйте /activate-test для тестирования.",
        )

    # --- Cancel any existing pending payments for this user ---
    pending_transactions = (
        db.query(PaymentTransaction)
        .filter(
            PaymentTransaction.user_id == current_user.id,
            PaymentTransaction.status == "pending",
        )
        .all()
    )
    for pt in pending_transactions:
        pt.status = "cancelled"
    db.flush()

    # --- Create payment transaction ---
    transaction = PaymentTransaction(
        user_id=current_user.id,
        amount=Decimal(str(amount)),
        currency="RUB",
        billing_period=body.billing_period,
        months_count=months_count,
        plan_code=plan.code,
        payment_system="robokassa",
        status="pending",
    )
    db.add(transaction)
    db.flush()  # This generates the invoice_number via the sequence

    # --- Build receipt items for 54-FZ ---
    receipt_items = build_receipt_items(plan.name, Decimal(str(amount)), months_count)

    # --- Generate Robokassa URL ---
    period_label = "год" if body.billing_period == "yearly" else "мес"
    description = f"AI Community Club: {plan.name} ({period_label})"

    payment_url = generate_payment_url(
        amount=Decimal(str(amount)),
        invoice_id=transaction.invoice_number,
        description=description,
        email=current_user.email,
        receipt_items=receipt_items,
    )

    db.commit()

    return {
        "payment_url": payment_url,
        "invoice_number": transaction.invoice_number,
        "transaction_id": str(transaction.id),
        "amount": float(amount),
        "currency": "RUB",
        "billing_period": body.billing_period,
        "plan": plan.code,
    }


@router.post("/activate-test")
def activate_test(
    body: ActivateTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test activation of a subscription without payment."""
    plan = (
        db.query(SubscriptionPlan)
        .filter(
            SubscriptionPlan.code == body.plan_code,
            SubscriptionPlan.is_active.is_(True),
        )
        .first()
    )
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Тариф не найден",
        )

    if body.months < 1 or body.months > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="months должно быть от 1 до 12",
        )

    result = activate_subscription_test(db, current_user, plan, body.months)
    return result
