import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .skin import Skin
    from .user import User


class PaymentStatus(str, enum.Enum):
    pending = "pending"      # invoice issued, awaiting Halyk webhook
    charged = "charged"      # money captured, skin granted
    failed = "failed"        # Halyk reported failure
    refunded = "refunded"    # money returned (skin revoked)
    cancelled = "cancelled"  # user cancelled before charge


class Payment(Base, TimestampMixin):
    """One row per attempted skin purchase. Linked to a Skin (catalog item)."""
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    skin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skins.id"), nullable=False, index=True
    )

    invoice_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        Enum(PaymentStatus), nullable=False, default=PaymentStatus.pending, index=True
    )

    # Halyk transaction details (filled when postlink arrives).
    halyk_transaction_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    approval_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reference: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    card_mask: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    card_type: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    reason_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    postlink_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    refunded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    skin: Mapped["Skin"] = relationship("Skin")
