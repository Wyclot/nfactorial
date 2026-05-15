import type { Board, Cell } from '../types';

export const SIZE = 8;

export const isWhite = (p: Cell) => p === 'w' || p === 'W';
export const isBlack = (p: Cell) => p === 'b' || p === 'B';
export const isOpponent = (a: Cell, b: Cell) =>
  (isWhite(a) && isBlack(b)) || (isBlack(a) && isWhite(b));

const inBounds = (r: number, c: number) => r >= 0 && r < SIZE && c >= 0 && c < SIZE;

function directions(p: Cell): [number, number][] {
  if (p === 'w') return [[-1, -1], [-1, 1]];
  if (p === 'b') return [[1, -1], [1, 1]];
  if (p === 'W' || p === 'B') return [[-1, -1], [-1, 1], [1, -1], [1, 1]];
  return [];
}

export function simpleMovesFrom(board: Board, r: number, c: number): [number, number][] {
  const p = board[r][c];
  const out: [number, number][] = [];
  for (const [dr, dc] of directions(p)) {
    const nr = r + dr, nc = c + dc;
    if (inBounds(nr, nc) && board[nr][nc] === '.') out.push([nr, nc]);
  }
  return out;
}

export function capturesFrom(board: Board, r: number, c: number, piece?: Cell): [number, number][] {
  const p = piece ?? board[r][c];
  const out: [number, number][] = [];
  for (const [dr, dc] of directions(p)) {
    const mr = r + dr, mc = c + dc;
    const tr = r + 2 * dr, tc = c + 2 * dc;
    if (!inBounds(tr, tc)) continue;
    const mp = board[mr][mc];
    if (mp === '.' || !isOpponent(p, mp)) continue;
    if (board[tr][tc] !== '.') continue;
    out.push([tr, tc]);
  }
  return out;
}

export function colorHasCapture(board: Board, color: 'w' | 'b'): boolean {
  for (let r = 0; r < SIZE; r++) {
    for (let c = 0; c < SIZE; c++) {
      const p = board[r][c];
      if (color === 'w' && isWhite(p) && capturesFrom(board, r, c).length) return true;
      if (color === 'b' && isBlack(p) && capturesFrom(board, r, c).length) return true;
    }
  }
  return false;
}

/** Returns legal destinations for a piece, given current turn. */
export function legalDestinations(board: Board, r: number, c: number, turn: 'w' | 'b'): [number, number][] {
  const p = board[r][c];
  if (turn === 'w' && !isWhite(p)) return [];
  if (turn === 'b' && !isBlack(p)) return [];
  const mustCapture = colorHasCapture(board, turn);
  if (mustCapture) {
    return capturesFrom(board, r, c);
  }
  return simpleMovesFrom(board, r, c);
}

/** Simulate a single jump and return resulting board (copy). */
export function applyJump(board: Board, fromR: number, fromC: number, toR: number, toC: number): Board {
  const b: Board = board.map((row) => [...row] as Cell[]);
  const piece = b[fromR][fromC];
  const midR = (fromR + toR) / 2;
  const midC = (fromC + toC) / 2;
  b[fromR][fromC] = '.';
  b[midR][midC] = '.';
  let placed: Cell = piece;
  if (piece === 'w' && toR === 0) placed = 'W';
  if (piece === 'b' && toR === SIZE - 1) placed = 'B';
  b[toR][toC] = placed;
  return b;
}
