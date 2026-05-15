import asyncio
from copy import deepcopy
from datetime import datetime, UTC
from typing import Annotated, List
from uuid import UUID as PyUUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from core.ai import analyze_game, search
from core.checkers import INITIAL_BOARD, apply_move, new_board
from core.clock import consume_clock_on_move, detect_timeout, start_clock
from core.database import get_db
from core.dependencies import CurrentUser
from core.ws_manager import ws_manager
from models.game import Game, GameStatus
from models.move import Move
from models.user import AI_BOT_ID
from schemas.schemas import (
    AiGameRequest,
    AnalysisItem,
    GameListItem,
    GameOut,
    MoveIn,
    MoveOut,
    TimeControl,
)

DIFFICULTY_DEPTH = {"easy": 2, "medium": 4, "hard": 6}


def _normalize_time_control(initial_seconds, increment_seconds):
    if initial_seconds is None or initial_seconds <= 0:
        return None, 0
    return initial_seconds * 1000, max(0, increment_seconds) * 1000

router = APIRouter()


@router.post("", response_model=GameOut)
async def create_game(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: TimeControl | None = None,
):
    init_ms, inc_ms = _normalize_time_control(
        data.initial_seconds if data else None,
        data.increment_seconds if data else 0,
    )
    game = Game(
        white_player_id=user.id,
        board=new_board(),
        turn="w",
        status=GameStatus.waiting,
        time_initial_ms=init_ms,
        time_increment_ms=inc_ms,
    )
    db.add(game)
    await db.commit()
    return await _load_game(db, game.id)


@router.get("", response_model=List[GameListItem])
async def list_open_games(db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(
        select(Game)
        .where(Game.status == GameStatus.waiting)
        .options(selectinload(Game.white_player))
        .order_by(Game.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/mine", response_model=List[GameListItem])
async def list_my_games(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Game)
        .where(or_(Game.white_player_id == user.id, Game.black_player_id == user.id))
        .options(selectinload(Game.white_player))
        .order_by(Game.created_at.desc())
        .limit(50)
    )
    return result.scalars().all()


@router.get("/{game_id}", response_model=GameOut)
async def get_game(
    game_id: PyUUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if detect_timeout(game):
        await db.commit()
        game = await _load_game(db, game_id)
        await ws_manager.broadcast(game_id, _state_message(game))
    return game


@router.get("/{game_id}/moves", response_model=List[MoveOut])
async def list_moves(
    game_id: PyUUID,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Move).where(Move.game_id == game_id).order_by(Move.move_number)
    )
    return result.scalars().all()


@router.get("/{game_id}/analysis", response_model=List[AnalysisItem])
async def analyze_finished_game(
    game_id: PyUUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    depth: int = 3,
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if game.status not in (GameStatus.finished, GameStatus.aborted):
        raise HTTPException(400, "Analysis is only available for finished games")
    if not 1 <= depth <= 5:
        raise HTTPException(400, "depth must be between 1 and 5")

    moves_result = await db.execute(
        select(Move).where(Move.game_id == game_id).order_by(Move.move_number)
    )
    moves = moves_result.scalars().all()
    paths = [m.path for m in moves]
    if not paths:
        return []

    # Run CPU-bound analysis off the event loop.
    annotations = await asyncio.to_thread(
        analyze_game, [row[:] for row in INITIAL_BOARD], paths, depth
    )
    return annotations


@router.post("/{game_id}/join", response_model=GameOut)
async def join_game(
    game_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if game.status != GameStatus.waiting:
        raise HTTPException(400, "Game is not joinable")
    if game.white_player_id == user.id:
        raise HTTPException(400, "Cannot join your own game")
    game.black_player_id = user.id
    game.status = GameStatus.in_progress
    start_clock(game)
    await db.commit()
    game = await _load_game(db, game_id)
    await ws_manager.broadcast(game_id, _state_message(game))
    return game


@router.post("/{game_id}/move", response_model=GameOut)
async def make_move(
    game_id: PyUUID,
    move_in: MoveIn,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if game.status != GameStatus.in_progress:
        raise HTTPException(400, "Game is not in progress")

    expected = game.white_player_id if game.turn == "w" else game.black_player_id
    if user.id != expected:
        raise HTTPException(403, "Not your turn")

    # If the player's clock already ran out, finish the game instead of applying the move.
    if consume_clock_on_move(game):
        await db.commit()
        game = await _load_game(db, game_id)
        await ws_manager.broadcast(game_id, _state_message(game))
        return game

    board_copy = deepcopy(game.board)
    try:
        new_b, captured, new_turn, winner_color = apply_move(board_copy, move_in.path, game.turn)
    except ValueError as e:
        raise HTTPException(400, str(e))

    game.board = new_b
    game.turn = new_turn
    game.move_count += 1
    game.draw_offered_by = None  # any move auto-declines a pending draw offer
    db.add(Move(
        game_id=game.id,
        player_id=user.id,
        move_number=game.move_count,
        path=move_in.path,
        captured=captured,
    ))
    if winner_color is not None:
        game.status = GameStatus.finished
        game.winner_id = game.white_player_id if winner_color == "w" else game.black_player_id
        game.finished_at = datetime.now(UTC)

    await db.commit()
    game = await _load_game(db, game_id)

    if game.ai_difficulty is not None and game.status == GameStatus.in_progress:
        # vs-AI: push the human move now so the board updates immediately,
        # then compute and apply the bot move.
        await ws_manager.broadcast(game_id, _state_message(game))
        await _maybe_ai_move(db, game)
        game = await _load_game(db, game_id)

    await ws_manager.broadcast(game_id, _state_message(game))
    return game


@router.post("/ai", response_model=GameOut)
async def create_ai_game(
    data: AiGameRequest,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    depth = DIFFICULTY_DEPTH.get(data.difficulty.lower())
    if depth is None:
        raise HTTPException(400, "difficulty must be 'easy', 'medium', or 'hard'")
    init_ms, inc_ms = _normalize_time_control(data.initial_seconds, data.increment_seconds)
    game = Game(
        white_player_id=user.id,
        black_player_id=AI_BOT_ID,
        board=new_board(),
        turn="w",
        status=GameStatus.in_progress,
        ai_difficulty=depth,
        time_initial_ms=init_ms,
        time_increment_ms=inc_ms,
    )
    start_clock(game)
    db.add(game)
    await db.commit()
    return await _load_game(db, game.id)


async def _maybe_ai_move(db: AsyncSession, game: Game) -> Game:
    """If game is vs AI and it's bot's turn, compute & apply the bot move."""
    if game.ai_difficulty is None or game.status != GameStatus.in_progress:
        return game
    bot_color = "b"  # human is always white in vs-AI games
    if game.turn != bot_color:
        return game

    ai_score, ai_path = await asyncio.to_thread(
        search, [row[:] for row in game.board], bot_color, game.ai_difficulty
    )
    if not ai_path:
        # Bot has no legal moves — opponent wins.
        game.status = GameStatus.finished
        game.winner_id = game.white_player_id
        game.finished_at = datetime.now(UTC)
        await db.commit()
        return game

    # Charge AI's clock for thinking time.
    if consume_clock_on_move(game):
        await db.commit()
        return game

    new_b, captured, new_turn, winner_color = apply_move(
        deepcopy(game.board), ai_path, bot_color
    )
    game.board = new_b
    game.turn = new_turn
    game.move_count += 1
    game.draw_offered_by = None
    db.add(Move(
        game_id=game.id,
        player_id=AI_BOT_ID,
        move_number=game.move_count,
        path=ai_path,
        captured=captured,
    ))
    if winner_color is not None:
        game.status = GameStatus.finished
        game.winner_id = game.white_player_id if winner_color == "w" else game.black_player_id
        game.finished_at = datetime.now(UTC)
    await db.commit()
    return game


@router.post("/quick-match", response_model=GameOut)
async def quick_match(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: TimeControl | None = None,
):
    """Join the oldest waiting game with matching time control; if none, create one."""
    init_ms, inc_ms = _normalize_time_control(
        data.initial_seconds if data else None,
        data.increment_seconds if data else 0,
    )
    result = await db.execute(
        select(Game)
        .where(
            Game.status == GameStatus.waiting,
            Game.white_player_id != user.id,
            Game.time_initial_ms.is_(init_ms) if init_ms is None else Game.time_initial_ms == init_ms,
            Game.time_increment_ms == inc_ms,
        )
        .order_by(Game.created_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    game = result.scalars().first()
    if game:
        game.black_player_id = user.id
        game.status = GameStatus.in_progress
        start_clock(game)
        await db.commit()
        game = await _load_game(db, game.id)
        await ws_manager.broadcast(game.id, _state_message(game))
        return game

    game = Game(
        white_player_id=user.id,
        board=new_board(),
        turn="w",
        status=GameStatus.waiting,
        time_initial_ms=init_ms,
        time_increment_ms=inc_ms,
    )
    db.add(game)
    await db.commit()
    return await _load_game(db, game.id)


@router.post("/{game_id}/abort", response_model=GameOut)
async def abort_game(
    game_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if game.status != GameStatus.waiting:
        raise HTTPException(400, "Only waiting games can be aborted")
    if game.white_player_id != user.id:
        raise HTTPException(403, "Only the host can abort")
    game.status = GameStatus.aborted
    game.finished_at = datetime.now(UTC)
    await db.commit()
    game = await _load_game(db, game_id)
    await ws_manager.broadcast(game_id, _state_message(game))
    return game


@router.post("/{game_id}/resign", response_model=GameOut)
async def resign_game(
    game_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if game.status != GameStatus.in_progress:
        raise HTTPException(400, "Game is not in progress")
    if user.id not in (game.white_player_id, game.black_player_id):
        raise HTTPException(403, "Not a player in this game")

    game.status = GameStatus.finished
    game.winner_id = (
        game.black_player_id if user.id == game.white_player_id else game.white_player_id
    )
    game.finished_at = datetime.now(UTC)
    game.draw_offered_by = None
    await db.commit()
    game = await _load_game(db, game_id)
    await ws_manager.broadcast(game_id, _state_message(game))
    return game


@router.post("/{game_id}/draw/offer", response_model=GameOut)
async def offer_draw(
    game_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if game.status != GameStatus.in_progress:
        raise HTTPException(400, "Game is not in progress")
    if user.id not in (game.white_player_id, game.black_player_id):
        raise HTTPException(403, "Not a player in this game")

    game.draw_offered_by = user.id
    await db.commit()
    game = await _load_game(db, game_id)
    await ws_manager.broadcast(game_id, _state_message(game))
    return game


@router.post("/{game_id}/draw/accept", response_model=GameOut)
async def accept_draw(
    game_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if game.status != GameStatus.in_progress:
        raise HTTPException(400, "Game is not in progress")
    if game.draw_offered_by is None:
        raise HTTPException(400, "No draw offer pending")
    if game.draw_offered_by == user.id:
        raise HTTPException(400, "Cannot accept your own draw offer")
    if user.id not in (game.white_player_id, game.black_player_id):
        raise HTTPException(403, "Not a player in this game")

    game.status = GameStatus.finished
    game.winner_id = None  # draw
    game.finished_at = datetime.now(UTC)
    game.draw_offered_by = None
    await db.commit()
    game = await _load_game(db, game_id)
    await ws_manager.broadcast(game_id, _state_message(game))
    return game


@router.post("/{game_id}/draw/decline", response_model=GameOut)
async def decline_draw(
    game_id: PyUUID,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    game = await _load_game(db, game_id)
    if not game:
        raise HTTPException(404, "Game not found")
    if game.draw_offered_by is None:
        raise HTTPException(400, "No draw offer pending")
    if game.draw_offered_by == user.id:
        raise HTTPException(400, "Cannot decline your own offer")
    if user.id not in (game.white_player_id, game.black_player_id):
        raise HTTPException(403, "Not a player in this game")

    game.draw_offered_by = None
    await db.commit()
    game = await _load_game(db, game_id)
    await ws_manager.broadcast(game_id, _state_message(game))
    return game


async def _load_game(db: AsyncSession, game_id: PyUUID) -> Game | None:
    result = await db.execute(
        select(Game)
        .where(Game.id == game_id)
        .options(selectinload(Game.white_player), selectinload(Game.black_player))
    )
    return result.scalars().first()


def _state_message(game: Game) -> dict:
    return {"type": "state", "game": GameOut.model_validate(game).model_dump(mode="json")}
