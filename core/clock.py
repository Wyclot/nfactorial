"""Time-control clock logic for timed games.

Game.last_clock_update_at marks the moment the current player's clock started ticking
(either the start of the game or the moment the opponent finished their last move).
"""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from models.game import Game


def start_clock(game: "Game") -> None:
    """Initialize both clocks when a timed game becomes in-progress."""
    if game.time_initial_ms is None:
        return
    if game.white_time_ms is None:
        game.white_time_ms = game.time_initial_ms
    if game.black_time_ms is None:
        game.black_time_ms = game.time_initial_ms
    game.last_clock_update_at = datetime.now(UTC)


def _elapsed_ms(game: "Game", now: datetime) -> int:
    if game.last_clock_update_at is None:
        return 0
    return int((now - game.last_clock_update_at).total_seconds() * 1000)


def detect_timeout(game: "Game") -> bool:
    """If the side to move has run out of time, mark game as finished. Returns True if applied."""
    from models.game import GameStatus

    if game.time_initial_ms is None or game.status != GameStatus.in_progress:
        return False
    if game.last_clock_update_at is None:
        return False
    now = datetime.now(UTC)
    elapsed = _elapsed_ms(game, now)
    cur_clock = game.white_time_ms if game.turn == "w" else game.black_time_ms
    if cur_clock is None or elapsed < cur_clock:
        return False
    if game.turn == "w":
        game.white_time_ms = 0
        game.winner_id = game.black_player_id
    else:
        game.black_time_ms = 0
        game.winner_id = game.white_player_id
    game.status = GameStatus.finished
    game.finished_at = now
    game.last_clock_update_at = now
    return True


def consume_clock_on_move(game: "Game") -> bool:
    """Deduct thinking time from the moving player. Returns True if they timed out.
    If True, caller must NOT apply the move — the game is already finished.
    """
    from models.game import GameStatus

    if game.time_initial_ms is None or game.last_clock_update_at is None:
        return False
    now = datetime.now(UTC)
    elapsed = _elapsed_ms(game, now)
    cur_clock = (game.white_time_ms if game.turn == "w" else game.black_time_ms) or 0
    remaining = cur_clock - elapsed
    if remaining <= 0:
        if game.turn == "w":
            game.white_time_ms = 0
            game.winner_id = game.black_player_id
        else:
            game.black_time_ms = 0
            game.winner_id = game.white_player_id
        game.status = GameStatus.finished
        game.finished_at = now
        game.last_clock_update_at = now
        return True
    new_clock = remaining + (game.time_increment_ms or 0)
    if game.turn == "w":
        game.white_time_ms = new_clock
    else:
        game.black_time_ms = new_clock
    game.last_clock_update_at = now
    return False
