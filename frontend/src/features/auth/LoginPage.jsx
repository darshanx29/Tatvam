import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Settings, Check, ArrowLeft, AlertCircle } from 'lucide-react';

export function LoginPage({ onNavigate }) {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      onNavigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Invalid email or password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', minHeight: '100vh', backgroundColor: 'var(--bg-canvas)' }}>
      {/* Left Column: Brand presentation */}
      <div style={{
        backgroundColor: 'var(--brand-900)',
        color: '#ffffff',
        padding: '60px 48px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        position: 'relative',
        overflow: 'hidden',
      }}>
        <div style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.35,
          background: 'radial-gradient(60% 50% at 85% 5%, #d97736 0%, transparent 60%)',
          pointerEvents: 'none',
        }} />

        <div style={{ position: 'relative', zIndex: 1, maxWidth: '480px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '36px' }}>
            <div style={{
              width: '42px',
              height: '42px',
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              border: '2px solid rgba(255, 255, 255, 0.3)',
              display: 'grid',
              placeItems: 'center',
              color: 'var(--brand-400)',
            }}>
              <Settings size={22} />
            </div>
            <div>
              <div style={{ fontSize: '22px', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
                AICTE <span style={{ color: 'var(--amber-400)' }}>SmartVerify</span>
              </div>
              <div style={{ fontSize: '11px', color: '#d6cebf', fontWeight: 600, letterSpacing: '0.08em' }}>
                VIDYA-NIRIKSHA
              </div>
            </div>
          </div>

          <h1 className="font-editorial" style={{ fontSize: '2.8rem', lineHeight: '1.15', fontWeight: 800, marginBottom: '20px', color: '#ffffff' }}>
            Verify earlier.<br />Review with evidence.
          </h1>
          <p style={{ color: '#d6cebf', fontSize: '16px', lineHeight: '1.65', marginBottom: '32px' }}>
            Sign in to validate applications, examine extracted document fields, review regulatory anomalies, and maintain an immutable decision audit trail.
          </p>

          <ul style={{ listStyle: 'none', padding: 0, margin: '0 0 40px 0', display: 'flex', flexDirection: 'column', gap: '14px', fontSize: '14px', color: '#ece5db' }}>
            {[
              'Multimodal OCR with page-level confidence',
              'Evidence-linked compliance rules & regulatory clauses',
              'Authoritative source registry verification',
              'Human decision on every flagged discrepancy',
            ].map((item, idx) => (
              <li key={idx} style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  backgroundColor: 'rgba(255, 255, 255, 0.12)',
                  display: 'grid',
                  placeItems: 'center',
                  color: 'var(--amber-400)',
                  flexShrink: 0,
                }}>
                  <Check size={14} />
                </span>
                <span>{item}</span>
              </li>
            ))}
          </ul>

          <div style={{ fontSize: '12px', color: '#a8a29e' }}>
            Synthetic demo environment · Not an official AICTE production system
          </div>
        </div>
      </div>

      {/* Right Column: Sign in form */}
      <div className="hero-bg" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '48px 24px' }}>
        <div style={{ width: '100%', maxWidth: '440px' }}>
          <button
            onClick={() => onNavigate('/')}
            className="btn btn-outline"
            style={{ marginBottom: '28px', padding: '6px 12px', fontSize: '13px' }}
          >
            <ArrowLeft size={15} /> Back to Home
          </button>

          <h2 className="font-editorial" style={{ fontSize: '2.2rem', fontWeight: 800, marginBottom: '8px' }}>
            Sign in
          </h2>
          <p style={{ fontSize: '14px', color: 'var(--ink-muted)', marginBottom: '24px' }}>
            Access with your institutional account or officer credentials.
          </p>

          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              padding: '12px 16px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'var(--red-50)',
              border: '1px solid var(--red-border)',
              color: 'var(--red-700)',
              fontSize: '13.5px',
              fontWeight: 600,
              marginBottom: '20px',
            }}>
              <AlertCircle size={18} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div>
              <label className="form-label" htmlFor="login-email">Email address</label>
              <input
                id="login-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="officer@demo.com"
                className="form-input"
              />
            </div>

            <div>
              <label className="form-label" htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="form-input"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn btn-primary"
              style={{ width: '100%', padding: '12px', fontSize: '15px', marginTop: '6px' }}
            >
              {loading ? 'Authenticating…' : 'Sign in to Platform'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
