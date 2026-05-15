import enum
import uuid
from decimal import Decimal
from typing import Optional, TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .payment import Payment
    from .user import User


class SkinKind(str, enum.Enum):
    piece_set = "piece_set"   # custom checker piece appearance
    board = "board"           # custom board theme
    effect = "effect"         # move/capture visual effects


class Skin(Base, TimestampMixin):
    """Catalog entry. One Skin row per buyable visual item."""
    __tablename__ = "skins"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    kind: Mapped[SkinKind] = mapped_column(Enum(SkinKind), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    price_kzt: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    preview_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserSkin(Base, TimestampMixin):
    """Entitlement — granted on successful payment. One row per (user, skin)."""
    __tablename__ = "user_skins"
    __table_args__ = (
        UniqueConstraint("user_id", "skin_id", name="uq_user_skin"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skins.id"), nullable=False, index=True
    )
    payment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("payments.id"), nullable=False
    )

    skin: Mapped["Skin"] = relationship("Skin")
    payment: Mapped["Payment"] = relationship("Payment")
