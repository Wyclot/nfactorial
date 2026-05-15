import uuid
from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Enum, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, Mapped, mapped_column
from .base import Base, TimestampMixin
import enum
from datetime import datetime


if TYPE_CHECKING:
    from .session import Session
    from .skin import Skin


class AuthProvider(str, enum.Enum):
    google = "google"
    apple = "apple"
    system = "system"


AI_BOT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
AI_BOT_NAME = "AI Bot"





class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[Optional[str]] = mapped_column(String, unique=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String, unique=True)
    name: Mapped[Optional[str]] = mapped_column(String(20))
    surname: Mapped[Optional[str]] = mapped_column(String(20))

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    provider:Mapped[AuthProvider]=mapped_column(Enum(AuthProvider),nullable=False)
    provider_user_id:Mapped[str]=mapped_column(String,nullable=False,index=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_banned: Mapped[bool] = mapped_column(default=False)
    ban_reason: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Equipped cosmetics (NULL → use default look).
    active_piece_skin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skins.id", ondelete="SET NULL"), nullable=True
    )
    active_board_skin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("skins.id", ondelete="SET NULL"), nullable=True
    )

    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    active_piece_skin: Mapped[Optional["Skin"]] = relationship(
        "Skin", foreign_keys=[active_piece_skin_id]
    )
    active_board_skin: Mapped[Optional["Skin"]] = relationship(
        "Skin", foreign_keys=[active_board_skin_id]
    )