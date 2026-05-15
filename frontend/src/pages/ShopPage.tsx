import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { SkinPreview } from '../components/SkinPreview';
import { api, ApiError } from '../lib/api';
import { useAuth } from '../lib/auth';
import type { Skin, SkinKind } from '../types';

type Tab = 'all' | 'piece_set' | 'board';

const TAB_LABEL: Record<Tab, string> = {
  all: 'All',
  piece_set: '♟ Pieces',
  board: '🏁 Boards',
};

export function ShopPage() {
  const navigate = useNavigate();
  const { refreshUser } = useAuth();
  const [skins, setSkins] = useState<Skin[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingId, setPendingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [flashMsg, setFlashMsg] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('all');

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
    setPendingId(skin.id);
    setError(null);
    setFlashMsg(null);
    try {
      const resp = await api.buySkin(skin.id);
      if (resp.invoice_url) {
        window.location.href = resp.invoice_url;
        return;
      }
      setFlashMsg(`✓ Unlocked "${skin.name}" — equip it below.`);
      await refresh();
    } catch (e: any) {
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

  const filtered = useMemo(() => {
    if (tab === 'all') return skins;
    return skins.filter((s) => s.kind === tab);
  }, [skins, tab]);

  if (loading) return <p className="muted">Loading shop…</p>;

  return (
    <div className="shop">
      <section className="shop-hero glass">
        <div>
          <h1>🛍️ Skin Shop</h1>
          <p style={{ margin: '6px 0 0' }}>Collect premium pieces and boards. Equip them to use in any match.</p>
        </div>
        <button className="btn-ghost" onClick={() => navigate('/')}>← Lobby</button>
      </section>

      {flashMsg && <p className="flash" style={{ marginBottom: 12 }}>{flashMsg}</p>}
      {error && <p className="error" style={{ marginBottom: 12 }}>{error}</p>}

      <div className="shop-tabs">
        {(Object.keys(TAB_LABEL) as Tab[]).map((t) => (
          <button
            key={t}
            className={`tab ${tab === t ? 'active' : ''}`}
            onClick={() => setTab(t)}
          >
            {TAB_LABEL[t]}
          </button>
        ))}
      </div>

      <div className="skin-grid">
        {filtered.map((skin) => (
          <div
            key={skin.id}
            className={`skin-card ${skin.owned ? 'owned' : ''} ${skin.equipped ? 'equipped' : ''}`}
          >
            <SkinPreview skin={skin} />
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <h3>{skin.name}</h3>
              {skin.equipped && <span className="badge gold">⭐ Active</span>}
              {!skin.equipped && skin.owned && <span className="badge ok">✓ Owned</span>}
            </div>
            {skin.description && <p className="skin-desc">{skin.description}</p>}

            <div className="skin-bottom">
              <span className="price-pill">{skin.price_kzt.toLocaleString()} ₸</span>
              {skin.equipped ? (
                <button onClick={() => unequip(skin.kind)}>Unequip</button>
              ) : skin.owned ? (
                <button
                  className="btn-primary"
                  onClick={() => equip(skin)}
                  disabled={pendingId !== null}
                >
                  {pendingId === skin.id ? '…' : 'Equip'}
                </button>
              ) : (
                <button
                  className="btn-cyan"
                  onClick={() => buy(skin)}
                  disabled={pendingId !== null}
                >
                  {pendingId === skin.id ? 'Processing…' : 'Buy'}
                </button>
              )}
            </div>
          </div>
        ))}

        {filtered.length === 0 && (
          <div className="empty glass" style={{ gridColumn: '1 / -1' }}>
            <div className="big">🕳</div>
            <div>Nothing in this category yet.</div>
          </div>
        )}
      </div>
    </div>
  );
}
