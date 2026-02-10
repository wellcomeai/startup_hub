from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.referral import ReferralCommission
from app.models.subscription import UserSubscription
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/referrals", tags=["referrals"])


@router.get("/my-team")
def get_my_team(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    # Level 1 - direct referrals
    level1_users = (
        db.query(User)
        .filter(User.referred_by_id == current_user.id)
        .order_by(User.created_at.desc())
        .all()
    )

    level1_data = []
    level1_ids = []
    for u in level1_users:
        level1_ids.append(u.id)
        # Get active subscription
        sub = (
            db.query(UserSubscription)
            .filter(
                UserSubscription.user_id == u.id,
                UserSubscription.status == "active",
            )
            .first()
        )
        # Get total commission from this user
        my_commission = (
            db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
            .filter(
                ReferralCommission.partner_id == current_user.id,
                ReferralCommission.payer_id == u.id,
            )
            .scalar()
        )
        level1_data.append({
            "id": str(u.id),
            "first_name": u.first_name,
            "last_name": u.last_name,
            "email": u.email,
            "registered_at": u.created_at.isoformat() if u.created_at else None,
            "has_active_subscription": sub is not None,
            "subscription_plan": sub.plan.code if sub else None,
            "consecutive_months": sub.consecutive_months if sub else 0,
            "my_commission_from_user": float(my_commission),
        })

    # Level 2 - referrals of referrals
    level2_data = []
    level2_count = 0
    level2_paid_count = 0
    if level1_ids:
        level2_users = (
            db.query(User)
            .filter(User.referred_by_id.in_(level1_ids))
            .order_by(User.created_at.desc())
            .all()
        )
        for u in level2_users:
            level2_count += 1
            sub = (
                db.query(UserSubscription)
                .filter(
                    UserSubscription.user_id == u.id,
                    UserSubscription.status == "active",
                )
                .first()
            )
            if sub:
                level2_paid_count += 1

            invited_by = db.query(User).filter(User.id == u.referred_by_id).first()
            my_commission = (
                db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
                .filter(
                    ReferralCommission.partner_id == current_user.id,
                    ReferralCommission.payer_id == u.id,
                )
                .scalar()
            )
            level2_data.append({
                "id": str(u.id),
                "first_name": u.first_name,
                "email": u.email,
                "registered_at": u.created_at.isoformat() if u.created_at else None,
                "has_active_subscription": sub is not None,
                "invited_by": {
                    "first_name": invited_by.first_name if invited_by else None,
                    "referral_code": invited_by.referral_code if invited_by else None,
                },
                "my_commission_from_user": float(my_commission),
            })

    # Count paid level1
    level1_paid_count = sum(1 for u in level1_data if u["has_active_subscription"])

    return {
        "level1": level1_data,
        "level2": level2_data,
        "totals": {
            "level1_count": len(level1_data),
            "level1_paid_count": level1_paid_count,
            "level2_count": level2_count,
            "level2_paid_count": level2_paid_count,
            "total_team_size": len(level1_data) + level2_count,
        },
    }


@router.get("/my-commissions")
def get_my_commissions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    commission_type: str = Query("all"),
):
    query = db.query(ReferralCommission).filter(
        ReferralCommission.partner_id == current_user.id
    )

    if commission_type != "all":
        query = query.filter(ReferralCommission.commission_type == commission_type)

    total_items = query.count()
    commissions = (
        query.order_by(ReferralCommission.accrued_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )

    items = []
    for c in commissions:
        payer = db.query(User).filter(User.id == c.payer_id).first()
        items.append({
            "id": str(c.id),
            "commission_type": c.commission_type,
            "referral_level": c.referral_level,
            "payer": {
                "first_name": payer.first_name if payer else None,
                "email": payer.email if payer else None,
            },
            "payment_amount": float(c.payment_amount),
            "commission_rate": float(c.commission_rate),
            "commission_amount": float(c.commission_amount),
            "status": c.status,
            "accrued_at": c.accrued_at.isoformat() if c.accrued_at else None,
            "paid_at": c.paid_at.isoformat() if c.paid_at else None,
        })

    # Summary
    total_earned = float(
        db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
        .filter(ReferralCommission.partner_id == current_user.id)
        .scalar()
    )
    total_paid = float(
        db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
        .filter(
            ReferralCommission.partner_id == current_user.id,
            ReferralCommission.status == "paid",
        )
        .scalar()
    )

    by_type = {}
    for ct in ["direct", "level2", "retention"]:
        by_type[ct] = float(
            db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
            .filter(
                ReferralCommission.partner_id == current_user.id,
                ReferralCommission.commission_type == ct,
            )
            .scalar()
        )

    return {
        "commissions": items,
        "summary": {
            "total_earned": total_earned,
            "total_paid": total_paid,
            "total_pending": total_earned - total_paid,
            "by_type": by_type,
        },
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": total_items,
            "total_pages": (total_items + per_page - 1) // per_page if per_page else 0,
        },
    }


@router.get("/my-link")
def get_my_link(
    current_user: User = Depends(get_current_user),
):
    base_url = settings.APP_URL.rstrip("/")
    return {
        "referral_code": current_user.referral_code,
        "referral_link": f"{base_url}/?ref={current_user.referral_code}",
        "utm_link": f"{base_url}/?utm_source=partner&utm_medium=referral&utm_campaign={current_user.referral_code}",
    }
