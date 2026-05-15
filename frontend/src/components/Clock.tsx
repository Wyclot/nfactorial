import { useEffect, useState } from 'react';

interface Props {
  remainingMs: number | null;
  active: boolean;
  /** Local-time epoch ms when `remainingMs` was last reported by the server. */
  baseTimestamp: number;
}

function format(ms: number): string {
  if (ms < 0) ms = 0;
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  if (ms < 10000) {
    // Show tenths under 10s for tension.
    const tenths = Math.floor((ms % 1000) / 100);
    return `${m}:${s.toString().padStart(2, '0')}.${tenths}`;
  }
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function Clock({ remainingMs, active, baseTimestamp }: Props) {
  const [, force] = useState(0);

  useEffect(() => {
    if (!active) return;
    const interval = remainingMs !== null && remainingMs < 10000 ? 100 : 500;
    const id = window.setInterval(() => force((n) => n + 1), interval);
    return () => clearInterval(id);
  }, [active, remainingMs]);

  if (remainingMs === null) return null;

  const elapsed = active ? Date.now() - baseTimestamp : 0;
  const display = Math.max(0, remainingMs - elapsed);
  const low = display < 10000;

  return (
    <span className={`clock ${active ? 'active' : ''} ${low ? 'low' : ''}`}>
      {format(display)}
    </span>
  );
}
