import React, { useState, useEffect } from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { Sidebar } from './components/layout/Sidebar';
import { LandingPage } from './features/landing/LandingPage';
import { LoginPage } from './features/auth/LoginPage';
import { DashboardPage } from './features/dashboard/DashboardPage';
import { NewApplicationPage } from './features/applications/NewApplicationPage';
import { ApplicationDetailPage } from './features/applications/ApplicationDetailPage';
import { DocumentViewerPage } from './features/documents/DocumentViewerPage';
import { CompliancePage } from './features/applications/CompliancePage';
import { ValidationReportPage } from './features/applications/ValidationReportPage';
import { AuditPage } from './features/applications/AuditPage';
import { AdminRulesPage } from './features/admin/AdminRulesPage';
import { AdminUsersPage } from './features/admin/AdminUsersPage';
import { AdminSettingsPage } from './features/admin/AdminSettingsPage';

function Router() {
  const { user, loading } = useAuth();
  const [currentHash, setCurrentHash] = useState(window.location.hash || '#/');

  useEffect(() => {
    const handleHashChange = () => {
      setCurrentHash(window.location.hash || '#/');
    };
    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigate = (path) => {
    const hash = path.startsWith('#') ? path : `#${path}`;
    window.location.hash = hash;
    setCurrentHash(hash);
    window.scrollTo(0, 0);
  };

  if (loading) {
    return (
      <div style={{
        height: '100vh',
        display: 'grid',
        placeItems: 'center',
        backgroundColor: 'var(--bg-canvas)',
        color: 'var(--ink-muted)',
        fontSize: '15px',
        fontWeight: 600,
      }}>
        Initializing Vidya-Niriksha SmartVerify…
      </div>
    );
  }

  // Parse path without '#'
  const path = currentHash.replace(/^#/, '').split('?')[0] || '/';

  // Public views
  if (path === '/' || path === '') {
    return <LandingPage onNavigate={navigate} />;
  }

  if (path === '/login') {
    if (user) {
      navigate('/dashboard');
      return null;
    }
    return <LoginPage onNavigate={navigate} />;
  }

  // If user is not authenticated, redirect to login
  if (!user) {
    navigate('/login');
    return null;
  }

  // Render view inside Authenticated App Shell
  const renderView = () => {
    // Exact routes
    if (path === '/dashboard') {
      return <DashboardPage onNavigate={navigate} />;
    }
    if (path === '/applications/new') {
      return <NewApplicationPage onNavigate={navigate} />;
    }
    if (path === '/admin/rules') {
      return <AdminRulesPage onNavigate={navigate} />;
    }
    if (path === '/admin/users') {
      return <AdminUsersPage onNavigate={navigate} />;
    }
    if (path === '/admin/settings') {
      return <AdminSettingsPage onNavigate={navigate} />;
    }
    if (path === '/admin/audit') {
      return <AuditPage appId={null} onNavigate={navigate} />;
    }

    // Parametric routes: /applications/:id/...
    const appMatch = path.match(/^\/applications\/([^\/]+)(?:\/(.*))?$/);
    if (appMatch) {
      const appId = appMatch[1];
      const sub = appMatch[2];
      if (sub === 'compliance') {
        return <CompliancePage appId={appId} onNavigate={navigate} />;
      }
      if (sub === 'report') {
        return <ValidationReportPage appId={appId} onNavigate={navigate} />;
      }
      if (sub === 'audit') {
        return <AuditPage appId={appId} onNavigate={navigate} />;
      }
      return <ApplicationDetailPage appId={appId} onNavigate={navigate} />;
    }

    // Parametric routes: /documents/:id
    const docMatch = path.match(/^\/documents\/(\d+)$/);
    if (docMatch) {
      return <DocumentViewerPage docId={docMatch[1]} onNavigate={navigate} />;
    }

    // Fallback to dashboard
    return <DashboardPage onNavigate={navigate} />;
  };

  return (
    <div className="app-shell">
      <Sidebar currentPath={path} onNavigate={navigate} />
      <div className="app-main">
        <main className="app-body">
          {renderView()}
        </main>
        <footer className="no-print" style={{
          borderTop: '1px solid var(--border-main)',
          backgroundColor: '#fdfcfa',
          color: 'var(--ink-muted)',
          fontSize: '12px',
          textAlign: 'center',
          padding: '16px 20px',
        }}>
          AI findings are preliminary decision-support outputs. Final decisions rest with authorized AICTE officials. Prototype · synthetic data only · not an official AICTE system.
        </footer>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router />
    </AuthProvider>
  );
}
