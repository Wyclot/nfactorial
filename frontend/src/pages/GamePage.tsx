import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Analysis } from '../components/Analysis';
import { Board } from '../components/Board';
import { Clock } from '../components/Clock';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import { GameSocket } from '../lib/ws';
import type { Game } from '../types';

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
        {error ? <p className="error">{error}</p> : <p>Loading game…</p>}
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

  const turnLabel =
    game.turn === 'w' ? `White${myColor === 'w' ? ' (you)' : ''}` :
    `Black${myColor === 'b' ? ' (you)' : ''}`;

  const winnerLabel = !game.winner_id ? 'Draw' :
    game.winner_id === game.white_player.id ? 'White' :
    game.winner_id === game.black_player?.id ? 'Black' : '?';

  const isVsAi = game.ai_difficulty !== null;
  const drawOfferFromOpponent =
    !isVsAi &&
    game.draw_offered_by !== null &&
    game.draw_offered_by !== user?.id &&
    isInProgress;
  const drawOfferFromMe =
    !isVsAi && game.draw_offered_by === user?.id && isInProgress;

  return (
    <div className="game-page">
      <header>
        <button onClick={() => navigate('/')}>← Lobby</button>
        <h2>Game</h2>
        <span className={connected ? 'badge ok' : 'badge'}>{connected ? '● live' : '○ connecting'}</span>
      </header>

      <div className="players">
        <div className={`player ${game.turn === 'b' ? 'active' : ''}`}>
          <span className="dot black" /> {game.black_player?.name ?? 'Waiting for opponent…'}
          {game.time_initial_ms !== null && (
            <Clock
              remainingMs={game.black_time_ms}
              active={isInProgress && game.turn === 'b'}
              baseTimestamp={receivedAt}
            />
          )}
        </div>
        <div className={`player ${game.turn === 'w' ? 'active' : ''}`}>
          <span className="dot white" /> {game.white_player.name ?? 'White'}
          {game.time_initial_ms !== null && (
            <Clock
              remainingMs={game.white_time_ms}
              active={isInProgress && game.turn === 'w'}
              baseTimestamp={receivedAt}
            />
          )}
        </div>
      </div>

      {isWaiting && (
        <div className="actions">
          <p>Waiting for an opponent to join…</p>
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={copyLink}>{linkCopied ? '✓ Copied' : '📋 Copy invite link'}</button>
            {!isPlayer && (
              <button onClick={() => action(() => api.joinGame(game.id))}>Join as black</button>
            )}
            {myColor === 'w' && (
              <button onClick={() => action(() => api.abortGame(game.id))}>Abort game</button>
            )}
          </div>
        </div>
      )}

      {isFinished && (
        <p className="status">
          {game.status === 'aborted' ? 'Game aborted.' : `Game over. Winner: ${winnerLabel}`}
        </p>
      )}

      {isInProgress && (
        <>
          <p>Turn: {turnLabel}</p>
          {isPlayer && (
            <div className="actions" style={{ display: 'flex', gap: 8, margin: '8px 0' }}>
              <button onClick={() => action(() => api.resignGame(game.id))}>Resign</button>
              {!isVsAi && !drawOfferFromMe && !drawOfferFromOpponent && (
                <button onClick={() => action(() => api.offerDraw(game.id))}>Offer draw</button>
              )}
              {drawOfferFromMe && <span className="badge">Draw offer sent…</span>}
              {drawOfferFromOpponent && (
                <>
                  <span className="badge ok">Opponent offers a draw</span>
                  <button onClick={() => action(() => api.acceptDraw(game.id))}>Accept</button>
                  <button onClick={() => action(() => api.declineDraw(game.id))}>Decline</button>
                </>
              )}
            </div>
          )}
        </>
      )}

      <Board
        board={game.board}
        turn={game.turn}
        myColor={myColor}
        disabled={disabled}
        onMove={sendMove}
        pieceSkinCode={user?.active_piece_skin_code ?? null}
        boardSkinCode={user?.active_board_skin_code ?? null}
      />

      {error && <p className="error">{error}</p>}

      {game.status === 'finished' && game.move_count > 0 && (
        <Analysis gameId={game.id} />
      )}
    </div>
  );
}
