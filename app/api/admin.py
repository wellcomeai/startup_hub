from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.referral import LeaderPoolEntry, ReferralCommission
from app.models.subscription import PaymentTransaction, SubscriptionPlan, UserSubscription
from app.models.user import User
from app.services.auth_service import get_admin_user

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def list_users(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    search: str = Query(""),
):
    query = db.query(User)
    if search:
        query = query.filter(
            User.email.ilike(f"%{search}%")
            | User.first_name.ilike(f"%{search}%")
            | User.last_name.ilike(f"%{search}%")
        )

    total = query.count()
    users = (
        query.order_by(User.created_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    result = []
    for u in users:
        sub = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == u.id,
                UserSubscription.status == "active",
            )
            .first()
        )
        referrals_count = db.query(User).filter(User.referred_by_id == u.id).count()
        result.append({
            "id": str(u.id),
            "email": u.email,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "referral_code": u.referral_code,
            "partner_status": u.partner_status,
            "is_admin": u.is_admin,
            "is_active": u.is_active,
            "subscription": sub.plan.code if sub else None,
            "referrals_count": referrals_count,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        })

    return {
        "users": result,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total,
            "total_pages": (total + per_page - 1) // per_page if per_page else 0,
        },
    }


@router.get("/stats")
def get_stats(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    total_users = db.query(User).count()

    total_paid_users = (
        db.query(UserSubscription.user_id)
        .filter(UserSubscription.status == "active")
        .distinct()
        .count()
    )

    total_revenue = float(
        db.query(sqlfunc.coalesce(sqlfunc.sum(PaymentTransaction.amount), 0))
        .filter(PaymentTransaction.status == "success")
        .scalar()
    )

    total_commissions_accrued = float(
        db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
        .scalar()
    )

    total_commissions_paid = float(
        db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
        .filter(ReferralCommission.status == "paid")
        .scalar()
    )

    # Users by plan
    users_by_plan = {}
    plan_counts = (
        db.query(SubscriptionPlan.code, sqlfunc.count(UserSubscription.id))
        .join(UserSubscription, UserSubscription.plan_id == SubscriptionPlan.id)
        .filter(UserSubscription.status == "active")
        .group_by(SubscriptionPlan.code)
        .all()
    )
    for code, count in plan_counts:
        users_by_plan[code] = count

    # Leader pool current month
    now = datetime.now(timezone.utc)
    leader_pool = (
        db.query(sqlfunc.coalesce(sqlfunc.sum(LeaderPoolEntry.total_pool_amount), 0))
        .filter(
            LeaderPoolEntry.period_year == now.year,
            LeaderPoolEntry.period_month == now.month,
        )
        .scalar()
    )

    return {
        "total_users": total_users,
        "total_paid_users": total_paid_users,
        "total_revenue": total_revenue,
        "total_commissions_accrued": total_commissions_accrued,
        "total_commissions_paid": total_commissions_paid,
        "users_by_plan": users_by_plan,
        "leader_pool_current_month": float(leader_pool),
    }


@router.post("/activate-test")
def admin_activate_test(
    body: dict,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Admin endpoint: activate a subscription for any user by email (for testing)."""
    from app.services.subscription_service import activate_subscription_test

    email = body.get("email", "").strip().lower()
    plan_code = body.get("plan_code", "")
    months = body.get("months", 1)

    if not email or not plan_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="email and plan_code are required",
        )

    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with email {email} not found",
        )

    plan = db.query(SubscriptionPlan).filter(
        SubscriptionPlan.code == plan_code,
        SubscriptionPlan.is_active.is_(True),
    ).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Plan {plan_code} not found",
        )

    result = activate_subscription_test(db, user, plan, int(months))
    result["user_email"] = email
    return result


@router.post("/distribute-leader-pool")
def distribute_leader_pool(
    body: dict,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """Manually distribute the leader pool for a given period."""
    period_year = body.get("period_year")
    period_month = body.get("period_month")
    distributions = body.get("distributions", [])

    if not period_year or not period_month:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="period_year and period_month are required",
        )

    for dist in distributions:
        entry = LeaderPoolEntry(
            period_year=period_year,
            period_month=period_month,
            partner_id=dist["user_id"],
            amount=Decimal(str(dist["amount"])),
            rank_position=dist.get("rank"),
            status="distributed",
            distributed_at=datetime.now(timezone.utc),
        )
        db.add(entry)

    db.commit()

    return {"success": True, "distributed_count": len(distributions)}
