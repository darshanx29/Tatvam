import React from 'react';
import { useAuth } from '../../context/AuthContext';
import { Settings, Shield, User, ArrowRight, LayoutDashboard } from 'lucide-react';

export function Navbar({ onNavigate }) {
  const { user } = useAuth();

  return (
    <header style={{
      position: 'sticky',
      top: 0,
      zIndex: 40,
      backgroundColor: 'rgba(253, 252, 250, 0.92)',
      backdropFilter: 'blur(12px)',
      borderBottom: '1px solid var(--border-main)',
    }}>
      <div style={{
        maxWidth: '1400px',
        margin: '0 auto',
        padding: '0 24px',
        height: '74px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        {/* Logo */}
        <a
          href="#/"
          onClick={(e) => { e.preventDefault(); onNavigate('/'); }}
          style={{ display: 'flex', alignItems: 'center', gap: '12px', textDecoration: 'none' }}
        >
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            backgroundColor: '#fbf6ee',
            border: '2px solid var(--ink)',
            display: 'grid',
            placeItems: 'center',
            color: 'var(--brand-600)',
          }}>
            <Settings size={20} />
          </div>
          <div>
            <div style={{ fontSize: '20px', letterSpacing: '-0.02em', lineHeight: '1.2' }}>
              <span style={{ fontWeight: 800, color: 'var(--ink)' }}>AICTE</span>{' '}
              <span style={{ fontWeight: 700, color: 'var(--brand-600)' }}>SmartVerify</span>
            </div>
            <div style={{ fontSize: '11px', color: 'var(--ink-muted)', fontWeight: 600, letterSpacing: '0.04em' }}>
              VIDYA-NIRIKSHA
            </div>
          </div>
        </a>

        {/* Public nav links */}
        <nav style={{ display: 'flex', alignItems: 'center', gap: '28px', fontSize: '14.5px', fontWeight: 600 }}>
          <a
            href="#capabilities"
            onClick={(e) => {
              e.preventDefault();
              onNavigate('/');
              setTimeout(() => {
                const el = document.getElementById('capabilities');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }, 100);
            }}
            style={{ color: 'var(--ink-secondary)', textDecoration: 'none' }}
          >
            Capabilities
          </a>
          <a
            href="#how"
            onClick={(e) => {
              e.preventDefault();
              onNavigate('/');
              setTimeout(() => {
                const el = document.getElementById('how');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }, 100);
            }}
            style={{ color: 'var(--ink-secondary)', textDecoration: 'none' }}
          >
            Workflow
          </a>
          <a
            href="#safeguards"
            onClick={(e) => {
              e.preventDefault();
              onNavigate('/');
              setTimeout(() => {
                const el = document.getElementById('safeguards');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }, 100);
            }}
            style={{ color: 'var(--ink-secondary)', textDecoration: 'none' }}
          >
            Safeguards
          </a>
          <a
            href="#faq"
            onClick={(e) => {
              e.preventDefault();
              onNavigate('/');
              setTimeout(() => {
                const el = document.getElementById('faq');
                if (el) el.scrollIntoView({ behavior: 'smooth' });
              }, 100);
            }}
            style={{ color: 'var(--ink-secondary)', textDecoration: 'none' }}
          >
            FAQ
          </a>
        </nav>

        {/* Auth CTA */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {user ? (
            <button
              onClick={() => onNavigate('/dashboard')}
              className="btn btn-primary"
            >
              <LayoutDashboard size={16} /> Open Dashboard
            </button>
          ) : (
            <button
              onClick={() => onNavigate('/login')}
              className="btn btn-primary"
            >
              Sign In <ArrowRight size={16} />
            </button>
          )}
        </div>
      </div>
    </header>
  );
}
