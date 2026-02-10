"""
Robokassa Payment Service — production integration.

Handles:
  - Payment URL generation with MD5 signature
  - Callback signature verification
  - Receipt generation for 54-FZ fiscal compliance
"""

import hashlib
import json
import logging
from decimal import Decimal
from urllib.parse import urlencode

from app.config import settings

logger = logging.getLogger(__name__)


def _md5(value: str) -> str:
    """Return the MD5 hex digest of the given string."""
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def generate_payment_url(
    amount: Decimal,
    invoice_id: int,
    description: str,
    email: str | None = None,
    receipt_items: list[dict] | None = None,
) -> str:
    """
    Generate a Robokassa payment URL.

    Parameters
    ----------
    amount : Decimal
        Payment amount in RUB (e.g. 3000.00).
    invoice_id : int
        Unique integer invoice number (InvId).
    description : str
        Payment description shown to the user.
    email : str, optional
        Buyer email for the receipt.
    receipt_items : list[dict], optional
        Items for 54-FZ fiscal receipt.

    Returns
    -------
    str
        Full URL to redirect the user to Robokassa.
    """
    merchant_login = settings.ROBOKASSA_MERCHANT_LOGIN
    password1 = settings.ROBOKASSA_PASSWORD_1

    if not merchant_login or not password1:
        raise ValueError("Robokassa credentials are not configured")

    out_sum = f"{amount:.2f}"

    # --- Receipt (54-FZ) ---
    receipt_param = None
    if receipt_items:
        receipt_obj = {
            "sno": "usn_income",  # Система налогообложения — УСН доходы
            "items": receipt_items,
        }
        receipt_param = json.dumps(receipt_obj, ensure_ascii=False)

    # --- Signature: MerchantLogin:OutSum:InvId:Receipt:Password1 ---
    # If receipt is present it goes into the signature
    if receipt_param:
        sign_string = f"{merchant_login}:{out_sum}:{invoice_id}:{receipt_param}:{password1}"
    else:
        sign_string = f"{merchant_login}:{out_sum}:{invoice_id}:{password1}"

    signature = _md5(sign_string)

    # --- Build URL ---
    if settings.ROBOKASSA_TEST_MODE:
        base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"
    else:
        base_url = "https://auth.robokassa.ru/Merchant/Index.aspx"

    params = {
        "MerchantLogin": merchant_login,
        "OutSum": out_sum,
        "InvId": invoice_id,
        "Description": description,
        "SignatureValue": signature,
        "Culture": "ru",
    }

    if settings.ROBOKASSA_TEST_MODE:
        params["IsTest"] = 1

    if email:
        params["Email"] = email

    if receipt_param:
        params["Receipt"] = receipt_param

    url = f"{base_url}?{urlencode(params)}"

    logger.info(
        f"Generated Robokassa URL: InvId={invoice_id}, amount={out_sum}, "
        f"test_mode={settings.ROBOKASSA_TEST_MODE}"
    )
    return url


def verify_result_signature(out_sum: str, inv_id: str, signature: str) -> bool:
    """
    Verify the signature on Robokassa Result URL callback.

    The expected signature is: MD5(OutSum:InvId:Password2)

    Parameters
    ----------
    out_sum : str
        The OutSum parameter from the callback.
    inv_id : str
        The InvId parameter from the callback.
    signature : str
        The SignatureValue parameter from the callback.

    Returns
    -------
    bool
        True if the signature is valid.
    """
    password2 = settings.ROBOKASSA_PASSWORD_2
    if not password2:
        logger.error("ROBOKASSA_PASSWORD_2 is not configured")
        return False

    expected = _md5(f"{out_sum}:{inv_id}:{password2}")
    result = expected.lower() == signature.lower()

    if not result:
        logger.warning(
            f"Signature mismatch for InvId={inv_id}: "
            f"expected={expected}, received={signature}"
        )

    return result


def build_receipt_items(plan_name: str, amount: Decimal, months: int) -> list[dict]:
    """
    Build a receipt items list for 54-FZ fiscal compliance.

    Parameters
    ----------
    plan_name : str
        Name of the subscription plan.
    amount : Decimal
        Total payment amount.
    months : int
        Number of months (1 or 12).

    Returns
    -------
    list[dict]
        List of receipt item dicts for Robokassa.
    """
    period_label = "годовая" if months == 12 else "месячная"
    item_name = f"Подписка «{plan_name}» ({period_label})"

    return [
        {
            "name": item_name[:128],  # Robokassa limit: 128 chars
            "quantity": 1,
            "sum": float(amount),
            "payment_method": "full_payment",
            "payment_object": "service",
            "tax": "none",  # Без НДС (УСН)
        }
    ]
