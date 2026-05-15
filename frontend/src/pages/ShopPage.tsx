import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { SkinPreview } from '../components/SkinPreview';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { Skin, SkinKind } from '../types';

const KIND_LABEL: Record<SkinKind, string> = {
  piece_set: 'Pieces',
  board: 'Boards',
  effect: 'Effects',
};

const KIND_ORDER: SkinKind[] = ['piece_set', 'board', 'effect'];

export function ShopPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [skins, setSkins] = useState<Skin[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flashMsg, setFlashMsg] = useState<string | null>(null);

  async function refresh() {
    setError(null);
    try {
      const list = await api.listSkins();
      console.log('[shop] /skins →', list.map(s => `${s.code}: owned=${s.owned} equipped=${s.equipped}`));
      setSkins(list);
    } catch (e: any) {
      console.error('[shop] /skins failed', e);
      setError(e.message ?? 'Failed to load shop');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // Re-fetch on tab focus / visibility change (handles return-from-Halyk via tab switch
    // and ensures ownership state is always server-authoritative on page wake-up).
    const onFocus = () => refresh();
    const onVis = () => {
      if (document.visibilityState === 'visible') refresh();
    };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVis);
    };
  }, []);

  async function buy(skin: Skin) {
    console.log('[shop] buy clicked for', skin.code, skin.id);
    setPendingId(skin.id);
    setError(null);
    setFlashMsg(null);
    try {
      const resp = await api.buySkin(skin.id);
      console.log('[shop] /payments/skin response:', resp);
      if (resp.invoice_url) {
        console.log('[shop] redirecting to Halyk:', resp.invoice_url);
        window.location.href = resp.invoice_url;
        return;
      }
      setFlashMsg(`✓ Got "${skin.name}" — try equipping it.`);
      await refresh();
    } catch (e: any) {
      console.error('[shop] buy failed', e);
      if (e instanceof ApiError && e.status === 409) {
        setFlashMsg('You already own this item — refreshing.');
        await refresh();
      } else {
        setError(e.message ?? 'Purchase failed');
      }
    } finally {
      setPendingId(null);
    }
  }

  async function equip(skin: Skin) {
    setPendingId(skin.id);
    setError(null);
    try {
      await api.equipSkin(skin.id);
      await Promise.all([refresh(), refreshUser()]);
      setFlashMsg(`⭐ Equipped "${skin.name}"`);
    } catch (e: any) {
      setError(e.message ?? 'Equip failed');
    } finally {
      setPendingId(null);
    }
  }

  async function unequip(kind: SkinKind) {
    setError(null);
    try {
      await api.unequipKind(kind);
      await Promise.all([refresh(), refreshUser()]);
      setFlashMsg('Reverted to default look.');
    } catch (e: any) {
      setError(e.message ?? 'Unequip failed');
    }
  }

  const byKind = useMemo(() => {
    const groups: Record<SkinKind, Skin[]> = { piece_set: [], board: [], effect: [] };
    for (const s of skins) groups[s.kind].push(s);
    return groups;
  }, [skins]);

  if (loading) return <p>Loading shop…</p>;

  return (
    <div className="shop">
      <header className="lobby-header">
        <h1>🛍️ Skin Shop</h1>
        <button onClick={() => navigate('/')}>← Lobby</button>
      </header>

      {flashMsg && <p className="flash">{flashMsg}</p>}
      {error && <p className="error">{error}</p>}

      {KIND_ORDER.map((kind) => {
        const items = byKind[kind];
        if (!items || items.length === 0) return null;
        return (
          <section key={kind} className="shop-section">
            <h2>{KIND_LABEL[kind]}</h2>
            <div className="skin-grid">
              {items.map((skin) => (
                <div
                  key={skin.id}
                  className={`skin-card ${skin.owned ? 'owned' : ''} ${skin.equipped ? 'equipped' : ''}`}
                >
                  <SkinPreview skin={skin} />
                  <h3>{skin.name}</h3>
                  {skin.description && <p className="skin-desc">{skin.description}</p>}
                  <div className="skin-bottom">
                    <span className="skin-price">{skin.price_kzt.toLocaleString()} ₸</span>
                    {skin.equipped ? (
                      <div className="card-actions">
                        <span className="badge ok">⭐ Active</span>
                        <button onClick={() => unequip(skin.kind)}>Unequip</button>
                      </div>
                    ) : skin.owned ? (
                      <div className="card-actions">
                        <span className="badge">✓ Owned</span>
                        <button
                          onClick={() => equip(skin)}
                          disabled={pendingId !== null}
                        >
                          {pendingId === skin.id ? '…' : 'Equip'}
                        </button>
                      </div>
                    ) : (
                      <button onClick={() => buy(skin)} disabled={pendingId !== null}>
                        {pendingId === skin.id ? 'Processing…' : 'Buy'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
