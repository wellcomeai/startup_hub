from pydantic import BaseModel


class CreatePaymentRequest(BaseModel):
    plan_code: str
    billing_period: str  # monthly or yearly


class ActivateTestRequest(BaseModel):
    plan_code: str
    months: int = 1
