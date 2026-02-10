from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest
from app.services.referral_service import update_partner_status
from app.utils.helpers import generate_referral_code
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    # Check email uniqueness
    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    if len(body.password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 6 characters",
        )

    # Generate unique referral code
    ref_code = generate_referral_code(db)

    # Handle referrer
    referred_by_id = None
    if body.referral_code:
        referrer = db.query(User).filter(
            User.referral_code == body.referral_code.upper()
        ).first()
        if not referrer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Referral code not found",
            )
        referred_by_id = referrer.id

    # Create user
    user = User(
        email=body.email.lower(),
        password_hash=hash_password(body.password),
        first_name=body.first_name,
        referral_code=ref_code,
        referred_by_id=referred_by_id,
    )
    db.add(user)
    db.flush()

    # Self-referral protection (shouldn't happen but just in case)
    if referred_by_id and user.id == referred_by_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot refer yourself",
        )

    # Update referrer's partner status
    if referred_by_id:
        update_partner_status(db, referred_by_id)

    db.commit()
    db.refresh(user)

    token = create_access_token(str(user.id), user.email)

    return {
        "token": token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "referral_code": user.referral_code,
        },
    }


@router.post("/login")
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    # Update last login
    user.last_login = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(str(user.id), user.email)

    return {
        "token": token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "first_name": user.first_name,
            "referral_code": user.referral_code,
            "is_admin": user.is_admin,
        },
    }
