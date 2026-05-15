import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { Payment } from '../types';

const AUTO_REDIRECT_SECONDS = 2;

export function PaymentSuccessPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [params] = useSearchParams();
  const paymentId = params.get('payment_id');
  const [payment, setPayment] = useState<Payment | null>(null);
  const [exhausted, setExhausted] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [redirectIn, setRedirectIn] = useState<number | null>(null);

  // Poll backend for status while pending.
  useEffect(() => {
    if (!paymentId) {
      setError('No payment_id in URL.');
      return;
    }
    let cancelled = false;
    let attempts = 0;

    const tick = async () => {
      try {
        const p = await api.getPayment(paymentId);
        if (cancelled) return;
        setPayment(p);
        if (p.status === 'charged') {
          await refreshUser();
          return;
        }
        if (p.status === 'failed' || p.status === 'refunded' || p.status === 'cancelled') {
          return;
        }
        attempts++;
        if (attempts < 15) {
          setTimeout(tick, 2000);
        } else {
          setExhausted(true);
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message ?? 'Failed to check payment');
      }
    };

    tick();
    return () => {
      cancelled = true;
    };
  }, [paymentId, refreshUser]);

  // Auto-redirect to shop on success.
  useEffect(() => {
    if (payment?.status !== 'charged') return;
    setRedirectIn(AUTO_REDIRECT_SECONDS);
    const interval = window.setInterval(() => {
      setRedirectIn((n) => (n === null ? null : n - 1));
    }, 1000);
    const timeout = window.setTimeout(() => {
      navigate('/shop', { replace: true });
    }, AUTO_REDIRECT_SECONDS * 1000);
    return () => {
      clearInterval(interval);
      clearTimeout(timeout);
    };
  }, [payment?.status, navigate]);

  if (error) {
    return (
      <div className="payment-result">
        <h1>Payment</h1>
        <p className="error">{error}</p>
        <button onClick={() => navigate('/shop')}>Back to shop</button>
      </div>
    );
  }

  if (!payment) {
    return (
      <div className="payment-result">
        <h1>⏳ Checking your payment…</h1>
        <p>This usually takes a couple of seconds.</p>
      </div>
    );
  }

  if (payment.status === 'charged') {
    return (
      <div className="payment-result success">
        <h1>✓ Payment successful</h1>
        <p>Your skin has been unlocked. Equip it from the shop.</p>
        <p className="redirect-hint">
          Returning to shop in {redirectIn ?? AUTO_REDIRECT_SECONDS}s…
        </p>
        <div className="actions">
          <button onClick={() => navigate('/shop', { replace: true })}>Open shop now</button>
        </div>
      </div>
    );
  }

  if (payment.status === 'pending') {
    return (
      <div className="payment-result">
        <h1>⏳ Confirming payment…</h1>
        {exhausted ? (
          <>
            <p>Halyk hasn't confirmed yet. The reconcile job will pick it up — check the shop in a minute.</p>
            <button onClick={() => navigate('/shop')}>Back to shop</button>
          </>
        ) : (
          <p>Talking to Halyk…</p>
        )}
      </div>
    );
  }

  return (
    <div className="payment-result failure">
      <h1>✗ Payment was not completed</h1>
      <p>{payment.refunded_at ? 'Payment was refunded.' : 'Payment failed or was cancelled.'}</p>
      <button onClick={() => navigate('/shop')}>Try again</button>
    </div>
  );
}
