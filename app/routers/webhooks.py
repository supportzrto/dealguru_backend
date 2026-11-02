
import hashlib
import hmac
import json

from decimal import Decimal, ROUND_HALF_UP

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.config import settings
from app.core.dependencies import get_db
from app.models.order import Order
from app.models.payment import Payment
from app.models.webhook_event import WebhookEvent


router = APIRouter(prefix="/api/webhooks", tags=["Webhooks"])

SUPPORTED_EVENTS = {"payment.captured", "payment.failed"}


@router.post("/razorpay")
async def razorpay_webhook(
    request: Request,
    db: Session = Depends(get_db),
    signature: str | None = Header(
        default=None,
        alias="X-Razorpay-Signature",
    ),
    event_id: str | None = Header(
        default=None,
        alias="X-Razorpay-Event-Id",
    ),
):
    if not signature:
        raise HTTPException(status_code=400, detail="Missing webhook signature")

    if not event_id:
        raise HTTPException(status_code=400, detail="Missing Razorpay event ID")

    body = await request.body()

    expected_signature = hmac.new(
        settings.razorpay_webhook_secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected_signature, signature):
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    try:
        event = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid webhook payload")

    event_type = event.get("event")

    if not isinstance(event_type, str):
        raise HTTPException(status_code=400, detail="Missing event type")

    try:
        # Insert the event atomically. A repeated event ID is ignored.
        inserted_event = db.execute(
            insert(WebhookEvent)
            .values(
                provider="razorpay",
                event_id=event_id,
                event_type=event_type,
                status="processing",
            )
            .on_conflict_do_nothing(index_elements=["event_id"])
            .returning(WebhookEvent.id)
        ).scalar_one_or_none()

        if inserted_event is None:
            db.rollback()
            return {"status": "duplicate"}

        if event_type not in SUPPORTED_EVENTS:
            db.execute(
                WebhookEvent.__table__.update()
                .where(WebhookEvent.id == inserted_event)
                .values(status="ignored")
            )
            db.commit()
            return {"status": "ignored"}

        payment_entity = (
            event.get("payload", {})
            .get("payment", {})
            .get("entity", {})
        )

        razorpay_payment_id = payment_entity.get("id")
        razorpay_order_id = payment_entity.get("order_id")

        if not razorpay_payment_id or not razorpay_order_id:
            raise HTTPException(
                status_code=400,
                detail="Missing payment details",
            )

        payment = db.scalar(
            select(Payment)
            .where(
                Payment.provider == "razorpay",
                Payment.provider_order_id == razorpay_order_id,
            )
            .with_for_update()
        )

        if not payment:
            db.execute(
                WebhookEvent.__table__.update()
                .where(WebhookEvent.id == inserted_event)
                .values(status="ignored")
            )
            db.commit()
            return {"status": "ignored"}

        order = db.scalar(
            select(Order)
            .where(Order.id == payment.order_id)
            .with_for_update()
        )

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        expected_amount = int(
            (payment.amount * 100).quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )
        )

        if (
            payment_entity.get("amount") != expected_amount
            or payment_entity.get("currency") != payment.currency
            or payment.currency != "INR"
        ):
            raise HTTPException(
                status_code=400,
                detail="Payment amount or currency mismatch",
            )

        if event_type == "payment.captured":

            if payment.status == "paid":
                if payment.provider_payment_id != razorpay_payment_id:
                    raise HTTPException(
                        status_code=409,
                        detail="Different payment already recorded",
                    )

                event_status = "already_processed"

            elif (
                order.payment_status != "pending"
                or order.order_status != "Pending Payment"
            ):
                # Captured payment for a cancelled or changed order.
                # Keep it visible for manual reconciliation/refund.
                event_status = "manual_review_required"

            else:
                payment.provider_payment_id = razorpay_payment_id
                payment.status = "paid"
                payment.method = payment_entity.get("method")

                order.payment_status = "paid"
                order.order_status = "Processing"

                event_status = "processed"

        else:
            # payment.failed
            if payment.status == "paid":
                event_status = "already_paid"

            elif payment.provider_payment_id not in (
                None,
                razorpay_payment_id,
            ):
                event_status = "ignored"

            else:
                payment.provider_payment_id = razorpay_payment_id
                payment.status = "failed"

                event_status = "processed"

        db.execute(
            WebhookEvent.__table__.update()
            .where(WebhookEvent.id == inserted_event)
            .values(status=event_status)
        )

        db.commit()

        return {"status": event_status}

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Webhook processing failed",
        )
