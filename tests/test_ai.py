"""Basic smoke tests for the AI engine. Run from project root:
    python tests/test_ai.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ai import apply_path, enumerate_paths, evaluate, search  # noqa: E402
from core.checkers import INITIAL_BOARD  # noqa: E402


def _empty_board():
    return [['.'] * 8 for _ in range(8)]


def test_initial_white_has_seven_moves():
    paths = enumerate_paths([row[:] for row in INITIAL_BOARD], 'w')
    assert len(paths) == 7, f"expected 7 opening moves, got {len(paths)}"


def test_initial_black_has_seven_moves():
    paths = enumerate_paths([row[:] for row in INITIAL_BOARD], 'b')
    assert len(paths) == 7, f"expected 7 opening moves for black, got {len(paths)}"


def test_simple_move_no_captures_present():
    board = _empty_board()
    board[5][2] = 'w'
    paths = enumerate_paths(board, 'w')
    # White man at (5,2) can move to (4,1) or (4,3).
    assert sorted(paths) == sorted([[[5, 2], [4, 1]]] + [[[5, 2], [4, 3]]]), paths


def test_forced_single_capture():
    board = _empty_board()
    board[4][3] = 'w'
    board[3][2] = 'b'
    paths = enumerate_paths(board, 'w')
    assert paths == [[[4, 3], [2, 1]]], paths


def test_capture_is_mandatory_over_simple_move():
    board = _empty_board()
    board[4][3] = 'w'
    board[3][2] = 'b'
    board[6][1] = 'w'  # this piece has a simple move available
    paths = enumerate_paths(board, 'w')
    # Only the capture is legal — simple moves of the other piece must NOT appear.
    assert paths == [[[4, 3], [2, 1]]], paths


def test_multi_jump_chain():
    board = _empty_board()
    board[6][5] = 'w'
    board[5][4] = 'b'
    board[3][4] = 'b'
    paths = enumerate_paths(board, 'w')
    assert paths == [[[6, 5], [4, 3], [2, 5]]], paths


def test_promotion_ends_capture_chain():
    """If a man promotes mid-chain, the turn ends (English rule)."""
    board = _empty_board()
    board[2][3] = 'w'
    board[1][2] = 'b'
    # If white captures (1,2) it lands at (0,1) and promotes to king.
    # Even if another capture were available, it must not continue.
    paths = enumerate_paths(board, 'w')
    assert paths == [[[2, 3], [0, 1]]], paths


def test_apply_path_simple_move():
    board = _empty_board()
    board[5][2] = 'w'
    new_b = apply_path(board, [[5, 2], [4, 1]])
    assert new_b[5][2] == '.'
    assert new_b[4][1] == 'w'


def test_apply_path_capture_promotes():
    board = _empty_board()
    board[2][3] = 'w'
    board[1][2] = 'b'
    new_b = apply_path(board, [[2, 3], [0, 1]])
    assert new_b[2][3] == '.'
    assert new_b[1][2] == '.'
    assert new_b[0][1] == 'W', f"expected promotion to king, got {new_b[0][1]}"


def test_evaluate_material_balance():
    board = _empty_board()
    board[4][3] = 'w'
    board[3][4] = 'b'
    # Roughly balanced. Positional bonuses make it slightly nonzero, but small.
    score = evaluate(board)
    assert abs(score) < 0.5, f"expected near 0, got {score}"


def test_search_returns_legal_move_from_start():
    score, path = search([row[:] for row in INITIAL_BOARD], 'w', 2)
    assert path is not None and len(path) >= 2
    # The chosen path must be in the legal move list.
    legal = enumerate_paths([row[:] for row in INITIAL_BOARD], 'w')
    assert path in legal, f"AI picked illegal move: {path}"


def test_search_finds_forced_capture():
    """When a capture is available, search must return that capture."""
    board = _empty_board()
    board[4][3] = 'w'
    board[3][2] = 'b'
    _, path = search(board, 'w', 2)
    assert path == [[4, 3], [2, 1]], path


def main():
    tests = [name for name in sorted(globals()) if name.startswith('test_')]
    failed = 0
    for name in tests:
        try:
            globals()[name]()
            print(f"  ok  {name}")
        except AssertionError as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERR  {name}: {e!r}")
            failed += 1
    print()
    if failed:
        print(f"{failed}/{len(tests)} failed")
        sys.exit(1)
    print(f"all {len(tests)} passed")


if __name__ == '__main__':
    main()
