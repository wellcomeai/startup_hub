"""
Payment callback endpoints for Robokassa integration.

These endpoints handle:
  - Result URL (server-to-server callback from Robokassa)
  - Success URL (user redirect after successful payment)
  - Fail URL (user redirect after failed/cancelled payment)
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.subscription import PaymentTransaction
from app.services.payment_service import verify_result_signature
from app.services.subscription_service import activate_subscription_from_payment

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/result", response_class=PlainTextResponse)
@router.get("/result", response_class=PlainTextResponse)
async def payment_result(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Robokassa Result URL callback.

    Called server-to-server by Robokassa after successful payment.
    Must return "OK{InvId}" on success, otherwise Robokassa will retry.

    NO authentication — Robokassa calls this directly.
    Verified by MD5 signature using Password2.
    """
    # Parse parameters from GET or POST
    if request.method == "POST":
        form_data = await request.form()
        params = dict(form_data)
    else:
        params = dict(request.query_params)

    out_sum = params.get("OutSum", "")
    inv_id = params.get("InvId", "")
    signature = params.get("SignatureValue", "")

    # Log the callback for audit
    logger.info(
        f"Robokassa Result callback: InvId={inv_id}, OutSum={out_sum}, "
        f"IP={request.client.host}"
    )

    # --- 1. Verify signature ---
    if not verify_result_signature(out_sum, inv_id, signature):
        logger.error(f"Invalid signature for InvId={inv_id}")
        return PlainTextResponse(
            content="bad sign",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # --- 2. Find the transaction ---
    try:
        invoice_number = int(inv_id)
    except (ValueError, TypeError):
        logger.error(f"Invalid InvId format: {inv_id}")
        return PlainTextResponse(
            content="bad invid",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # Lock the row to prevent double-processing
    transaction = (
        db.query(PaymentTransaction)
        .filter(PaymentTransaction.invoice_number == invoice_number)
        .with_for_update()
        .first()
    )

    if not transaction:
        logger.error(f"Transaction not found for InvId={inv_id}")
        return PlainTextResponse(
            content="not found",
            status_code=status.HTTP_404_NOT_FOUND,
        )

    # --- 3. Idempotency: already processed ---
    if transaction.status == "success":
        logger.info(f"Transaction {inv_id} already processed, returning OK")
        return PlainTextResponse(content=f"OK{inv_id}")

    if transaction.status != "pending":
        logger.warning(
            f"Transaction {inv_id} has unexpected status: {transaction.status}"
        )
        return PlainTextResponse(
            content="bad status",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # --- 4. Validate amount (Decimal comparison, tolerant to trailing zeros) ---
    try:
        received_amount = Decimal(out_sum).quantize(Decimal("0.01"))
        expected_amount = transaction.amount.quantize(Decimal("0.01"))
    except (InvalidOperation, AttributeError) as e:
        logger.error(f"Cannot parse amount for InvId={inv_id}: OutSum={out_sum}, error={e}")
        return PlainTextResponse(
            content="bad amount",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if received_amount != expected_amount:
        logger.error(
            f"Amount mismatch for InvId={inv_id}: "
            f"expected={expected_amount}, received={received_amount}"
        )
        return PlainTextResponse(
            content="bad amount",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    # --- 5. Mark as paid ---
    transaction.status = "success"
    transaction.paid_at = datetime.now(timezone.utc)
    transaction.callback_data = params
    db.flush()

    # --- 6. Activate subscription and commissions ---
    try:
        activate_subscription_from_payment(db, transaction)
        db.commit()
        logger.info(f"Payment processed successfully: InvId={inv_id}")
    except Exception as e:
        db.rollback()
        logger.exception(f"Failed to activate subscription for InvId={inv_id}: {e}")
        return PlainTextResponse(
            content="internal error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Robokassa expects exactly "OK{InvId}" to confirm receipt
    return PlainTextResponse(content=f"OK{inv_id}")


@router.get("/success", response_class=HTMLResponse)
async def payment_success(
    InvId: str = Query(""),
    OutSum: str = Query(""),
    db: Session = Depends(get_db),
):
    """
    Robokassa Success URL — user is redirected here after payment.

    This is a user-facing page, NOT the server callback.
    The actual payment confirmation happens via /result.
    """
    app_url = settings.APP_URL.rstrip("/")

    # Try to get transaction info for a nice message
    plan_name = ""
    if InvId:
        try:
            transaction = (
                db.query(PaymentTransaction)
                .filter(PaymentTransaction.invoice_number == int(InvId))
                .first()
            )
            if transaction:
                plan_name = transaction.plan_code
        except (ValueError, TypeError):
            pass

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Оплата успешна — AI Community Club</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
            color: #fff; display: flex; justify-content: center; align-items: center;
            min-height: 100vh; padding: 20px;
        }}
        .card {{
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px; padding: 48px; text-align: center; max-width: 480px;
        }}
        .icon {{ font-size: 64px; margin-bottom: 24px; }}
        h1 {{ font-size: 24px; margin-bottom: 12px; }}
        p {{ color: rgba(255,255,255,0.7); margin-bottom: 24px; line-height: 1.6; }}
        .btn {{
            display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #6c5ce7, #a855f7);
            color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600;
            transition: transform 0.2s;
        }}
        .btn:hover {{ transform: translateY(-2px); }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">✅</div>
        <h1>Оплата прошла успешно!</h1>
        <p>
            Ваша подписка{' «' + plan_name + '»' if plan_name else ''} активирована.
            Спасибо за покупку!
        </p>
        <a href="{app_url}/static/dashboard.html" class="btn">Перейти в личный кабинет</a>
    </div>
    <script>
        // Auto-redirect after 5 seconds
        setTimeout(function() {{
            window.location.href = '{app_url}/static/dashboard.html';
        }}, 5000);
    </script>
</body>
</html>"""

    return HTMLResponse(content=html)


@router.get("/fail", response_class=HTMLResponse)
async def payment_fail(
    InvId: str = Query(""),
    OutSum: str = Query(""),
    db: Session = Depends(get_db),
):
    """
    Robokassa Fail URL — user is redirected here if payment fails or is cancelled.
    """
    app_url = settings.APP_URL.rstrip("/")

    # Mark transaction as failed if it exists and is still pending
    if InvId:
        try:
            transaction = (
                db.query(PaymentTransaction)
                .filter(
                    PaymentTransaction.invoice_number == int(InvId),
                    PaymentTransaction.status == "pending",
                )
                .first()
            )
            if transaction:
                transaction.status = "failed"
                db.commit()
        except (ValueError, TypeError):
            pass

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ошибка оплаты — AI Community Club</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #0f0f23 0%, #1a1a3e 100%);
            color: #fff; display: flex; justify-content: center; align-items: center;
            min-height: 100vh; padding: 20px;
        }}
        .card {{
            background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 16px; padding: 48px; text-align: center; max-width: 480px;
        }}
        .icon {{ font-size: 64px; margin-bottom: 24px; }}
        h1 {{ font-size: 24px; margin-bottom: 12px; }}
        p {{ color: rgba(255,255,255,0.7); margin-bottom: 24px; line-height: 1.6; }}
        .btn {{
            display: inline-block; padding: 14px 32px; background: linear-gradient(135deg, #6c5ce7, #a855f7);
            color: #fff; text-decoration: none; border-radius: 8px; font-weight: 600;
            transition: transform 0.2s; margin: 0 8px;
        }}
        .btn-outline {{
            background: transparent; border: 1px solid rgba(255,255,255,0.3);
        }}
        .btn:hover {{ transform: translateY(-2px); }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">❌</div>
        <h1>Оплата не прошла</h1>
        <p>
            Платёж был отменён или произошла ошибка.
            Средства не были списаны. Вы можете попробовать снова.
        </p>
        <a href="{app_url}/static/dashboard.html" class="btn">В личный кабинет</a>
    </div>
</body>
</html>"""

    return HTMLResponse(content=html)
