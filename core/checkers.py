"""English/American draughts (checkers).

Board: 8x8 list of lists of single-char strings.
  '.' empty, 'w' white man, 'W' white king, 'b' black man, 'B' black king.
White starts at the bottom (rows 5-7) and moves toward row 0.
Black starts at the top (rows 0-2) and moves toward row 7.
Captures are mandatory; multi-jumps must be continued.
"""

from copy import deepcopy
from typing import List, Optional, Tuple

BOARD_SIZE = 8

INITIAL_BOARD: List[List[str]] = [
    ['.', 'b', '.', 'b', '.', 'b', '.', 'b'],
    ['b', '.', 'b', '.', 'b', '.', 'b', '.'],
    ['.', 'b', '.', 'b', '.', 'b', '.', 'b'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['.', '.', '.', '.', '.', '.', '.', '.'],
    ['w', '.', 'w', '.', 'w', '.', 'w', '.'],
    ['.', 'w', '.', 'w', '.', 'w', '.', 'w'],
    ['w', '.', 'w', '.', 'w', '.', 'w', '.'],
]


def is_white(p: str) -> bool:
    return p in ('w', 'W')


def is_black(p: str) -> bool:
    return p in ('b', 'B')


def is_opponent(a: str, b: str) -> bool:
    return (is_white(a) and is_black(b)) or (is_black(a) and is_white(b))


def in_bounds(r: int, c: int) -> bool:
    return 0 <= r < BOARD_SIZE and 0 <= c < BOARD_SIZE


def piece_directions(piece: str) -> List[Tuple[int, int]]:
    if piece == 'w':
        return [(-1, -1), (-1, 1)]
    if piece == 'b':
        return [(1, -1), (1, 1)]
    if piece in ('W', 'B'):
        return [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    return []


def simple_moves_from(board: List[List[str]], r: int, c: int) -> List[Tuple[int, int]]:
    moves = []
    piece = board[r][c]
    for dr, dc in piece_directions(piece):
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc) and board[nr][nc] == '.':
            moves.append((nr, nc))
    return moves


def captures_from(board: List[List[str]], r: int, c: int, piece: Optional[str] = None) -> List[Tuple[int, int, int, int]]:
    """Returns list of (to_r, to_c, captured_r, captured_c) for one-jump captures."""
    if piece is None:
        piece = board[r][c]
    caps = []
    for dr, dc in piece_directions(piece):
        mid_r, mid_c = r + dr, c + dc
        to_r, to_c = r + 2 * dr, c + 2 * dc
        if not in_bounds(to_r, to_c):
            continue
        mid_piece = board[mid_r][mid_c]
        if mid_piece == '.' or not is_opponent(piece, mid_piece):
            continue
        if board[to_r][to_c] != '.':
            continue
        caps.append((to_r, to_c, mid_r, mid_c))
    return caps


def color_has_capture(board: List[List[str]], color: str) -> bool:
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            p = board[r][c]
            if color == 'w' and is_white(p) and captures_from(board, r, c):
                return True
            if color == 'b' and is_black(p) and captures_from(board, r, c):
                return True
    return False


def color_has_any_move(board: List[List[str]], color: str) -> bool:
    if color_has_capture(board, color):
        return True
    for r in range(BOARD_SIZE):
        for c in range(BOARD_SIZE):
            p = board[r][c]
            if (color == 'w' and is_white(p)) or (color == 'b' and is_black(p)):
                if simple_moves_from(board, r, c):
                    return True
    return False


def apply_move(
    board: List[List[str]],
    path: List[List[int]],
    turn: str,
) -> Tuple[List[List[str]], int, str, Optional[str]]:
    """Apply a move described by `path` (list of [r,c] squares) for `turn` ('w'|'b').

    Mutates `board` (pass a deepcopy if you need to keep the original).
    Returns (board, captured_count, new_turn, winner_color_or_None).
    Raises ValueError on illegal moves.
    """
    if turn not in ('w', 'b'):
        raise ValueError("turn must be 'w' or 'b'")
    if not isinstance(path, list) or len(path) < 2:
        raise ValueError("path must have at least 2 squares")
    for sq in path:
        if not (isinstance(sq, (list, tuple)) and len(sq) == 2):
            raise ValueError("each square must be [row, col]")
        if not in_bounds(sq[0], sq[1]):
            raise ValueError("square out of bounds")

    r0, c0 = path[0]
    piece = board[r0][c0]
    if piece == '.':
        raise ValueError("no piece at start square")
    if turn == 'w' and not is_white(piece):
        raise ValueError("not your piece")
    if turn == 'b' and not is_black(piece):
        raise ValueError("not your piece")

    must_capture = color_has_capture(board, turn)

    if len(path) == 2 and abs(path[1][0] - r0) == 1:
        # Simple (non-capturing) move
        if must_capture:
            raise ValueError("capture is available — simple move not allowed")
        r1, c1 = path[1]
        if (r1, c1) not in simple_moves_from(board, r0, c0):
            raise ValueError("illegal simple move")
        board[r0][c0] = '.'
        board[r1][c1] = _maybe_promote(piece, r1)
        captured = 0
    else:
        # Capture sequence
        if not must_capture:
            raise ValueError("no captures available — use a simple move")
        captured = 0
        cur_r, cur_c = r0, c0
        cur_piece = piece
        board[r0][c0] = '.'
        for i in range(1, len(path)):
            tr, tc = path[i]
            dr, dc = tr - cur_r, tc - cur_c
            if abs(dr) != 2 or abs(dc) != 2:
                raise ValueError("each jump must be 2 squares diagonally")
            step = (dr // 2, dc // 2)
            if step not in piece_directions(cur_piece):
                raise ValueError("illegal direction for this piece")
            mid_r, mid_c = cur_r + step[0], cur_c + step[1]
            mid_piece = board[mid_r][mid_c]
            if mid_piece == '.' or not is_opponent(cur_piece, mid_piece):
                raise ValueError("must jump over opponent piece")
            if board[tr][tc] != '.':
                raise ValueError("landing square not empty")
            board[mid_r][mid_c] = '.'
            captured += 1
            cur_r, cur_c = tr, tc
            promoted = _maybe_promote(cur_piece, tr)
            if promoted != cur_piece:
                cur_piece = promoted
                # English rule: promotion ends the turn even if more captures exist.
                if i != len(path) - 1:
                    raise ValueError("promotion ends the turn — cannot continue capturing")
        board[cur_r][cur_c] = cur_piece
        # Mandatory continuation if more captures are still available.
        if captures_from(board, cur_r, cur_c):
            raise ValueError("must continue capturing with the same piece")

    new_turn = 'b' if turn == 'w' else 'w'
    winner = _check_winner(board, new_turn, turn)
    return board, captured, new_turn, winner


def _maybe_promote(piece: str, row: int) -> str:
    if piece == 'w' and row == 0:
        return 'W'
    if piece == 'b' and row == BOARD_SIZE - 1:
        return 'B'
    return piece


def _check_winner(board: List[List[str]], next_turn: str, just_moved: str) -> Optional[str]:
    white = sum(1 for row in board for p in row if is_white(p))
    black = sum(1 for row in board for p in row if is_black(p))
    if white == 0:
        return 'b'
    if black == 0:
        return 'w'
    if not color_has_any_move(board, next_turn):
        return just_moved
    return None


def new_board() -> List[List[str]]:
    return deepcopy(INITIAL_BOARD)
