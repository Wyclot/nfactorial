from copy import deepcopy
from datetime import datetime, UTC
from uuid import UUID as PyUUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import selectinload

import asyncio
from core.ai import search
from core.checkers import apply_move
from core.clock import consume_clock_on_move, detect_timeout
from core.database import AsyncSessionLocal
from core.security import verify_access_token
from core.ws_manager import ws_manager
from models.game import Game, GameStatus
from models.move import Move
from models.user import AI_BOT_ID
from schemas.schemas import GameOut

router = APIRouter()


def _state_message(game: Game) -> dict:
    return {"type": "state", "game": GameOut.model_validate(game).model_dump(mode="json")}


async def _authenticate(token: str) -> PyUUID | None:
    payload = verify_access_token(token)
    if not payload:
        return None
    try:
        return PyUUID(payload["sub"])
    except (KeyError, ValueError, TypeError):
        return None


@router.websocket("/games/{game_id}")
async def game_socket(
    websocket: WebSocket,
    game_id: PyUUID,
    token: str = Query(...),
):
    user_id = await _authenticate(token)
    if not user_id:
        await websocket.close(code=4401)
        return

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Game)
            .where(Game.id == game_id)
            .options(selectinload(Game.white_player), selectinload(Game.black_player))
        )
        game = result.scalars().first()
        if not game:
            await websocket.close(code=4404)
            return
        is_player = user_id in (game.white_player_id, game.black_player_id)
        initial_state = _state_message(game)

    await websocket.accept()
    await ws_manager.connect(game_id, websocket)
    await websocket.send_json(initial_state)

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "ping":
                await websocket.send_json({"type": "pong"})
                continue

            if msg_type != "move":
                await websocket.send_json({"type": "error", "detail": "unknown message type"})
                continue

            if not is_player:
                await websocket.send_json({"type": "error", "detail": "spectators cannot move"})
                continue

            path = data.get("path")
            if not isinstance(path, list) or len(path) < 2:
                await websocket.send_json({"type": "error", "detail": "invalid path"})
                continue

            broadcast_payload = await _apply_move_tx(game_id, user_id, path)
            if isinstance(broadcast_payload, str):
                await websocket.send_json({"type": "error", "detail": broadcast_payload})
                continue
            await ws_manager.broadcast(game_id, broadcast_payload)

    except WebSocketDisconnect:
        pass
    finally:
        await ws_manager.disconnect(game_id, websocket)


async def _apply_move_tx(game_id: PyUUID, user_id: PyUUID, path: list) -> dict | str:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Game)
            .where(Game.id == game_id)
            .options(selectinload(Game.white_player), selectinload(Game.black_player))
        )
        game = result.scalars().first()
        if not game:
            return "game not found"
        if game.status != GameStatus.in_progress:
            return "game not in progress"

        expected = game.white_player_id if game.turn == "w" else game.black_player_id
        if user_id != expected:
            return "not your turn"

        if consume_clock_on_move(game):
            await db.commit()
            await db.refresh(game, ["white_player", "black_player"])
            return _state_message(game)

        board_copy = deepcopy(game.board)
        try:
            new_b, captured, new_turn, winner_color = apply_move(board_copy, path, game.turn)
        except ValueError as e:
            return str(e)

        game.board = new_b
        game.turn = new_turn
        game.move_count += 1
        game.draw_offered_by = None
        db.add(Move(
            game_id=game.id,
            player_id=user_id,
            move_number=game.move_count,
            path=path,
            captured=captured,
        ))
        if winner_color is not None:
            game.status = GameStatus.finished
            game.winner_id = game.white_player_id if winner_color == "w" else game.black_player_id
            game.finished_at = datetime.now(UTC)

        await db.commit()

        # vs-AI: push human move first for snappy UI, then think.
        if (
            game.ai_difficulty is not None
            and game.status == GameStatus.in_progress
            and game.turn == "b"
        ):
            await db.refresh(game, ["white_player", "black_player"])
            await ws_manager.broadcast(game_id, _state_message(game))
            _, ai_path = await asyncio.to_thread(
                search, [row[:] for row in game.board], "b", game.ai_difficulty
            )
            if ai_path is None:
                game.status = GameStatus.finished
                game.winner_id = game.white_player_id
                game.finished_at = datetime.now(UTC)
            elif consume_clock_on_move(game):
                # AI ran out of time while thinking.
                pass
            else:
                new_b2, captured2, new_turn2, winner2 = apply_move(
                    deepcopy(game.board), ai_path, "b"
                )
                game.board = new_b2
                game.turn = new_turn2
                game.move_count += 1
                db.add(Move(
                    game_id=game.id,
                    player_id=AI_BOT_ID,
                    move_number=game.move_count,
                    path=ai_path,
                    captured=captured2,
                ))
                if winner2 is not None:
                    game.status = GameStatus.finished
                    game.winner_id = (
                        game.white_player_id if winner2 == "w" else game.black_player_id
                    )
                    game.finished_at = datetime.now(UTC)
            await db.commit()

        await db.refresh(game, ["white_player", "black_player"])
        return _state_message(game)
