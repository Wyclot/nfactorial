from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from models.game import GameStatus
from models.payment import PaymentStatus
from models.skin import SkinKind


class GoogleAuthRequest(BaseModel):
    id_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: Optional[str] = None
    name: Optional[str] = None
    surname: Optional[str] = None
    created_at: datetime
    active_piece_skin_code: Optional[str] = None
    active_board_skin_code: Optional[str] = None
    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    name: Optional[str] = None
    surname: Optional[str] = None


class PlayerOut(BaseModel):
    id: UUID
    name: Optional[str] = None
    model_config = {"from_attributes": True}


class GameOut(BaseModel):
    id: UUID
    white_player: PlayerOut
    black_player: Optional[PlayerOut] = None
    board: List[List[str]]
    turn: str
    status: GameStatus
    winner_id: Optional[UUID] = None
    draw_offered_by: Optional[UUID] = None
    ai_difficulty: Optional[int] = None
    time_initial_ms: Optional[int] = None
    time_increment_ms: int = 0
    white_time_ms: Optional[int] = None
    black_time_ms: Optional[int] = None
    last_clock_update_at: Optional[datetime] = None
    move_count: int
    created_at: datetime
    model_config = {"from_attributes": True}


class GameListItem(BaseModel):
    id: UUID
    white_player: PlayerOut
    status: GameStatus
    created_at: datetime
    model_config = {"from_attributes": True}


class MoveIn(BaseModel):
    path: List[List[int]] = Field(..., min_length=2)


class TimeControl(BaseModel):
    initial_seconds: Optional[int] = None
    increment_seconds: int = 0


class AiGameRequest(BaseModel):
    difficulty: str  # 'easy' | 'medium' | 'hard'
    initial_seconds: Optional[int] = None
    increment_seconds: int = 0


class MoveOut(BaseModel):
    move_number: int
    path: List[List[int]]
    captured: int
    player_id: UUID
    created_at: datetime
    model_config = {"from_attributes": True}


class AnalysisItem(BaseModel):
    move_number: int
    by: str  # 'w' or 'b'
    verdict: str  # good | inaccuracy | mistake | blunder
    eval_loss: float
    best_path: List[List[int]]
    comment: str


class SkinOut(BaseModel):
    id: UUID
    code: str
    kind: SkinKind
    name: str
    description: Optional[str] = None
    price_kzt: float
    preview_url: Optional[str] = None
    is_active: bool
    owned: bool = False
    equipped: bool = False
    model_config = {"from_attributes": True}


class UserSkinOut(BaseModel):
    id: UUID
    skin: SkinOut
    created_at: datetime
    model_config = {"from_attributes": True}


class PaymentInitResponse(BaseModel):
    invoice_id: str
    invoice_url: Optional[str] = None  # null when granted directly (dev mode)
    amount: float
    expire_date: Optional[str] = None
    status: PaymentStatus


class PaymentOut(BaseModel):
    id: UUID
    skin_id: UUID
    invoice_id: str
    amount: float
    status: PaymentStatus
    created_at: datetime
    paid_at: Optional[datetime] = None
    refunded_at: Optional[datetime] = None
    model_config = {"from_attributes": True}
