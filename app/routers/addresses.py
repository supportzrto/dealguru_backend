
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, get_current_user
from app.models.user import User, Address
from app.schemas.address import (
    AddressCreate,
    AddressUpdate,
    AddressResponse,
)

router = APIRouter(
    prefix="/api/auth/addresses",
    tags=["Addresses"],
)


@router.get("/", response_model=list[AddressResponse])
def get_addresses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return db.scalars(
        select(Address)
        .where(Address.user_id == current_user.id)
        .order_by(Address.id)
    ).all()


@router.post("/", response_model=AddressResponse, status_code=201)
def create_address(
    data: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    addresses = db.scalars(
        select(Address).where(Address.user_id == current_user.id)
    ).all()

    make_default = data.is_default or not addresses

    if make_default:
        for address in addresses:
            address.is_default = False

    address = Address(
        user_id=current_user.id,
        **data.model_dump(exclude={"is_default"}),
        is_default=make_default,
    )

    db.add(address)
    db.commit()
    db.refresh(address)

    return address


@router.put("/{address_id}", response_model=AddressResponse)
def update_address(
    address_id: UUID,
    data: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    address = db.scalar(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id,
        )
    )

    if not address:
        raise HTTPException(404, "Address not found")

    if data.is_default:
        db.query(Address).filter(
            Address.user_id == current_user.id
        ).update({"is_default": False})

    for key, value in data.model_dump().items():
        setattr(address, key, value)

    db.commit()
    db.refresh(address)

    return address


@router.delete("/{address_id}")
def delete_address(
    address_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    address = db.scalar(
        select(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id,
        )
    )

    if not address:
        raise HTTPException(404, "Address not found")

    was_default = address.is_default

    db.delete(address)
    db.flush()

    if was_default:
        next_address = db.scalar(
            select(Address)
            .where(Address.user_id == current_user.id)
            .order_by(Address.id)
            .limit(1)
        )

        if next_address:
            next_address.is_default = True

    db.commit()

    return {"message": "Address deleted successfully"}
