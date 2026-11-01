import razorpay

from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_db, get_current_user, get_current_admin
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User, Address
from app.schemas.order import OrderCreate, OrderResponse
from app.config import settings
from app.models.payment import Payment


router = APIRouter(prefix="/api/orders", tags=["Orders"])

razorpay_client = razorpay.Client(
    auth=(
        settings.razorpay_key_id,
        settings.razorpay_key_secret,
    )
)

ZERO = Decimal("0.00")
GIFT_WRAP_FEE = Decimal("49.00")

# These are the current default frontend coupon rules.
# Move coupon configuration to the backend database later.
COUPONS = {
    "GURU10": {"percent": Decimal("10"), "max_discount": None},
    "WELCOME20": {"percent": Decimal("20"), "max_discount": Decimal("500.00")},
}

ALLOWED_PAYMENT_METHODS = {
    "upi",
    "card",
    "netbanking",
    "wallet",
    "emi",
}


class OrderStatusUpdate(BaseModel):
    order_status: str

class AdminOrderDetailsUpdate(BaseModel):
    tracking_number: str | None = None
    internal_note: str | None = None

class RazorpayOrderResponse(BaseModel):
    dealguru_order_id: UUID
    razorpay_order_id: str
    razorpay_key_id: str
    amount: int
    currency: str

class RazorpayPaymentVerify(BaseModel):
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_discount(subtotal: Decimal, coupon_code: str | None) -> Decimal:
    if not coupon_code:
        return ZERO

    code = coupon_code.strip().upper()
    coupon = COUPONS.get(code)

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid coupon code",
        )

    discount = money(subtotal * coupon["percent"] / Decimal("100"))

    maximum = coupon["max_discount"]
    if maximum is not None:
        discount = min(discount, maximum)

    return min(discount, subtotal)


def get_order_query():
    return select(Order).options(selectinload(Order.items))


def restore_stock(db: Session, order: Order) -> None:
    """Restore reserved stock for an order exactly once."""
    for item in order.items:
        if item.product_id:
            product = db.scalar(
                select(Product)
                .where(Product.id == item.product_id)
                .with_for_update()
            )

            if product:
                product.stock += item.quantity


@router.post("/", response_model=OrderResponse, status_code=201)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # This store currently supports prepaid orders only.
        if payload.payment_method not in ALLOWED_PAYMENT_METHODS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported payment method",
            )

        if payload.delivery_method != "standard":
            raise HTTPException(
                status_code=400,
                detail="Only standard delivery is currently available",
            )

        # Verify that the address belongs to the logged-in customer.
        address = db.scalar(
            select(Address).where(
                Address.id == payload.address_id,
                Address.user_id == current_user.id,
            )
        )

        if not address:
            raise HTTPException(
                status_code=404,
                detail="Delivery address not found",
            )

        # Lock products while checking and reserving stock.
        product_ids = {item.product_id for item in payload.items}

        products = db.scalars(
            select(Product)
            .where(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
        ).all()

        product_map = {product.id: product for product in products}

        # Check quantities across duplicate product lines too.
        requested_quantities = {}
        for item in payload.items:
            requested_quantities[item.product_id] = (
                requested_quantities.get(item.product_id, 0)
                + item.quantity
            )

        for product_id, quantity in requested_quantities.items():
            product = product_map.get(product_id)

            if not product or product.status != "active":
                raise HTTPException(
                    status_code=400,
                    detail=f"Product {product_id} is unavailable",
                )

            if product.stock < quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {product.name}",
                )

        # Calculate all prices using database values.
        subtotal = ZERO
        order_items = []

        for requested_item in payload.items:
            product = product_map[requested_item.product_id]
            unit_price = money(Decimal(product.price))
            line_total = unit_price * requested_item.quantity
            subtotal += line_total

            order_items.append(
                OrderItem(
                    product_id=product.id,
                    product_sku=product.sku,
                    product_name=product.name,
                    image=product.image,
                    unit_price=unit_price,
                    quantity=requested_item.quantity,
                    selected_color=requested_item.selected_color,
                    selected_size=requested_item.selected_size,
                )
            )

        subtotal = money(subtotal)
        discount = calculate_discount(subtotal, payload.coupon_code)
        delivery_fee = ZERO
        gift_wrap_fee = GIFT_WRAP_FEE if payload.gift_wrap else ZERO

        # COD and gift-card deductions are not accepted by this API.
        cod_fee = ZERO
        gift_card_amount = ZERO

        total = money(
            subtotal
            - discount
            + delivery_fee
            + gift_wrap_fee
            + cod_fee
            - gift_card_amount
        )

        if total <= ZERO:
            raise HTTPException(
                status_code=400,
                detail="Order total must be greater than zero",
            )

        address_snapshot = {
            "full_name": address.full_name,
            "phone": address.phone,
            "pincode": address.pincode,
            "line1": address.line1,
            "line2": address.line2,
            "landmark": address.landmark,
            "city": address.city,
            "state": address.state,
            "address_type": address.address_type,
        }

        delivery_snapshot = {
            "method": "standard",
            "gift_wrap": payload.gift_wrap,
            "notes": payload.delivery_notes,
        }

        order = Order(
            user_id=current_user.id,
            address_snapshot=address_snapshot,
            delivery_snapshot=delivery_snapshot,
            subtotal=subtotal,
            discount=discount,
            delivery_fee=delivery_fee,
            gift_wrap_fee=gift_wrap_fee,
            cod_fee=cod_fee,
            gift_card_amount=gift_card_amount,
            total=total,
            order_status="Pending Payment",
            payment_status="pending",
            payment_method=payload.payment_method,
            coupon_code=payload.coupon_code.strip().upper()
            if payload.coupon_code
            else None,
            items=order_items,
        )

        # Reserve stock while the order awaits payment.
        for product_id, quantity in requested_quantities.items():
            product_map[product_id].stock -= quantity

        db.add(order)
        db.commit()

        saved_order = db.scalar(
            get_order_query().where(Order.id == order.id)
        )

        return saved_order

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.get("/", response_model=list[OrderResponse])
def get_my_orders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.scalars(
        get_order_query()
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    ).all()


@router.get("/admin/all", response_model=list[OrderResponse])
def get_all_orders(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    return db.scalars(
        get_order_query().order_by(Order.created_at.desc())
    ).all()

@router.post("/{order_id}/payment/create", response_model=RazorpayOrderResponse)
def create_razorpay_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        order = db.scalar(
            get_order_query()
            .where(Order.id == order_id)
            .with_for_update()
        )

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        if order.order_status != "Pending Payment":
            raise HTTPException(
                status_code=400,
                detail="Order is not awaiting payment",
            )

        if order.payment_status != "pending":
            raise HTTPException(
                status_code=400,
                detail="Payment is not pending",
            )

        amount_paise = int(
            (order.total * 100).quantize(Decimal("1"))
        )

        existing_payment = db.scalar(
            select(Payment)
            .where(
                Payment.order_id == order.id,
                Payment.status == "created",
            )
            .order_by(Payment.created_at.desc())
        )

        if existing_payment and existing_payment.provider_order_id:
            return RazorpayOrderResponse(
                dealguru_order_id=order.id,
                razorpay_order_id=existing_payment.provider_order_id,
                razorpay_key_id=settings.razorpay_key_id,
                amount=int(existing_payment.amount * 100),
                currency=existing_payment.currency,
            )

        razorpay_order = razorpay_client.order.create(
            {
                "amount": amount_paise,
                "currency": "INR",
                "receipt": str(order.id),
                "notes": {
                    "dealguru_order_id": str(order.id),
                    "customer_id": str(current_user.id),
                },
            }
        )

        payment = Payment(
            order_id=order.id,
            provider="razorpay",
            provider_order_id=razorpay_order["id"],
            amount=order.total,
            currency="INR",
            status="created",
        )

        db.add(payment)
        db.commit()

        return RazorpayOrderResponse(
            dealguru_order_id=order.id,
            razorpay_order_id=razorpay_order["id"],
            razorpay_key_id=settings.razorpay_key_id,
            amount=amount_paise,
            currency="INR",
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Unable to create Razorpay payment order",
        )


@router.post("/{order_id}/payment/verify", response_model=OrderResponse)
def verify_razorpay_payment(
    order_id: UUID,
    payload: RazorpayPaymentVerify,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        order = db.scalar(
            get_order_query()
            .where(Order.id == order_id)
            .with_for_update()
        )

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        payment = db.scalar(
            select(Payment)
            .where(
                Payment.order_id == order.id,
                Payment.provider_order_id == payload.razorpay_order_id,
            )
            .with_for_update()
        )

        if not payment:
            raise HTTPException(
                status_code=404,
                detail="Payment record not found",
            )

        # Verify Razorpay signature.
        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": payload.razorpay_order_id,
                "razorpay_payment_id": payload.razorpay_payment_id,
                "razorpay_signature": payload.razorpay_signature,
            }
        )

        # Fetch authoritative payment details from Razorpay.
        razorpay_payment = razorpay_client.payment.fetch(
            payload.razorpay_payment_id
        )

        if razorpay_payment.get("order_id") != payment.provider_order_id:
            raise HTTPException(
                status_code=400,
                detail="Payment does not belong to this order",
            )

        if razorpay_payment.get("amount") != int(order.total * 100):
            raise HTTPException(
                status_code=400,
                detail="Payment amount mismatch",
            )

        if razorpay_payment.get("currency") != "INR":
            raise HTTPException(
                status_code=400,
                detail="Invalid payment currency",
            )

        if razorpay_payment.get("status") != "captured":
            raise HTTPException(
                status_code=400,
                detail="Payment has not been captured",
            )

        # Idempotency: accept a repeat request for the same verified payment.
        if payment.status == "paid":
            if payment.provider_payment_id != payload.razorpay_payment_id:
                raise HTTPException(
                    status_code=409,
                    detail="A different payment is already recorded",
                )

            return order

        if order.order_status != "Pending Payment":
            raise HTTPException(
                status_code=400,
                detail="Order is not awaiting payment",
            )

        if order.payment_status != "pending":
            raise HTTPException(
                status_code=400,
                detail="Order payment is not pending",
            )

        payment.provider_payment_id = payload.razorpay_payment_id
        payment.status = "paid"
        payment.method = razorpay_payment.get("method")

        order.payment_status = "paid"
        order.order_status = "Processing"

        db.commit()

        return db.scalar(
            get_order_query().where(Order.id == order.id)
        )

    except HTTPException:
        db.rollback()
        raise

    except razorpay.errors.SignatureVerificationError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Invalid payment signature",
        )

    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=502,
            detail="Payment verification failed",
        )


@router.get("/{order_id}", response_model=OrderResponse)
def get_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = db.scalar(
        get_order_query().where(Order.id == order_id)
    )

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    if current_user.role != "admin" and order.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return order


@router.post("/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(
    order_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        order = db.scalar(
            get_order_query()
            .where(Order.id == order_id)
            .with_for_update()
        )

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        if order.order_status == "Cancelled":
            raise HTTPException(status_code=400, detail="Order is already cancelled")

        if order.payment_status != "pending":
            raise HTTPException(
                status_code=400,
                detail="Paid orders require the refund process",
            )

        if order.order_status != "Pending Payment":
            raise HTTPException(
                status_code=400,
                detail="This order can no longer be cancelled here",
            )

        restore_stock(db, order)
        order.order_status = "Cancelled"

        db.commit()

        return db.scalar(
            get_order_query().where(Order.id == order.id)
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.patch("/admin/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: UUID,
    payload: OrderStatusUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    allowed_statuses = {
        "Processing",
        "Shipped",
        "Delivered",
        "Cancelled",
    }

    if payload.order_status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="Invalid order status")

    try:
        order = db.scalar(
            get_order_query()
            .where(Order.id == order_id)
            .with_for_update()
        )

        if not order:
            raise HTTPException(status_code=404, detail="Order not found")

        if order.order_status in {"Cancelled", "Delivered"}:
            raise HTTPException(
                status_code=400,
                detail="This order can no longer be updated",
            )

        if payload.order_status == "Cancelled":
            if order.payment_status != "pending":
                raise HTTPException(
                    status_code=400,
                    detail="Paid orders require the refund process",
                )

            restore_stock(db, order)

        else:
            if order.payment_status != "paid":
                raise HTTPException(
                    status_code=400,
                    detail="Order must have verified payment before processing",
                )

        order.order_status = payload.order_status
        db.commit()

        return db.scalar(
            get_order_query().where(Order.id == order.id)
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise


@router.patch("/admin/{order_id}/details", response_model=OrderResponse)
def update_order_details(
    order_id: UUID,
    payload: AdminOrderDetailsUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin),
):
    try:
        order = db.scalar(
            get_order_query()
            .where(Order.id == order_id)
            .with_for_update()
        )

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found",
            )

        if "tracking_number" in payload.model_fields_set:
            order.tracking_number = (
                payload.tracking_number.strip()
                if payload.tracking_number
                else None
            )

        if "internal_note" in payload.model_fields_set:
            order.internal_note = (
                payload.internal_note.strip()
                if payload.internal_note
                else None
            )

        db.commit()

        return db.scalar(
            get_order_query().where(Order.id == order.id)
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

