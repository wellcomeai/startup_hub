from typing import Optional

from pydantic import BaseModel


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    telegram: Optional[str] = None
    city: Optional[str] = None
    about: Optional[str] = None


class SetReferrerRequest(BaseModel):
    referral_code: str
