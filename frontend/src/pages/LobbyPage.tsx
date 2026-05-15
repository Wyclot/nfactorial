import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { Difficulty, GameListItem } from '../types';

type TcKey = 'untimed' | 'blitz3' | 'blitz5' | 'bullet1';

const TIME_CONTROLS: Record<TcKey, { label: string; body?: { initial_seconds: number; increment_seconds: number } }> = {
  untimed: { label: 'Untimed' },
  blitz3:  { label: 'Blitz 3+2',  body: { initial_seconds: 180, increment_seconds: 2 } },
  blitz5:  { label: 'Blitz 5+0',  body: { initial_seconds: 300, increment_seconds: 0 } },
  bullet1: { label: 'Bullet 1+0', body: { initial_seconds: 60,  increment_seconds: 0 } },
};

export function LobbyPage() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState<GameListItem[]>([]);
  const [mine, setMine] = useState<GameListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tc, setTc] = useState<TcKey>('untimed');
  const tcBody = TIME_CONTROLS[tc].body;

  async function refresh() {
    setError(null);
    try {
      const [o, m] = await Promise.all([api.listOpenGames(), api.listMyGames()]);
      setOpen(o);
      setMine(m);
    } catch (e: any) {
      setError(e.message ?? 'Failed to load');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  async function create() {
    try {
      const g = await api.createGame(tcBody);
      navigate(`/game/${g.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function quickMatch() {
    try {
      const g = await api.quickMatch(tcBody);
      navigate(`/game/${g.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function playVsAi(difficulty: Difficulty) {
    try {
      const g = await api.createAiGame(difficulty, tcBody);
      navigate(`/game/${g.id}`);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function join(id: string) {
    try {
      await api.joinGame(id);
      navigate(`/game/${id}`);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 400) {
        // Maybe already joined — just open it.
        navigate(`/game/${id}`);
        return;
      }
      setError(e.message);
    }
  }

  if (loading) return <p>Loading…</p>;

  return (
    <div className="lobby">
      <header className="lobby-header">
        <h1>Lobby</h1>
        <div>
          <span>{user?.name ?? user?.email}</span>
          <button onClick={() => navigate('/shop')}>🛍️ Shop</button>
          <button onClick={signOut}>Sign out</button>
        </div>
      </header>

      <section>
        <label style={{ display: 'block', marginBottom: 8, fontSize: 13, color: '#aaa' }}>
          Time control
        </label>
        <select
          value={tc}
          onChange={(e) => setTc(e.target.value as TcKey)}
          style={{
            background: '#3a3a3a', color: '#eee', border: '1px solid #555',
            padding: '8px 10px', borderRadius: 6, fontSize: 14, marginBottom: 12,
          }}
        >
          {(Object.keys(TIME_CONTROLS) as TcKey[]).map((k) => (
            <option key={k} value={k}>{TIME_CONTROLS[k].label}</option>
          ))}
        </select>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={quickMatch}>⚡ Quick match</button>
          <button onClick={create}>+ Create new game</button>
        </div>
      </section>

      <section>
        <h2>🤖 Play vs AI</h2>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={() => playVsAi('easy')}>Easy</button>
          <button onClick={() => playVsAi('medium')}>Medium</button>
          <button onClick={() => playVsAi('hard')}>Hard</button>
        </div>
      </section>

      {error && <p className="error">{error}</p>}

      <section>
        <h2>Open games ({open.length})</h2>
        {open.length === 0 && <p>No open games. Create one!</p>}
        <ul>
          {open.map((g) => (
            <li key={g.id}>
              <span>{g.white_player.name ?? 'White player'}</span>
              {g.white_player.id === user?.id ? (
                <button onClick={() => navigate(`/game/${g.id}`)}>Open (yours)</button>
              ) : (
                <button onClick={() => join(g.id)}>Join</button>
              )}
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2>My games ({mine.length})</h2>
        <ul>
          {mine.map((g) => (
            <li key={g.id}>
              <span>vs {g.white_player.name ?? '...'} — {g.status}</span>
              <button onClick={() => navigate(`/game/${g.id}`)}>Open</button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
