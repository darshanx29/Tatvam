import React from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  Home,
  FileText,
  PlusCircle,
  Layers,
  Users,
  Settings as SettingsIcon,
  ListOrdered,
  LogOut,
  User as UserIcon,
} from 'lucide-react';

export function Sidebar({ currentPath, onNavigate }) {
  const { user, logout, isInstitution, isAdmin } = useAuth();

  const isCurrent = (path) => {
    if (path === '/dashboard' && currentPath === '/dashboard') return true;
    if (path === '/applications' && currentPath.startsWith('/applications') && currentPath !== '/applications/new') return true;
    return currentPath === path;
  };

  return (
    <aside className="app-sidebar no-print">
      {/* Brand logo */}
      <a
        href="#/dashboard"
        onClick={(e) => { e.preventDefault(); onNavigate('/dashboard'); }}
        className="app-sidebar-logo"
      >
        <div style={{
          width: '36px',
          height: '36px',
          borderRadius: '50%',
          backgroundColor: 'rgba(255, 255, 255, 0.08)',
          border: '1.5px solid rgba(255, 255, 255, 0.25)',
          display: 'grid',
          placeItems: 'center',
          color: 'var(--amber-600)',
          marginRight: '12px'
        }}>
          <SettingsIcon size={18} />
        </div>
        <div>
          <div style={{ fontSize: '17px', fontWeight: 800, color: '#ffffff', letterSpacing: '-0.02em', lineHeight: '1.2' }}>
            AICTE <span style={{ color: 'var(--brand-500)' }}>SmartVerify</span>
          </div>
          <div style={{ fontSize: '10px', color: '#a8a29e', fontWeight: 600, letterSpacing: '0.08em' }}>
            VIDYA-NIRIKSHA
          </div>
        </div>
      </a>

      {/* Navigation items */}
      <nav className="app-sidebar-nav">
        <a
          href="#/dashboard"
          onClick={(e) => { e.preventDefault(); onNavigate('/dashboard'); }}
          className={`sidebar-nav-item ${isCurrent('/dashboard') ? 'active' : ''}`}
        >
          <Home size={18} />
          <span>Dashboard</span>
        </a>

        <a
          href="#/dashboard#applications"
          onClick={(e) => {
            e.preventDefault();
            onNavigate('/dashboard');
            setTimeout(() => {
              const el = document.getElementById('applications-section');
              if (el) el.scrollIntoView({ behavior: 'smooth' });
            }, 100);
          }}
          className={`sidebar-nav-item ${isCurrent('/applications') ? 'active' : ''}`}
        >
          <FileText size={18} />
          <span>Applications</span>
        </a>

        {isInstitution && (
          <a
            href="#/applications/new"
            onClick={(e) => { e.preventDefault(); onNavigate('/applications/new'); }}
            className={`sidebar-nav-item ${isCurrent('/applications/new') ? 'active' : ''}`}
          >
            <PlusCircle size={18} />
            <span>New Application</span>
          </a>
        )}

        {isAdmin && (
          <>
            <div style={{
              margin: '14px 12px 6px',
              fontSize: '11px',
              fontWeight: 700,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: '#78716c'
            }}>
              Administration
            </div>

            <a
              href="#/admin/rules"
              onClick={(e) => { e.preventDefault(); onNavigate('/admin/rules'); }}
              className={`sidebar-nav-item ${isCurrent('/admin/rules') ? 'active' : ''}`}
            >
              <Layers size={18} />
              <span>Rules & Checklists</span>
            </a>

            <a
              href="#/admin/users"
              onClick={(e) => { e.preventDefault(); onNavigate('/admin/users'); }}
              className={`sidebar-nav-item ${isCurrent('/admin/users') ? 'active' : ''}`}
            >
              <Users size={18} />
              <span>Users & Access</span>
            </a>

            <a
              href="#/admin/settings"
              onClick={(e) => { e.preventDefault(); onNavigate('/admin/settings'); }}
              className={`sidebar-nav-item ${isCurrent('/admin/settings') ? 'active' : ''}`}
            >
              <SettingsIcon size={18} />
              <span>Settings & Models</span>
            </a>

            <a
              href="#/admin/audit"
              onClick={(e) => { e.preventDefault(); onNavigate('/admin/audit'); }}
              className={`sidebar-nav-item ${isCurrent('/admin/audit') ? 'active' : ''}`}
            >
              <ListOrdered size={18} />
              <span>System Audit</span>
            </a>
          </>
        )}
      </nav>

      {/* User profile & sign out */}
      {user && (
        <div className="app-sidebar-footer">
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            padding: '8px 4px',
            marginBottom: '8px'
          }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              backgroundColor: 'rgba(255, 255, 255, 0.12)',
              display: 'grid',
              placeItems: 'center',
              color: '#f4dcce'
            }}>
              <UserIcon size={18} />
            </div>
            <div style={{ minWidth: 0, flex: 1 }}>
              <div style={{ fontSize: '13px', fontWeight: 700, color: '#ffffff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.name || user.email}
              </div>
              <div style={{ fontSize: '11px', color: '#a8a29e', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user.role_label || user.role}
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            className="sidebar-nav-item"
            style={{ width: '100%', border: 'none', background: 'transparent', cursor: 'pointer', textAlign: 'left' }}
          >
            <LogOut size={16} />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </aside>
  );
}
