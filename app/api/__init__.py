from fastapi import APIRouter

from app.api.admin import router as admin_router
from app.api.auth import router as auth_router
from app.api.payments import router as payments_router
from app.api.referrals import router as referrals_router
from app.api.subscriptions import router as subscriptions_router
from app.api.users import router as users_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(referrals_router)
api_router.include_router(subscriptions_router)
api_router.include_router(payments_router)
api_router.include_router(admin_router)
