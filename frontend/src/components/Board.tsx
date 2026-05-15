import { useMemo, useState } from 'react';
import type { Board as BoardT, Cell } from '../types';
import { applyJump, capturesFrom, colorHasCapture, legalDestinations } from '../lib/checkers';

interface Props {
  board: BoardT;
  turn: 'w' | 'b';
  myColor: 'w' | 'b' | null;
  disabled: boolean;
  onMove: (path: number[][]) => void;
  /** Active piece skin code (e.g. "piece_pearl"). Null/empty → default look. */
  pieceSkinCode?: string | null;
  /** Active board skin code (e.g. "board_marble"). Null/empty → default look. */
  boardSkinCode?: string | null;
}

export function Board({
  board,
  turn,
  myColor,
  disabled,
  onMove,
  pieceSkinCode,
  boardSkinCode,
}: Props) {
  // Selected piece + accumulated path (for multi-jumps).
  const [path, setPath] = useState<number[][]>([]);
  const [virtualBoard, setVirtualBoard] = useState<BoardT | null>(null);

  const isMyTurn = !disabled && myColor === turn;

  const activeBoard = virtualBoard ?? board;
  const selected = path[path.length - 1];

  const legalNow = useMemo(() => {
    if (!isMyTurn || path.length === 0) return [];
    const [r, c] = selected;
    if (path.length === 1) {
      return legalDestinations(activeBoard, r, c, turn);
    }
    // Already mid-capture — only further captures allowed.
    return capturesFrom(activeBoard, r, c);
  }, [activeBoard, selected, isMyTurn, path.length, turn]);

  function resetSelection() {
    setPath([]);
    setVirtualBoard(null);
  }

  function clickSquare(r: number, c: number) {
    if (!isMyTurn) return;
    const cell = activeBoard[r][c];

    // Click empty when nothing selected — ignore.
    if (path.length === 0) {
      if (!isOwn(cell, turn)) return;
      // Can only pick a piece that has legal moves (forced capture rule).
      const legal = legalDestinations(board, r, c, turn);
      if (legal.length === 0) {
        const mustCapture = colorHasCapture(board, turn);
        if (mustCapture) return; // must pick a piece that can capture
        return;
      }
      setPath([[r, c]]);
      return;
    }

    const [sr, sc] = selected;

    // Click on selected piece again — deselect.
    if (sr === r && sc === c) {
      resetSelection();
      return;
    }

    // Click own piece while another is selected (and no captures yet) — reselect.
    if (path.length === 1 && isOwn(cell, turn)) {
      const legal = legalDestinations(board, r, c, turn);
      if (legal.length > 0) {
        setPath([[r, c]]);
        setVirtualBoard(null);
      }
      return;
    }

    // Try to make a step.
    const dest = legalNow.find(([dr, dc]) => dr === r && dc === c);
    if (!dest) return;

    const dr = r - sr;
    const isJump = Math.abs(dr) === 2;

    if (!isJump) {
      // Simple move — send right away.
      onMove([[sr, sc], [r, c]]);
      resetSelection();
      return;
    }

    // Jump — apply to virtual board, check for continuation.
    const newBoard = applyJump(activeBoard, sr, sc, r, c);
    const newPath = [...path, [r, c]];
    const more = capturesFrom(newBoard, r, c);
    // English rule: promotion ends the turn.
    const piece = activeBoard[sr][sc];
    const promoted = (piece === 'w' && r === 0) || (piece === 'b' && r === 7);
    if (promoted || more.length === 0) {
      onMove(newPath);
      resetSelection();
    } else {
      setPath(newPath);
      setVirtualBoard(newBoard);
    }
  }

  const boardThemeClass = boardSkinCode ? `theme-${boardSkinCode}` : '';

  // Board orientation is fixed: row 0 (black side) at the top, row 7 (white side) at the
  // bottom — same view for both players. Coordinates (r, c) come straight from the server
  // state and round-trip back to the server unchanged. Do NOT add per-color flipping here.
  return (
    <div className={`board ${boardThemeClass}`}>
      {activeBoard.map((row, r) =>
        row.map((cell, c) => {
          const dark = (r + c) % 2 === 1;
          const isSelected = selected && selected[0] === r && selected[1] === c;
          const isLegal = legalNow.some(([lr, lc]) => lr === r && lc === c);
          return (
            <div
              key={`${r}-${c}`}
              className={`square ${dark ? 'dark' : 'light'} ${isSelected ? 'selected' : ''} ${isLegal ? 'legal' : ''}`}
              onClick={() => clickSquare(r, c)}
            >
              {cell !== '.' && <Piece cell={cell} skinCode={pieceSkinCode} />}
            </div>
          );
        })
      )}
    </div>
  );
}

function Piece({ cell, skinCode }: { cell: Cell; skinCode?: string | null }) {
  const color = cell === 'w' || cell === 'W' ? 'white' : 'black';
  const king = cell === 'W' || cell === 'B';
  const skinClass = skinCode ? `skin-${skinCode} ${color}` : `piece-${color}`;
  return (
    <div className={`piece ${skinClass}`}>
      {king && <span className="crown">♛</span>}
    </div>
  );
}

function isOwn(cell: Cell, turn: 'w' | 'b'): boolean {
  if (turn === 'w') return cell === 'w' || cell === 'W';
  return cell === 'b' || cell === 'B';
}
