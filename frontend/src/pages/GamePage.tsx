import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Analysis } from '../components/Analysis';
import { Board } from '../components/Board';
import { Clock } from '../components/Clock';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { GameSocket } from '../lib/ws';
import type { Game } from '../types';

function initials(name?: string | null): string {
  return (name ?? '?').trim().slice(0, 1).toUpperCase();
}

export function GamePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [game, setGame] = useState<Game | null>(null);
  const [receivedAt, setReceivedAt] = useState<number>(() => Date.now());
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [linkCopied, setLinkCopied] = useState(false);

  function applyGame(g: Game) {
    setGame(g);
    setReceivedAt(Date.now());
  }

  useEffect(() => {
    if (!id) return;
    api.getGame(id).then(applyGame).catch((e) => setError(e.message));

    const sock = new GameSocket(id);
    sock.connect();
    const unsub = sock.subscribe((ev) => {
      if (ev.type === 'state') {
        applyGame(ev.game);
        setConnected(true);
        setError(null);
      } else if (ev.type === 'error') {
        setError(ev.detail);
      }
    });

    return () => {
      unsub();
      sock.close();
    };
  }, [id]);

  if (!game) {
    return (
      <div>
        <button onClick={() => navigate('/')}>← Lobby</button>
        {error ? <p className="error" style={{ marginTop: 16 }}>{error}</p> : <p className="muted">Loading game…</p>}
      </div>
    );
  }

  const myColor: 'w' | 'b' | null =
    user?.id === game.white_player.id ? 'w' :
    user?.id === game.black_player?.id ? 'b' :
    null;

  const isPlayer = myColor !== null;
  const isFinished = game.status === 'finished' || game.status === 'aborted';
  const isWaiting = game.status === 'waiting';
  const isInProgress = game.status === 'in_progress';
  const disabled = !isInProgress || !isPlayer;

  async function sendMove(path: number[][]) {
    if (!id) return;
    try {
      const g = await api.makeMove(id, path);
      applyGame(g);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }

  async function action(fn: () => Promise<Game>) {
    try {
      const g = await fn();
      applyGame(g);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }

  function copyLink() {
    navigator.clipboard.writeText(window.location.href).then(() => {
      setLinkCopied(true);
      setTimeout(() => setLinkCopied(false), 2000);
    });
  }

  const isVsAi = game.ai_difficulty !== null;
  const drawOfferFromOpponent =
    !isVsAi &&
    game.draw_offered_by !== null &&
    game.draw_offered_by !== user?.id &&
    isInProgress;
  const drawOfferFromMe =
    !isVsAi && game.draw_offered_by === user?.id && isInProgress;

  const turnLabel =
    game.turn === 'w'
      ? `White${myColor === 'w' ? ' — your turn' : ''}`
      : `Black${myColor === 'b' ? ' — your turn' : ''}`;

  const winnerLabel = !game.winner_id ? 'Draw' :
    game.winner_id === game.white_player.id ? 'White' :
    game.winner_id === game.black_player?.id ? 'Black' : '?';

  return (
    <div className="game-page">
      <header className="game-header">
        <button className="btn-ghost" onClick={() => navigate('/')}>← Lobby</button>
        <h2>Match</h2>
        <span className={connected ? 'badge ok' : 'badge'}>
          {connected ? '● Live' : '○ Connecting…'}
        </span>
      </header>

      <div className="players-row">
        <div className={`player-card ${game.turn === 'b' && isInProgress ? 'active' : ''}`}>
          <span className="avatar black">{initials(game.black_player?.name) || 'B'}</span>
          <div>
            <div className="name">{game.black_player?.name ?? 'Waiting for opponent…'}</div>
            <div className="role">Black{myColor === 'b' ? ' (you)' : ''}</div>
          </div>
          {game.time_initial_ms !== null && (
            <Clock
              remainingMs={game.black_time_ms}
              active={isInProgress && game.turn === 'b'}
              baseTimestamp={receivedAt}
            />
          )}
        </div>

        <div className={`player-card ${game.turn === 'w' && isInProgress ? 'active' : ''}`}>
          <span className="avatar">{initials(game.white_player.name) || 'W'}</span>
          <div>
            <div className="name">{game.white_player.name ?? 'White'}</div>
            <div className="role">White{myColor === 'w' ? ' (you)' : ''}</div>
          </div>
          {game.time_initial_ms !== null && (
            <Clock
              remainingMs={game.white_time_ms}
              active={isInProgress && game.turn === 'w'}
              baseTimestamp={receivedAt}
            />
          )}
        </div>
      </div>

      {isInProgress && (
        <div className="turn-banner">
          <span className="pulse" />
          <span>{turnLabel}</span>
        </div>
      )}

      {isWaiting && (
        <div className="status-card glass">
          <p style={{ margin: '0 0 12px' }}>Waiting for an opponent to join…</p>
          <div className="board-actions">
            <button className="btn-cyan" onClick={copyLink}>
              {linkCopied ? '✓ Copied' : '📋 Copy invite link'}
            </button>
            {!isPlayer && (
              <button className="btn-primary" onClick={() => action(() => api.joinGame(game.id))}>
                Join as black
              </button>
            )}
            {myColor === 'w' && (
              <button className="btn-danger" onClick={() => action(() => api.abortGame(game.id))}>
                Abort game
              </button>
            )}
          </div>
        </div>
      )}

      {isFinished && (
        <div className="status-card glass">
          <h3 style={{ margin: 0 }}>
            {game.status === 'aborted' ? 'Game aborted.' : `Winner: ${winnerLabel}`}
          </h3>
        </div>
      )}

      <div className="board-stage glass">
        <Board
          board={game.board}
          turn={game.turn}
          myColor={myColor}
          disabled={disabled}
          onMove={sendMove}
          pieceSkinCode={user?.active_piece_skin_code ?? null}
          boardSkinCode={user?.active_board_skin_code ?? null}
        />
      </div>

      {isInProgress && isPlayer && (
        <div className="board-actions">
          <button className="btn-danger" onClick={() => action(() => api.resignGame(game.id))}>
            🏳 Resign
          </button>
          {!isVsAi && !drawOfferFromMe && !drawOfferFromOpponent && (
            <button onClick={() => action(() => api.offerDraw(game.id))}>
              🤝 Offer draw
            </button>
          )}
          {drawOfferFromMe && <span className="badge warn">Draw offer sent…</span>}
          {drawOfferFromOpponent && (
            <>
              <span className="badge ok">Opponent offers a draw</span>
              <button className="btn-success" onClick={() => action(() => api.acceptDraw(game.id))}>Accept</button>
              <button onClick={() => action(() => api.declineDraw(game.id))}>Decline</button>
            </>
          )}
        </div>
      )}

      {error && <p className="error">{error}</p>}

      {game.status === 'finished' && game.move_count > 0 && (
        <Analysis gameId={game.id} />
      )}
    </div>
  );
}
