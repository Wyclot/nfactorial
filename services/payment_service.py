"""
Payment Service — single-skin purchases via Halyk Invoice Link.

Flow:
- init_skin_payment(skin, user) → creates Payment(pending), asks Halyk for an
  invoice URL, returns it. User goes off to Halyk and pays.
- handle_post_link(payload) → Halyk webhook. On code='ok' we grant the skin
  (insert UserSkin) and mark payment charged. Idempotent.
- reconcile_pending(...) → catches stale pending payments (postlink lost in
  transit, network split, etc.) by polling Halyk for transaction status.
- refund_payment(payment, amount?) → refunds and revokes the UserSkin
  entitlement.

Duplicate purchase guard: if a UserSkin already exists for (user, skin) when
the postlink lands, we auto-refund — the user shouldn't be charged twice for
the same digital item.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from integrations.halyk_client import HalykClient
from models.payment import Payment, PaymentStatus
from models.skin import Skin, UserSkin
from models.user import User
from services.utils import generate_invoice_id

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self, db: AsyncSession, halyk: HalykClient):
        self.db = db
        self.halyk = halyk

    # =================================================================
    # Init — create invoice, return URL to redirect user to Halyk page
    # =================================================================

    async def init_skin_payment(self, skin: Skin, user: User) -> dict:
        if not user.email:
            raise HTTPException(400, "Email is required for payment")
        if not skin.is_active:
            raise HTTPException(400, "Skin is not available for purchase")
        if skin.price_kzt <= 0:
            raise HTTPException(400, "Skin price is not set")

        # Already owned? Don't let the user pay twice.
        existing = await self.db.execute(
            select(UserSkin).where(
                UserSkin.user_id == user.id,
                UserSkin.skin_id == skin.id,
            )
        )
        if existing.scalars().first():
            raise HTTPException(409, "You already own this skin")

        # Old pending payments for the same skin/user can stay — reconcile will
        # handle them. Each init starts a fresh invoice_id.
        payment = Payment(
            user_id=user.id,
            skin_id=skin.id,
            invoice_id=generate_invoice_id(),
            amount=skin.price_kzt,
            status=PaymentStatus.pending,
        )
        self.db.add(payment)
        await self.db.flush()

        sep = "&" if "?" in settings.halyk_back_link else "?"
        back_link = f"{settings.halyk_back_link}{sep}payment_id={payment.id}"
        fail_sep = "&" if "?" in settings.halyk_failure_back_link else "?"
        failure_back_link = f"{settings.halyk_failure_back_link}{fail_sep}payment_id={payment.id}"

        try:
            invoice = await self.halyk.create_invoice(
                invoice_id=payment.invoice_id,
                amount=payment.amount,
                description=f"Checkers · {skin.name}",
                account_id=str(user.id),
                email=user.email,
                phone=user.phone,
                post_link=settings.halyk_postlink_url,
                back_link=back_link,
                failure_back_link=failure_back_link,
            )
        except Exception as exc:
            logger.exception("Failed to create Halyk invoice for skin %s", skin.id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Payment provider unavailable",
            ) from exc

        await self.db.commit()

        return {
            "invoice_id": payment.invoice_id,
            "invoice_url": invoice["invoice_url"],
            "amount": float(payment.amount),
            "expire_date": invoice.get("expire_date"),
        }

    # =================================================================
    # Postlink — webhook from Halyk announcing the result
    # =================================================================

    async def handle_post_link(self, payload: dict[str, Any]) -> None:
        invoice_id = payload.get("invoiceId")
        if not invoice_id:
            raise HTTPException(400, "missing invoiceId")

        result = await self.db.execute(
            select(Payment).where(Payment.invoice_id == invoice_id).with_for_update()
        )
        payment = result.scalars().first()
        if not payment:
            logger.warning("Postlink for unknown invoice_id=%s", invoice_id)
            return

        if payment.status in (
            PaymentStatus.charged,
            PaymentStatus.refunded,
            PaymentStatus.failed,
            PaymentStatus.cancelled,
        ):
            logger.info(
                "Postlink for already-finalized invoice=%s status=%s",
                invoice_id, payment.status,
            )
            return

        try:
            amount = Decimal(str(payload.get("amount")))
        except (TypeError, ValueError):
            raise HTTPException(400, "invalid amount format")

        if payment.amount != amount:
            logger.error(
                "amount mismatch invoice=%s expected=%s got=%s",
                invoice_id, payment.amount, amount,
            )
            raise HTTPException(400, "amount mismatch")

        payment.postlink_payload = payload
        payment.halyk_transaction_id = payload.get("id")
        payment.approval_code = payload.get("approvalCode") or None
        payment.reference = payload.get("reference") or None
        payment.card_mask = payload.get("cardMask") or None
        payment.card_type = payload.get("cardType") or None
        payment.reason_code = payload.get("reasonCode")
        payment.reason = payload.get("reason")

        if payload.get("code") == "ok":
            await self._grant_skin(payment)
        else:
            payment.status = PaymentStatus.failed
            logger.info(
                "Payment %s failed: reason=%s code=%s",
                payment.id, payment.reason, payment.reason_code,
            )

        await self.db.commit()

    # =================================================================
    # Internal — grant entitlement, refund duplicates
    # =================================================================

    async def _grant_skin(self, payment: Payment) -> None:
        """Halyk says: paid. Grant the entitlement, unless already owned (auto-refund)."""
        dup = await self.db.execute(
            select(UserSkin).where(
                UserSkin.user_id == payment.user_id,
                UserSkin.skin_id == payment.skin_id,
            )
        )
        if dup.scalars().first():
            # User already owns this skin (maybe paid via a different invoice
            # that landed first). Mark charged then refund this one back.
            payment.status = PaymentStatus.charged
            logger.info(
                "Payment %s: user %s already owns skin %s — auto-refund",
                payment.id, payment.user_id, payment.skin_id,
            )
            await self._auto_refund(payment, reason="duplicate_purchase")
            return

        self.db.add(UserSkin(
            user_id=payment.user_id,
            skin_id=payment.skin_id,
            payment_id=payment.id,
        ))
        payment.status = PaymentStatus.charged
        payment.paid_at = datetime.now(UTC)
        logger.info(
            "Payment %s charged → skin %s granted to user %s amount=%s",
            payment.id, payment.skin_id, payment.user_id, payment.amount,
        )

    async def _auto_refund(self, payment: Payment, reason: str) -> None:
        if not payment.halyk_transaction_id:
            logger.error("Cannot auto-refund %s: no transaction_id stored", payment.id)
            return
        try:
            await self.halyk.refund(transaction_id=payment.halyk_transaction_id)
            payment.status = PaymentStatus.refunded
            payment.refunded_at = datetime.now(UTC)
            payment.reason = f"auto_refund: {reason}"
        except Exception:
            logger.exception("Auto-refund failed for payment %s", payment.id)

    # =================================================================
    # Manual refund (revokes the skin entitlement)
    # =================================================================

    async def refund_payment(self, payment: Payment, amount: Decimal | None = None) -> None:
        if payment.status != PaymentStatus.charged:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot refund payment in status {payment.status.value}",
            )
        if not payment.halyk_transaction_id:
            raise HTTPException(500, "no halyk_transaction_id stored")

        try:
            await self.halyk.refund(
                transaction_id=payment.halyk_transaction_id,
                amount=amount,
            )
        except Exception as exc:
            logger.exception("Refund failed for %s", payment.id)
            raise HTTPException(502, "Refund failed") from exc

        payment.status = PaymentStatus.refunded
        payment.refunded_at = datetime.now(UTC)

        # Revoke the granted entitlement (only on full refund — partials keep the skin).
        if amount is None:
            entitlement_result = await self.db.execute(
                select(UserSkin).where(UserSkin.payment_id == payment.id)
            )
            entitlement = entitlement_result.scalars().first()
            if entitlement:
                await self.db.delete(entitlement)

        await self.db.commit()
        logger.info(
            "Refund successful: payment=%s amount=%s",
            payment.id, amount if amount is not None else "full",
        )

    # =================================================================
    # Reconcile — pick up pending payments that never got a postlink
    # =================================================================

    async def reconcile_pending(self, max_age_minutes: int = 10) -> int:
        cutoff = datetime.now(UTC) - timedelta(minutes=max_age_minutes)
        result = await self.db.execute(
            select(Payment).where(
                Payment.status == PaymentStatus.pending,
                Payment.created_at < cutoff,
            )
        )
        stale = result.scalars().all()
        if not stale:
            return 0

        count = 0
        for p in stale:
            try:
                tx = await self.halyk.get_status(p.invoice_id)
                await self._apply_halyk_status(p, tx)
                count += 1
            except Exception:
                logger.exception("Reconcile failed for %s", p.id)
                continue

        await self.db.commit()
        return count

    async def _apply_halyk_status(self, payment: Payment, halyk_response: dict[str, Any]) -> None:
        if halyk_response.get("resultCode") != "100":
            return
        tx = halyk_response.get("transaction") or {}
        status_name = tx.get("statusName")

        if not payment.halyk_transaction_id:
            payment.halyk_transaction_id = tx.get("id")
        if not payment.approval_code:
            payment.approval_code = tx.get("approvalCode")
        if not payment.reference:
            payment.reference = tx.get("reference")
        if not payment.card_mask:
            payment.card_mask = tx.get("cardMask")
        if not payment.card_type:
            payment.card_type = tx.get("cardType")
        if not payment.reason:
            payment.reason = tx.get("reason")
        if not payment.reason_code:
            payment.reason_code = tx.get("reasonCode")

        if status_name == "CHARGE":
            await self._grant_skin(payment)
            logger.info("Reconciled %s → charged (missed webhook)", payment.id)
        elif status_name in ("FAILED", "REJECT", "3D"):
            payment.status = PaymentStatus.failed
        elif status_name == "REFUND":
            payment.status = PaymentStatus.refunded
            payment.refunded_at = datetime.now(UTC)
