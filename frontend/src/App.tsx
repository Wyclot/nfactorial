import { Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './lib/auth';
import { LoginPage } from './pages/LoginPage';
import { LobbyPage } from './pages/LobbyPage';
import { GamePage } from './pages/GamePage';
import { ShopPage } from './pages/ShopPage';
import { PaymentSuccessPage } from './pages/PaymentSuccessPage';
import { PaymentFailurePage } from './pages/PaymentFailurePage';

function Protected({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth();
  if (loading) return <p>Loading…</p>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<Protected><LobbyPage /></Protected>} />
      <Route path="/game/:id" element={<Protected><GamePage /></Protected>} />
      <Route path="/shop" element={<Protected><ShopPage /></Protected>} />
      <Route path="/payment/success" element={<Protected><PaymentSuccessPage /></Protected>} />
      <Route path="/payment/failure" element={<Protected><PaymentFailurePage /></Protected>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
