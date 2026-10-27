import React, { useState, useEffect } from 'react';
import { api } from '../../api';
import { ArrowLeft, Clock, Shield } from 'lucide-react';

export function AuditPage({ appId = null, onNavigate }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAudit = async () => {
      setLoading(true);
      try {
        const res = appId ? await api.getAudit(appId) : await api.getSystemAudit();
        setEvents(res.items || []);
      } catch (err) {
        setError(err.message || 'Failed to load audit history');
      } finally {
        setLoading(false);
      }
    };
    fetchAudit();
  }, [appId]);

  return (
    <div style={{ maxWidth: '840px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        {appId ? (
          <button
            onClick={() => onNavigate(`/applications/${appId}`)}
            className="btn btn-outline btn-sm"
            style={{ marginBottom: '14px' }}
          >
            <ArrowLeft size={14} /> Back to {appId}
          </button>
        ) : (
          <button
            onClick={() => onNavigate('/dashboard')}
            className="btn btn-outline btn-sm"
            style={{ marginBottom: '14px' }}
          >
            <ArrowLeft size={14} /> Back to Dashboard
          </button>
        )}
        <span className="eyebrow">Immutable Audit Log</span>
        <h1 className="font-editorial" style={{ fontSize: '2.2rem', fontWeight: 800, marginTop: '4px' }}>
          {appId ? `Audit History · ${appId}` : 'System Administration & Security Audit'}
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>
          Chronological record of every event, authentication attempt, document upload, OCR correction, and officer review action.
        </p>
      </div>

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--ink-muted)' }}>Loading audit records…</div>
      ) : error ? (
        <div className="card" style={{ padding: '24px', color: 'var(--red-700)' }}>{error}</div>
      ) : (
        <div className="card" style={{ padding: '32px' }}>
          <div style={{
            borderLeft: '2px solid var(--brand-300)',
            marginLeft: '8px',
            display: 'flex',
            flexDirection: 'column',
            gap: '24px',
          }}>
            {events.length > 0 ? (
              events.map((e, idx) => (
                <div key={idx} style={{ position: 'relative', paddingLeft: '24px' }}>
                  <span style={{
                    position: 'absolute',
                    left: '-7px',
                    top: '4px',
                    width: '12px',
                    height: '12px',
                    borderRadius: '50%',
                    backgroundColor: 'var(--brand-600)',
                    border: '3px solid var(--brand-100)',
                  }} />
                  <div style={{ fontSize: '11.5px', color: 'var(--ink-muted)' }}>
                    {e.ts} · <b>{e.actor}</b>
                  </div>
                  <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--ink)', marginTop: '2px', textTransform: 'capitalize' }}>
                    {e.event?.replace(/_/g, ' ')}
                  </div>
                  {e.detail && (
                    <div style={{ fontSize: '13px', color: 'var(--ink-secondary)', marginTop: '2px' }}>
                      {e.detail}
                    </div>
                  )}
                </div>
              ))
            ) : (
              <div style={{ paddingLeft: '20px', color: 'var(--ink-muted)' }}>No audit events logged.</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
