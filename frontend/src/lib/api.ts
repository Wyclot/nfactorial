import { clearTokens, getAccessToken, getRefreshToken, setTokens } from './tokens';
import type {
  AnalysisItem,
  Difficulty,
  Game,
  GameListItem,
  Payment,
  PaymentInitResponse,
  Skin,
  SkinKind,
  TokenResponse,
  User,
  UserSkin,
} from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  if (refreshing) return refreshing;
  const refresh_token = getRefreshToken();
  if (!refresh_token) return null;

  refreshing = (async () => {
    try {
      const res = await fetch(`${API_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token }),
      });
      if (!res.ok) {
        clearTokens();
        return null;
      }
      const data: TokenResponse = await res.json();
      setTokens(data.access_token, data.refresh_token);
      return data.access_token;
    } finally {
      refreshing = null;
    }
  })();

  return refreshing;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true): Promise<T> {
  const access = getAccessToken();
  const headers = new Headers(init.headers);
  if (access) headers.set('Authorization', `Bearer ${access}`);
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const res = await fetch(`${API_URL}${path}`, { ...init, headers });

  if (res.status === 401 && retry) {
    const newAccess = await refreshAccessToken();
    if (newAccess) {
      return request<T>(path, init, false);
    }
    throw new ApiError(401, 'Unauthorized');
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = body.detail;
    } catch {}
    throw new ApiError(res.status, detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export const api = {
  googleSignIn: (id_token: string) =>
    request<TokenResponse>('/auth/google', {
      method: 'POST',
      body: JSON.stringify({ id_token }),
    }),

  me: () => request<User>('/me'),

  listOpenGames: () => request<GameListItem[]>('/games'),
  listMyGames: () => request<GameListItem[]>('/games/mine'),

  createGame: (timeControl?: { initial_seconds: number; increment_seconds: number }) =>
    request<Game>('/games', {
      method: 'POST',
      body: timeControl ? JSON.stringify(timeControl) : undefined,
    }),
  createAiGame: (
    difficulty: Difficulty,
    timeControl?: { initial_seconds: number; increment_seconds: number },
  ) =>
    request<Game>('/games/ai', {
      method: 'POST',
      body: JSON.stringify({ difficulty, ...(timeControl ?? {}) }),
    }),
  quickMatch: (timeControl?: { initial_seconds: number; increment_seconds: number }) =>
    request<Game>('/games/quick-match', {
      method: 'POST',
      body: timeControl ? JSON.stringify(timeControl) : undefined,
    }),
  getGame: (id: string) => request<Game>(`/games/${id}`),
  joinGame: (id: string) => request<Game>(`/games/${id}/join`, { method: 'POST' }),
  abortGame: (id: string) => request<Game>(`/games/${id}/abort`, { method: 'POST' }),
  resignGame: (id: string) => request<Game>(`/games/${id}/resign`, { method: 'POST' }),
  offerDraw: (id: string) => request<Game>(`/games/${id}/draw/offer`, { method: 'POST' }),
  acceptDraw: (id: string) => request<Game>(`/games/${id}/draw/accept`, { method: 'POST' }),
  declineDraw: (id: string) => request<Game>(`/games/${id}/draw/decline`, { method: 'POST' }),
  makeMove: (id: string, path: number[][]) =>
    request<Game>(`/games/${id}/move`, { method: 'POST', body: JSON.stringify({ path }) }),
  analyzeGame: (id: string, depth = 3) =>
    request<AnalysisItem[]>(`/games/${id}/analysis?depth=${depth}`),

  logout: () => request<void>('/auth/logout', { method: 'POST' }),

  // Shop / skins
  listSkins: () => request<Skin[]>('/skins'),
  listMySkins: () => request<UserSkin[]>('/skins/me'),
  buySkin: (skinId: string) =>
    request<PaymentInitResponse>(`/payments/skin/${skinId}`, { method: 'POST' }),
  equipSkin: (skinId: string) =>
    request<Skin>(`/skins/${skinId}/equip`, { method: 'POST' }),
  unequipKind: (kind: SkinKind) =>
    request<{ ok: boolean }>(`/skins/unequip/${kind}`, { method: 'POST' }),
  getPayment: (paymentId: string) => request<Payment>(`/payments/${paymentId}`),
};
