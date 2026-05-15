import { GoogleLogin } from '@react-oauth/google';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';

export function LoginPage() {
  const { signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="login-page">
      <h1>Checkers</h1>
      <p>Sign in to play.</p>
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
      />
      {error && <p className="error">{error}</p>}
    </div>
  );
}
