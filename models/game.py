import uuid
import enum
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Enum, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from .base import Base, TimestampMixin

if TYPE_CHECKING:
    from .user import User
    from .move import Move


class GameStatus(str, enum.Enum):
    waiting = "waiting"
    in_progress = "in_progress"
    finished = "finished"
    aborted = "aborted"


class Game(Base, TimestampMixin):
    __tablename__ = "games"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    white_player_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    black_player_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True
    )
    board: Mapped[list] = mapped_column(JSONB, nullable=False)
    turn: Mapped[str] = mapped_column(String(1), nullable=False, default="w")
    status: Mapped[GameStatus] = mapped_column(Enum(GameStatus), nullable=False, default=GameStatus.waiting, index=True)
    winner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    draw_offered_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    ai_difficulty: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    move_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Time controls (None = untimed game).
    time_initial_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    time_increment_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    white_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    black_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    last_clock_update_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    white_player: Mapped["User"] = relationship("User", foreign_keys=[white_player_id])
    black_player: Mapped[Optional["User"]] = relationship("User", foreign_keys=[black_player_id])
    moves: Mapped[list["Move"]] = relationship(
        "Move",
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="Move.move_number",
    )
