from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.subscription import SubscriptionPlan, UserSubscription
from app.models.user import User
from app.schemas.subscription import ActivateTestRequest, CreatePaymentRequest
from app.services.auth_service import get_current_user
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
    """Stub for payment creation. Robokassa integration will be added later."""
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.code == body.plan_code,
        SubscriptionPlan.is_active.is_(True),
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    if body.billing_period not in ("monthly", "yearly"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="billing_period must be 'monthly' or 'yearly'",
        )

    amount = float(plan.price_monthly) if body.billing_period == "monthly" else float(plan.price_yearly)

    return {
        "message": "Payment system not yet connected. Use /activate-test for testing.",
        "plan": plan.code,
        "amount": amount,
        "currency": "RUB",
    }


@router.post("/activate-test")
def activate_test(
    body: ActivateTestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Test activation of a subscription without payment."""
    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.code == body.plan_code,
        SubscriptionPlan.is_active.is_(True),
    ).first()

    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    if body.months < 1 or body.months > 12:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="months must be between 1 and 12",
        )

    result = activate_subscription_test(db, current_user, plan, body.months)
    return result
