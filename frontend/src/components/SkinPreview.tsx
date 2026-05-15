import type { Skin } from '../types';

/** Renders a visual mock of the skin so users see exactly what they'll get. */
export function SkinPreview({ skin }: { skin: Skin }) {
  if (skin.kind === 'piece_set') {
    return (
      <div className="skin-preview piece-preview">
        <div className={`preview-piece skin-${skin.code} white`} />
        <div className={`preview-piece skin-${skin.code} black king`}>
          <span className="crown">♛</span>
        </div>
      </div>
    );
  }

  if (skin.kind === 'board') {
    return (
      <div className="skin-preview">
        <div className={`board-preview skin-${skin.code}`}>
          {Array.from({ length: 64 }).map((_, i) => {
            const r = Math.floor(i / 8);
            const c = i % 8;
            const dark = (r + c) % 2 === 1;
            return <div key={i} className={dark ? 'dark' : 'light'} />;
          })}
        </div>
      </div>
    );
  }

  // Effect — no rich preview yet, just a placeholder.
  return (
    <div className="skin-preview effect-preview">
      <div className="effect-spark">✨</div>
    </div>
  );
}
