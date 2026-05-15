import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .game import Game
    from .user import User


class Move(Base, TimestampMixin):
    __tablename__ = "moves"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    move_number: Mapped[int] = mapped_column(Integer, nullable=False)
    path: Mapped[list] = mapped_column(JSONB, nullable=False)
    captured: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    game: Mapped["Game"] = relationship("Game", back_populates="moves")
    player: Mapped["User"] = relationship("User")
