export type Cell = '.' | 'w' | 'W' | 'b' | 'B';
export type Board = Cell[][];

export type GameStatus = 'waiting' | 'in_progress' | 'finished' | 'aborted';

export interface Player {
  id: string;
  name: string | null;
}

export type Difficulty = 'easy' | 'medium' | 'hard';

export interface Game {
  id: string;
  white_player: Player;
  black_player: Player | null;
  board: Board;
  turn: 'w' | 'b';
  status: GameStatus;
  winner_id: string | null;
  draw_offered_by: string | null;
  ai_difficulty: number | null;
  time_initial_ms: number | null;
  time_increment_ms: number;
  white_time_ms: number | null;
  black_time_ms: number | null;
  last_clock_update_at: string | null;
  move_count: number;
  created_at: string;
}

export interface TimeControlPreset {
  label: string;
  body?: { initial_seconds: number; increment_seconds: number };
}

export type SkinKind = 'piece_set' | 'board' | 'effect';

export interface Skin {
  id: string;
  code: string;
  kind: SkinKind;
  name: string;
  description: string | null;
  price_kzt: number;
  preview_url: string | null;
  is_active: boolean;
  owned: boolean;
  equipped: boolean;
}

export interface Payment {
  id: string;
  skin_id: string;
  invoice_id: string;
  amount: number;
  status: PaymentStatus;
  created_at: string;
  paid_at: string | null;
  refunded_at: string | null;
}

export interface UserSkin {
  id: string;
  skin: Skin;
  created_at: string;
}

export type PaymentStatus = 'pending' | 'charged' | 'failed' | 'refunded' | 'cancelled';

export interface PaymentInitResponse {
  invoice_id: string;
  invoice_url: string | null;
  amount: number;
  expire_date: string | null;
  status: PaymentStatus;
}

export interface GameListItem {
  id: string;
  white_player: Player;
  status: GameStatus;
  created_at: string;
}

export interface User {
  id: string;
  email: string | null;
  name: string | null;
  surname: string | null;
  created_at: string;
  active_piece_skin_code: string | null;
  active_board_skin_code: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export type Verdict = 'good' | 'inaccuracy' | 'mistake' | 'blunder';

export interface AnalysisItem {
  move_number: number;
  by: 'w' | 'b';
  verdict: Verdict;
  eval_loss: number;
  best_path: number[][];
  comment: string;
}
