"""
Robokassa integration - stub for future implementation.
"""


def generate_payment_url(merchant_login: str, amount: float, invoice_id: str, description: str) -> str:
    """Generate Robokassa payment URL. Stub."""
    return f"https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin={merchant_login}&OutSum={amount}&InvId={invoice_id}&Description={description}"


def verify_payment_signature(received_signature: str, amount: float, invoice_id: str, password: str) -> bool:
    """Verify Robokassa callback signature. Stub."""
    return False
