import React, { useState, useEffect } from 'react';
import { api } from '../../api';
import { Settings, Save, ShieldCheck, Activity, CheckCircle } from 'lucide-react';

export function AdminSettingsPage({ onNavigate }) {
  const [settings, setSettings] = useState({
    verify_max_attempts: '3',
    qr_allowed_hosts: '',
    retention_days: '365',
  });
  const [evaluation, setEvaluation] = useState(null);
  const [runs, setRuns] = useState([]);
  const [adapter, setAdapter] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMsg, setActionMsg] = useState('');
  const [verifyingAudit, setVerifyingAudit] = useState(false);
  const [auditResult, setAuditResult] = useState(null);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await api.getSettings();
      setSettings(res.settings || {});
      setEvaluation(res.evaluation);
      setRuns(res.runs || []);
      setAdapter(res.adapter || '');
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load system settings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSaveSettings = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await api.saveSettings(settings);
      setActionMsg('System settings successfully updated.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleVerifyAuditChain = async () => {
    setVerifyingAudit(true);
    setAuditResult(null);
    try {
      const res = await api.verifyAuditChain();
      setAuditResult(res);
    } catch (err) {
      setAuditResult({ ok: false, message: err.message || 'Audit verification failed' });
    } finally {
      setVerifyingAudit(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <span className="eyebrow">System Configuration</span>
        <h1 className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '4px' }}>
          Integrations, Settings & Model Monitoring
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>
          Configure verification adapters, QR domain security allow-lists, data retention lifecycles, and monitor OCR benchmark precision.
        </p>
      </div>

      {actionMsg && (
        <div style={{
          padding: '10px 16px',
          backgroundColor: 'var(--green-50)',
          border: '1px solid var(--green-border)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--green-700)',
          fontSize: '13.5px',
          fontWeight: 600,
        }}>
          {actionMsg}
        </div>
      )}

      {error && (
        <div style={{
          padding: '10px 16px',
          backgroundColor: 'var(--red-50)',
          border: '1px solid var(--red-border)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--red-700)',
          fontSize: '13.5px',
          fontWeight: 600,
        }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
        {/* Left: Configuration Form */}
        <section className="card" style={{ padding: '26px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '6px' }}>
            System Parameters
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '18px' }}>
            Active verification adapter: <b>{adapter}</b>. Outbound requests are locked behind SSRF protection.
          </p>

          <form onSubmit={handleSaveSettings} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label className="form-label">Max Source-Verification Attempts</label>
              <input
                type="number"
                value={settings.verify_max_attempts || '3'}
                onChange={(e) => setSettings({ ...settings, verify_max_attempts: e.target.value })}
                className="form-input"
              />
            </div>

            <div>
              <label className="form-label">Authorized QR / Verification Hosts (Comma-separated)</label>
              <input
                value={settings.qr_allowed_hosts || ''}
                onChange={(e) => setSettings({ ...settings, qr_allowed_hosts: e.target.value })}
                placeholder="verify.example.gov.in, aicte-india.org"
                className="form-input"
              />
            </div>

            <div>
              <label className="form-label">Retention for Closed Applications (Days)</label>
              <input
                type="number"
                value={settings.retention_days || '365'}
                onChange={(e) => setSettings({ ...settings, retention_days: e.target.value })}
                className="form-input"
              />
              <span style={{ fontSize: '11px', color: 'var(--ink-muted)', marginTop: '4px', display: 'block' }}>
                Applied during automated cryptographic purge cycles.
              </span>
            </div>

            <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start', marginTop: '6px' }}>
              <Save size={15} /> Save Settings
            </button>
          </form>

          {/* Audit Chain Verification Card */}
          <div style={{ marginTop: '28px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)' }}>
            <h3 className="font-editorial" style={{ fontSize: '1.15rem', fontWeight: 700, marginBottom: '6px' }}>
              Cryptographic Audit Log Integrity
            </h3>
            <p style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '14px' }}>
              Verify SHA-256 hash chaining across all logged institutional and administrative events.
            </p>
            <button
              type="button"
              onClick={handleVerifyAuditChain}
              disabled={verifyingAudit}
              className="btn btn-outline btn-sm"
            >
              <ShieldCheck size={14} /> {verifyingAudit ? 'Verifying Integrity...' : 'Verify Cryptographic Audit Log'}
            </button>
            {auditResult && (
              <div style={{
                marginTop: '12px',
                padding: '10px 14px',
                borderRadius: 'var(--radius-md)',
                fontSize: '12px',
                backgroundColor: auditResult.ok ? 'var(--green-50)' : 'var(--red-50)',
                color: auditResult.ok ? 'var(--green-700)' : 'var(--red-700)',
                border: `1px solid ${auditResult.ok ? 'var(--green-border)' : 'var(--red-border)'}`,
              }}>
                <b>{auditResult.ok ? 'Chain Valid: ' : 'Integrity Issue: '}</b> {auditResult.message}
              </div>
            )}
          </div>
        </section>

        {/* Right: Model Monitoring & Processing Runs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <section className="card" style={{ padding: '26px' }}>
            <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '10px' }}>
              Model Performance Telemetry
            </h2>
            {evaluation ? (
              <div>
                <p style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '12px' }}>
                  Measured on synthetic verification suite ({evaluation.n_applications} applications).
                </p>
                <pre style={{
                  padding: '14px',
                  backgroundColor: '#f7f4ee',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '11.5px',
                  fontFamily: 'var(--font-mono)',
                  maxHeight: '180px',
                  overflowY: 'auto',
                }}>
                  {JSON.stringify(evaluation, null, 2)}
                </pre>
              </div>
            ) : (
              <p style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>No evaluation report found.</p>
            )}
          </section>

          <section className="card" style={{ padding: '26px' }}>
            <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '12px' }}>
              Recent Engine Processing Runs
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13px' }}>
              {runs.length > 0 ? (
                runs.map((r, idx) => (
                  <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#faf8f5', borderRadius: '6px' }}>
                    <span><b>{r.app_id}</b> · {r.status}</span>
                    <span style={{ color: 'var(--ink-muted)', fontSize: '12px' }}>{r.duration_s != null ? `${r.duration_s}s` : '—'} · {r.started}</span>
                  </div>
                ))
              ) : (
                <p style={{ color: 'var(--ink-muted)' }}>No recent runs recorded.</p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
