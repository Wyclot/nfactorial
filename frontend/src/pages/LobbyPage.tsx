import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { Difficulty, GameListItem } from '../types';

type TcKey = 'untimed' | 'blitz3' | 'blitz5' | 'bullet1';

const TIME_CONTROLS: Record<TcKey, { label: string; body?: { initial_seconds: number; increment_seconds: number } }> = {
  untimed: { label: 'Untimed' },
  blitz3:  { label: '3 + 2',  body: { initial_seconds: 180, increment_seconds: 2 } },
  blitz5:  { label: '5 + 0',  body: { initial_seconds: 300, increment_seconds: 0 } },
  bullet1: { label: '1 + 0',  body: { initial_seconds: 60,  increment_seconds: 0 } },
};

function initials(name?: string | null, email?: string | null): string {
  const src = (name || email || '?').trim();
  return src.slice(0, 1).toUpperCase();
}

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
    } catch (e: any) { setError(e.message); }
  }

  async function quickMatch() {
    try {
      const g = await api.quickMatch(tcBody);
      navigate(`/game/${g.id}`);
    } catch (e: any) { setError(e.message); }
  }

  async function playVsAi(difficulty: Difficulty) {
    try {
      const g = await api.createAiGame(difficulty, tcBody);
      navigate(`/game/${g.id}`);
    } catch (e: any) { setError(e.message); }
  }

  async function join(id: string) {
    try {
      await api.joinGame(id);
      navigate(`/game/${id}`);
    } catch (e: any) {
      if (e instanceof ApiError && e.status === 400) {
        navigate(`/game/${id}`);
        return;
      }
      setError(e.message);
    }
  }

  if (loading) return <p className="muted">Loading lobby…</p>;

  return (
    <div className="lobby">
      <header className="app-header glass">
        <div className="brand">♟ Checkers Arena</div>
        <div className="right">
          <button onClick={() => navigate('/shop')}>🛍️ Shop</button>
          <div className="user-chip">
            <span className="avatar">{initials(user?.name, user?.email)}</span>
            <span>{user?.name ?? user?.email}</span>
          </div>
          <button className="btn-ghost" onClick={signOut}>Sign out</button>
        </div>
      </header>

      <section className="lobby-hero glass">
        <div>
          <h1>Ready for your next match?</h1>
          <p>Find an opponent, challenge a friend, or train with the AI.</p>
        </div>
        <span className="badge gradient">{mine.length} game{mine.length === 1 ? '' : 's'} in history</span>
      </section>

      <div className="time-control-row">
        <span className="label">Time control</span>
        {(Object.keys(TIME_CONTROLS) as TcKey[]).map((k) => (
          <button
            key={k}
            className={`tc-chip ${tc === k ? 'active' : ''}`}
            onClick={() => setTc(k)}
          >
            {TIME_CONTROLS[k].label}
          </button>
        ))}
      </div>

      <div className="action-grid">
        <button className="action-card cyan" onClick={quickMatch}>
          <span className="icon">⚡</span>
          <h3>Quick Match</h3>
          <span className="desc">Auto-pair with another player at the selected time control.</span>
        </button>
        <button className="action-card" onClick={create}>
          <span className="icon">＋</span>
          <h3>Create Game</h3>
          <span className="desc">Open a room and share the link — your friend joins as black.</span>
        </button>
        <div className="action-card emerald" style={{ cursor: 'default' }}>
          <span className="icon">🤖</span>
          <h3>Play vs AI</h3>
          <span className="desc">Pick a difficulty — bot moves automatically after you.</span>
        </div>
      </div>

      <h2 className="section-title">AI Opponent</h2>
      <div className="ai-difficulty-row">
        <button className="diff-card easy" onClick={() => playVsAi('easy')}>
          <span className="lvl">Level 1</span>
          <h4>Easy</h4>
          <span className="desc">Plays plausible moves. Great for warming up.</span>
        </button>
        <button className="diff-card medium" onClick={() => playVsAi('medium')}>
          <span className="lvl">Level 2</span>
          <h4>Medium</h4>
          <span className="desc">Balanced challenge — punishes simple blunders.</span>
        </button>
        <button className="diff-card hard" onClick={() => playVsAi('hard')}>
          <span className="lvl">Level 3</span>
          <h4>Hard</h4>
          <span className="desc">Searches 6 plies ahead — sharp tactics.</span>
        </button>
      </div>

      {error && <p className="error" style={{ marginTop: 18 }}>{error}</p>}

      <h2 className="section-title">
        Open games <span className="count">{open.length}</span>
      </h2>
      <div className="list-card glass">
        {open.length === 0 ? (
          <div className="empty">
            <div className="big">🕊</div>
            <div>No open games right now. Create one or start a Quick Match.</div>
          </div>
        ) : (
          open.map((g) => (
            <div key={g.id} className="list-row">
              <div className="left">
                <span className="avatar">{initials(g.white_player.name)}</span>
                <div>
                  <div style={{ fontWeight: 600 }}>{g.white_player.name ?? 'Anonymous'}</div>
                  <div className="meta">Waiting for opponent</div>
                </div>
              </div>
              {g.white_player.id === user?.id ? (
                <button onClick={() => navigate(`/game/${g.id}`)}>Open (yours)</button>
              ) : (
                <button className="btn-cyan" onClick={() => join(g.id)}>Join as black</button>
              )}
            </div>
          ))
        )}
      </div>

      <h2 className="section-title">
        My games <span className="count">{mine.length}</span>
      </h2>
      <div className="list-card glass">
        {mine.length === 0 ? (
          <div className="empty">
            <div className="big">📜</div>
            <div>You haven't played any games yet.</div>
          </div>
        ) : (
          mine.map((g) => (
            <div key={g.id} className="list-row">
              <div className="left">
                <span className="avatar">{initials(g.white_player.name)}</span>
                <div>
                  <div style={{ fontWeight: 600 }}>{g.white_player.name ?? 'Anonymous'}</div>
                  <div className="meta">Status: {g.status}</div>
                </div>
              </div>
              <button onClick={() => navigate(`/game/${g.id}`)}>Open</button>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
