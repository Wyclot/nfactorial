"""Checkers AI: legal move generation, evaluation, minimax with alpha-beta.

Designed for both:
- Picking AI moves in real-time gameplay (medium depth, fast)
- Post-game analysis (higher depth, comparing actual vs best move)

Scores are from White's perspective: positive = White better, negative = Black better.
"""

import math
from typing import List, Optional, Tuple

from core.checkers import (
    BOARD_SIZE,
    captures_from,
    color_has_capture,
    is_black,
    is_white,
    simple_moves_from,
)

SIZE = BOARD_SIZE

Path = List[List[int]]
Board = List[List[str]]


# ---------- Move generation ----------

def enumerate_paths(board: Board, turn: str) -> List[Path]:
    """All legal moves for `turn` as paths (lists of [r,c] squares)."""
    must_capture = color_has_capture(board, turn)
    paths: List[Path] = []
    for r in range(SIZE):
        for c in range(SIZE):
            p = board[r][c]
            mine = (turn == 'w' and is_white(p)) or (turn == 'b' and is_black(p))
            if not mine:
                continue
            if must_capture:
                caps = captures_from(board, r, c)
                if not caps:
                    continue
                paths.extend(_extend_captures(board, [[r, c]], p))
            else:
                for nr, nc in simple_moves_from(board, r, c):
                    paths.append([[r, c], [nr, nc]])
    return paths


def _extend_captures(board: Board, prefix: Path, piece: str) -> List[Path]:
    """Recursively enumerate maximal capture sequences. English rule: promotion ends the chain."""
    r, c = prefix[-1]
    caps = captures_from(board, r, c, piece)
    if not caps:
        return [prefix]
    results: List[Path] = []
    # captures_from returns (to_r, to_c, captured_r, captured_c)
    for tr, tc, mid_r, mid_c in caps:
        b = [row[:] for row in board]
        b[r][c] = '.'
        b[mid_r][mid_c] = '.'
        new_piece = piece
        promoted = False
        if piece == 'w' and tr == 0:
            new_piece = 'W'
            promoted = True
        elif piece == 'b' and tr == SIZE - 1:
            new_piece = 'B'
            promoted = True
        b[tr][tc] = new_piece
        new_prefix = prefix + [[tr, tc]]
        if promoted:
            results.append(new_prefix)
        else:
            results.extend(_extend_captures(b, new_prefix, new_piece))
    return results


def apply_path(board: Board, path: Path) -> Board:
    """Apply a legal path (from enumerate_paths) and return a new board."""
    b = [row[:] for row in board]
    r0, c0 = path[0]
    piece = b[r0][c0]
    if len(path) == 2 and abs(path[1][0] - r0) == 1:
        b[r0][c0] = '.'
        r1, c1 = path[1]
        if piece == 'w' and r1 == 0:
            piece = 'W'
        elif piece == 'b' and r1 == SIZE - 1:
            piece = 'B'
        b[r1][c1] = piece
        return b
    b[r0][c0] = '.'
    for i in range(1, len(path)):
        pr, pc = path[i - 1]
        tr, tc = path[i]
        mr, mc = (pr + tr) // 2, (pc + tc) // 2
        b[mr][mc] = '.'
        if piece == 'w' and tr == 0:
            piece = 'W'
        elif piece == 'b' and tr == SIZE - 1:
            piece = 'B'
    tr, tc = path[-1]
    b[tr][tc] = piece
    return b


# ---------- Evaluation ----------

PIECE_VALUE = {'.': 0.0, 'w': 1.0, 'W': 1.7, 'b': -1.0, 'B': -1.7}


def evaluate(board: Board) -> float:
    score = 0.0
    for r in range(SIZE):
        for c in range(SIZE):
            p = board[r][c]
            if p == '.':
                continue
            score += PIECE_VALUE[p]
            # Small positional bonus: men get rewarded for advancing toward promotion.
            if p == 'w':
                score += (SIZE - 1 - r) * 0.02
            elif p == 'b':
                score -= r * 0.02
            # Center bias.
            center = 3.5
            d = max(abs(r - center), abs(c - center))
            bias = (3.5 - d) * 0.01
            if p in ('w', 'W'):
                score += bias
            else:
                score -= bias
    return score


# ---------- Minimax with alpha-beta ----------

def search(board: Board, turn: str, depth: int) -> Tuple[float, Optional[Path]]:
    return _minimax(board, turn, depth, -math.inf, math.inf)


def _minimax(board: Board, turn: str, depth: int, alpha: float, beta: float) -> Tuple[float, Optional[Path]]:
    moves = enumerate_paths(board, turn)
    if not moves:
        # Current side has no moves → loses.
        return (-math.inf if turn == 'w' else math.inf), None
    if depth == 0:
        return evaluate(board), None

    best_path: Optional[Path] = None
    next_turn = 'b' if turn == 'w' else 'w'

    if turn == 'w':
        value = -math.inf
        for move in moves:
            v, _ = _minimax(apply_path(board, move), next_turn, depth - 1, alpha, beta)
            if v > value:
                value, best_path = v, move
            if value > alpha:
                alpha = value
            if alpha >= beta:
                break
        return value, best_path
    else:
        value = math.inf
        for move in moves:
            v, _ = _minimax(apply_path(board, move), next_turn, depth - 1, alpha, beta)
            if v < value:
                value, best_path = v, move
            if value < beta:
                beta = value
            if alpha >= beta:
                break
        return value, best_path


# ---------- Post-game analysis ----------

VERDICT_GOOD = 'good'
VERDICT_INACCURACY = 'inaccuracy'
VERDICT_MISTAKE = 'mistake'
VERDICT_BLUNDER = 'blunder'


def analyze_game(initial_board: Board, moves: List[Path], depth: int = 3) -> List[dict]:
    """Walk the game and annotate each move with verdict + best alternative.

    `moves` is the actual sequence of paths played (in order).
    """
    board = [row[:] for row in initial_board]
    turn = 'w'
    annotations: List[dict] = []

    for idx, actual in enumerate(moves):
        # Best move at this position.
        best_score, best_path = search(board, turn, depth)

        # Apply actual move.
        after = apply_path(board, actual)

        # Eval the resulting position one ply shallower.
        next_turn = 'b' if turn == 'w' else 'w'
        actual_score, _ = search(after, next_turn, max(depth - 1, 1))

        # Loss-from-best for whoever moved.
        if turn == 'w':
            loss = best_score - actual_score  # white wants high; lower actual = bad
        else:
            loss = actual_score - best_score  # black wants low; higher actual = bad

        if loss < 0.3:
            verdict = VERDICT_GOOD
        elif loss < 1.0:
            verdict = VERDICT_INACCURACY
        elif loss < 2.5:
            verdict = VERDICT_MISTAKE
        else:
            verdict = VERDICT_BLUNDER

        annotations.append({
            'move_number': idx + 1,
            'by': turn,
            'verdict': verdict,
            'eval_loss': round(loss, 2),
            'best_path': best_path or actual,
            'comment': _comment(board, turn, actual, best_path, loss),
        })

        board = after
        turn = next_turn

    return annotations


def _is_capture_path(path: Path) -> bool:
    if len(path) > 2:
        return True
    return abs(path[1][0] - path[0][0]) == 2


def _captures_count(path: Path) -> int:
    return len(path) - 1 if _is_capture_path(path) else 0


def _comment(board: Board, turn: str, actual: Path, best: Optional[Path], loss: float) -> str:
    if best is None:
        return "Forced move."
    actual_caps = _captures_count(actual)
    best_caps = _captures_count(best) if best else 0
    if best_caps > actual_caps:
        diff = best_caps - actual_caps
        return f"Missed a capture — could have taken {diff} more piece{'s' if diff > 1 else ''}."
    if loss < 0.3:
        return "Good move."
    if loss < 1.0:
        return "Slightly inaccurate — a better continuation existed."
    if loss < 2.5:
        return "Mistake. This concedes the initiative."
    return "Blunder — this loses material or position significantly."
