import { GoogleLogin } from '@react-oauth/google';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';

const BENEFITS = [
  'Real-time PvP',
  'Play vs AI Coach',
  'Unlock premium skins',
  'Train your strategy',
];

function MiniBoard() {
  // Decorative 8x8 board with starting pieces — purely visual.
  return (
    <div className="login-mini-board board-preview skin-board_ocean">
      {Array.from({ length: 64 }).map((_, i) => {
        const r = Math.floor(i / 8);
        const c = i % 8;
        const dark = (r + c) % 2 === 1;
        return <div key={i} className={dark ? 'dark' : 'light'} />;
      })}
    </div>
  );
}

export function LoginPage() {
  const { signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="login-hero">
      <div className="login-left">
        <h1>Checkers Arena</h1>
        <p className="subtitle">
          Play, train, and climb the leaderboard. Real-time multiplayer, a built-in AI coach,
          and a shop full of premium skins.
        </p>

        <div className="benefits">
          {BENEFITS.map((b) => (
            <div key={b} className="benefit">
              <span className="dot" />
              <span>{b}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="login-card glass-strong">
        <h2>Start playing in seconds</h2>
        <p className="login-sub">Sign in with Google to save your progress and skins.</p>

        <div style={{ marginTop: 8 }}>
          <GoogleLogin
            onSuccess={async (resp) => {
              if (!resp.credential) {
                setError('No credential from Google');
                return;
              }
              try {
                await signInWithGoogle(resp.credential);
                navigate('/');
              } catch (e: any) {
                setError(e.message ?? 'Sign-in failed');
              }
            }}
            onError={() => setError('Google sign-in failed')}
            theme="filled_black"
            size="large"
            shape="pill"
          />
        </div>

        <MiniBoard />

        {error && <p className="error" style={{ width: '100%' }}>{error}</p>}
      </div>
    </div>
  );
}
