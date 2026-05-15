import { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import type { Payment } from '../types';

export function PaymentFailurePage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const paymentId = params.get('payment_id');
  const [payment, setPayment] = useState<Payment | null>(null);

  useEffect(() => {
    if (!paymentId) return;
    api.getPayment(paymentId).then(setPayment).catch(() => {});
  }, [paymentId]);

  return (
    <div className="payment-result failure glass">
      <h1>✗ Payment failed</h1>
      <p>The payment didn't go through. You haven't been charged.</p>
      {payment?.status === 'charged' && (
        <p className="flash">Actually, Halyk reports your payment succeeded — the skin should be unlocked.</p>
      )}
      <div className="actions">
        <button onClick={() => navigate('/shop')}>Back to shop</button>
        <button onClick={() => navigate('/')}>Back to lobby</button>
      </div>
    </div>
  );
}
