from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID as PyUUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import CurrentUser
from integrations.halyk_client import HalykClient, get_halyk_client, is_halyk_configured
from models.payment import Payment, PaymentStatus
from models.skin import Skin, UserSkin
from schemas.schemas import PaymentInitResponse, PaymentOut
from services.payment_service import PaymentService
from services.utils import generate_invoice_id

router = APIRouter()


def _service(
    db: Annotated[AsyncSession, Depends(get_db)],
    halyk: Annotated[HalykClient, Depends(get_halyk_client)],
) -> PaymentService:
    return PaymentService(db, halyk)


@router.post("/skin/{skin_id}", response_model=PaymentInitResponse)
async def buy_skin(
    skin_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    service: Annotated[PaymentService, Depends(_service)],
):
    """Start a Halyk-hosted payment for the given skin.
    Falls back to a direct grant if Halyk credentials are not configured (dev mode)."""
    skin = (await db.execute(select(Skin).where(Skin.id == skin_id))).scalars().first()
    if not skin:
        raise HTTPException(404, "Skin not found")

    if not is_halyk_configured():
        return await _dev_grant(db, user.id, skin)

    result = await service.init_skin_payment(skin, user)
    return PaymentInitResponse(
        invoice_id=result["invoice_id"],
        invoice_url=result["invoice_url"],
        amount=result["amount"],
        expire_date=result.get("expire_date"),
        status=PaymentStatus.pending,
    )


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    payment = (
        await db.execute(select(Payment).where(Payment.id == payment_id))
    ).scalars().first()
    if not payment:
        raise HTTPException(404, "Payment not found")
    if payment.user_id != user.id:
        raise HTTPException(403, "Not your payment")
    return payment


@router.post("/halyk/postlink", include_in_schema=False)
async def halyk_postlink(
    request: Request,
    service: Annotated[PaymentService, Depends(_service)],
):
    """Public webhook called by Halyk after a payment attempt finishes.
    No auth — Halyk authenticates implicitly via the invoice_id we minted."""
    payload = await request.json()
    await service.handle_post_link(payload)
    return {"ok": True}


async def _dev_grant(db: AsyncSession, user_id: PyUUID, skin: Skin) -> PaymentInitResponse:
    """Bypass Halyk when no credentials are configured — useful for local UI dev."""
    if skin.price_kzt <= 0:
        raise HTTPException(400, "Skin price is not set")

    already = await db.execute(
        select(UserSkin).where(UserSkin.user_id == user_id, UserSkin.skin_id == skin.id)
    )
    if already.scalars().first():
        raise HTTPException(409, "You already own this skin")

    payment = Payment(
        user_id=user_id,
        skin_id=skin.id,
        invoice_id=generate_invoice_id(),
        amount=skin.price_kzt,
        status=PaymentStatus.charged,
        paid_at=datetime.now(UTC),
        reason="DEV_GRANT (Halyk not configured)",
    )
    db.add(payment)
    await db.flush()
    db.add(UserSkin(user_id=user_id, skin_id=skin.id, payment_id=payment.id))
    await db.commit()

    return PaymentInitResponse(
        invoice_id=payment.invoice_id,
        invoice_url=None,
        amount=float(payment.amount),
        expire_date=None,
        status=PaymentStatus.charged,
    )
