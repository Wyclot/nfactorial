import { useState } from 'react';
import { api } from '../lib/api';
import type { AnalysisItem, Verdict } from '../types';

const VERDICT_LABEL: Record<Verdict, string> = {
  good: '✓ Good',
  inaccuracy: '? Inaccuracy',
  mistake: '?? Mistake',
  blunder: '?? Blunder',
};

const VERDICT_COLOR: Record<Verdict, string> = {
  good: '#6fc36f',
  inaccuracy: '#ffd166',
  mistake: '#ff9f43',
  blunder: '#ff6b6b',
};

function squareLabel([r, c]: number[]): string {
  const files = 'abcdefgh';
  return `${files[c]}${8 - r}`;
}

function pathLabel(path: number[][]): string {
  return path.map(squareLabel).join('→');
}

export function Analysis({ gameId }: { gameId: string }) {
  const [items, setItems] = useState<AnalysisItem[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const data = await api.analyzeGame(gameId);
      setItems(data);
    } catch (e: any) {
      setError(e.message ?? 'Analysis failed');
    } finally {
      setLoading(false);
    }
  }

  if (!items) {
    return (
      <div className="analysis">
        <button onClick={run} disabled={loading}>
          {loading ? 'Analyzing… (may take a few seconds)' : '🧠 Analyze with AI Coach'}
        </button>
        {error && <p className="error">{error}</p>}
      </div>
    );
  }

  const blunders = items.filter((i) => i.verdict === 'blunder').length;
  const mistakes = items.filter((i) => i.verdict === 'mistake').length;

  return (
    <div className="analysis">
      <h3>AI Coach review</h3>
      <p>
        Blunders: <b>{blunders}</b> · Mistakes: <b>{mistakes}</b> · Total moves: <b>{items.length}</b>
      </p>
      <ol className="analysis-list">
        {items.map((it) => (
          <li key={it.move_number} style={{ borderLeftColor: VERDICT_COLOR[it.verdict] }}>
            <div className="analysis-head">
              <span className="move-num">#{it.move_number}</span>
              <span className="move-by">{it.by === 'w' ? '⚪' : '⚫'}</span>
              <span className="verdict" style={{ color: VERDICT_COLOR[it.verdict] }}>
                {VERDICT_LABEL[it.verdict]}
              </span>
              <span className="eval-loss">(−{it.eval_loss.toFixed(2)})</span>
            </div>
            <p className="comment">{it.comment}</p>
            {it.verdict !== 'good' && (
              <p className="best-line">Better: <code>{pathLabel(it.best_path)}</code></p>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}
