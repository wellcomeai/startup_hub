from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.referral import ReferralCommission
from app.models.subscription import UserSubscription
from app.models.user import User
from app.schemas.user import SetReferrerRequest, UserUpdate
from app.services.auth_service import get_current_user
from app.services.referral_service import update_partner_status

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Referrer info
    referred_by = None
    if current_user.referred_by_id:
        ref = db.query(User).filter(User.id == current_user.referred_by_id).first()
        if ref:
            referred_by = {
                "id": str(ref.id),
                "first_name": ref.first_name,
                "email": ref.email,
            }

    # Active subscription
    subscription = None
    active_sub = (
        db.query(UserSubscription)
        .filter(
            UserSubscription.user_id == current_user.id,
            UserSubscription.status == "active",
        )
        .first()
    )
    if active_sub:
        subscription = {
            "plan_code": active_sub.plan.code,
            "plan_name": active_sub.plan.name,
            "status": active_sub.status,
            "expires_at": active_sub.expires_at.isoformat() if active_sub.expires_at else None,
            "billing_period": active_sub.billing_period,
            "consecutive_months": active_sub.consecutive_months,
        }

    # Referral stats
    level1_count = db.query(User).filter(User.referred_by_id == current_user.id).count()

    # Level 2: referrals of my referrals
    level1_ids = [
        r.id
        for r in db.query(User.id).filter(User.referred_by_id == current_user.id).all()
    ]
    level2_count = 0
    if level1_ids:
        level2_count = db.query(User).filter(User.referred_by_id.in_(level1_ids)).count()

    # Paid referrals (those who have at least one active subscription)
    total_paid_referrals = 0
    if level1_ids:
        total_paid_referrals = (
            db.query(UserSubscription.user_id)
            .filter(
                UserSubscription.user_id.in_(level1_ids),
                UserSubscription.status == "active",
            )
            .distinct()
            .count()
        )

    # Commission totals
    total_earned = (
        db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
        .filter(ReferralCommission.partner_id == current_user.id)
        .scalar()
    )
    total_paid = (
        db.query(sqlfunc.coalesce(sqlfunc.sum(ReferralCommission.commission_amount), 0))
        .filter(
            ReferralCommission.partner_id == current_user.id,
            ReferralCommission.status == "paid",
        )
        .scalar()
    )

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
        "telegram": current_user.telegram,
        "city": current_user.city,
        "about": current_user.about,
        "referral_code": current_user.referral_code,
        "partner_status": current_user.partner_status,
        "is_admin": current_user.is_admin,
        "referred_by": referred_by,
        "subscription": subscription,
        "stats": {
            "total_referrals_level1": level1_count,
            "total_referrals_level2": level2_count,
            "total_paid_referrals": total_paid_referrals,
            "total_commissions_earned": float(total_earned),
            "total_commissions_paid": float(total_paid),
        },
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
    }


@router.put("/me")
def update_profile(
    body: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(current_user, field, value)

    db.commit()
    db.refresh(current_user)

    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
        "telegram": current_user.telegram,
        "city": current_user.city,
        "about": current_user.about,
        "referral_code": current_user.referral_code,
        "partner_status": current_user.partner_status,
    }


@router.post("/me/set-referrer")
def set_referrer(
    body: SetReferrerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check if referrer is already set
    if current_user.referred_by_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Реферер уже установлен и не может быть изменён",
        )

    # Find referrer by code
    referrer = db.query(User).filter(
        User.referral_code == body.referral_code.upper()
    ).first()
    if not referrer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь с таким кодом не найден",
        )

    # Self-referral protection
    if referrer.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя указать свой собственный код",
        )

    # Cycle protection: cannot refer to someone who is in your downline
    if referrer.referred_by_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Невозможно создать циклическую связь рефералов",
        )

    # Use SELECT FOR UPDATE for atomicity
    user_to_update = (
        db.query(User)
        .filter(User.id == current_user.id)
        .with_for_update()
        .first()
    )

    # Double-check after lock
    if user_to_update.referred_by_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Реферер уже установлен и не может быть изменён",
        )

    user_to_update.referred_by_id = referrer.id

    # Update referrer's partner status
    update_partner_status(db, referrer.id)

    db.commit()

    return {
        "success": True,
        "referred_by": {
            "first_name": referrer.first_name,
            "referral_code": referrer.referral_code,
        },
    }
