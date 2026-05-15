import { getAccessToken } from './tokens';
import type { Game } from '../types';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';

export type WSEvent =
  | { type: 'state'; game: Game }
  | { type: 'error'; detail: string }
  | { type: 'pong' };

type Listener = (e: WSEvent) => void;

export class GameSocket {
  private ws: WebSocket | null = null;
  private listeners = new Set<Listener>();
  private gameId: string;
  private retries = 0;
  private maxRetries = 5;
  private closed = false;
  private pingTimer: number | null = null;

  constructor(gameId: string) {
    this.gameId = gameId;
  }

  connect() {
    const token = getAccessToken();
    if (!token) {
      this.emit({ type: 'error', detail: 'No access token' });
      return;
    }
    const url = `${WS_URL}/ws/games/${this.gameId}?token=${encodeURIComponent(token)}`;
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.retries = 0;
      this.startPing();
    };

    this.ws.onmessage = (ev) => {
      try {
        const data: WSEvent = JSON.parse(ev.data);
        this.emit(data);
      } catch (e) {
        console.error('bad ws message', e);
      }
    };

    this.ws.onclose = () => {
      this.stopPing();
      if (this.closed) return;
      if (this.retries >= this.maxRetries) {
        this.emit({ type: 'error', detail: 'Connection lost' });
        return;
      }
      const delay = Math.min(1000 * 2 ** this.retries, 10000);
      this.retries++;
      setTimeout(() => {
        if (!this.closed) this.connect();
      }, delay);
    };

    this.ws.onerror = () => {
      // onclose will follow
    };
  }

  sendMove(path: number[][]) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type: 'move', path }));
    }
  }

  close() {
    this.closed = true;
    this.stopPing();
    this.ws?.close();
  }

  subscribe(fn: Listener): () => void {
    this.listeners.add(fn);
    return () => this.listeners.delete(fn);
  }

  private emit(e: WSEvent) {
    this.listeners.forEach((fn) => fn(e));
  }

  private startPing() {
    this.pingTimer = window.setInterval(() => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'ping' }));
      }
    }, 25000);
  }

  private stopPing() {
    if (this.pingTimer !== null) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }
}
