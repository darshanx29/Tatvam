import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api';
import { StatusBadge } from '../../components/ui/StatusBadge';
import {
  FileText,
  Clock,
  User,
  Flag,
  AlertTriangle,
  BarChart2,
  Shield,
  PlusCircle,
  Search,
  Filter,
  CheckCircle,
  Bell,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';

export function DashboardPage({ onNavigate }) {
  const { user, isInstitution } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [page, setPage] = useState(1);

  const fetchDashboard = async () => {
    setLoading(true);
    try {
      const res = await api.getDashboard({ q: search, status: statusFilter, page });
      setData(res);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, [search, statusFilter, page]);

  const handleMarkNotificationsRead = async () => {
    try {
      await api.markNotificationsRead();
      fetchDashboard();
    } catch (err) {
      console.error(err);
    }
  };

  const kpi = data?.kpi || {};
  const ev = data?.evaluation_report;
  const alerts = data?.alerts || [];
  const high = data?.high || [];
  const notes = data?.notes || [];
  const apps = data?.apps || [];
  const statuses = data?.statuses || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      {/* Top Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: '16px' }}>
        <div>
          <span className="eyebrow">{user?.role_label || 'Dashboard'}</span>
          <h1 className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '4px' }}>
            System Overview
          </h1>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={fetchDashboard}
            className="btn btn-outline btn-sm"
            style={{ padding: '8px 14px' }}
          >
            <RefreshCw size={15} /> Refresh
          </button>
          {isInstitution && (
            <button
              onClick={() => onNavigate('/applications/new')}
              className="btn btn-primary"
            >
              <PlusCircle size={16} /> New Application
            </button>
          )}
        </div>
      </div>

      {/* Notifications from officers for Institution */}
      {notes.length > 0 && (
        <section className="card" style={{ padding: '20px', borderColor: 'var(--sky-border)', backgroundColor: 'var(--sky-50)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--sky-700)', fontWeight: 700, fontSize: '15px' }}>
              <Bell size={18} /> Requests from Regulatory Officers
            </div>
            <button
              onClick={handleMarkNotificationsRead}
              className="btn btn-outline btn-sm"
              style={{ fontSize: '12px', background: '#ffffff' }}
            >
              Mark all as read
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {notes.map((n) => (
              <div
                key={n.id}
                style={{
                  padding: '10px 14px',
                  backgroundColor: '#ffffff',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
              >
                <div>
                  <a
                    href={`#/applications/${n.app_id}`}
                    onClick={(e) => { e.preventDefault(); onNavigate(`/applications/${n.app_id}`); }}
                    style={{ fontWeight: 700, color: 'var(--brand-600)', textDecoration: 'none', marginRight: '8px' }}
                  >
                    {n.app_id}
                  </a>
                  <span style={{ fontSize: '13.5px', color: 'var(--ink)' }}>{n.message}</span>
                </div>
                <span style={{ fontSize: '11.5px', color: 'var(--ink-muted)' }}>{n.created_at}</span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 8 Primary KPI Metric Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(135px, 1fr))', gap: '14px' }}>
        {[
          { label: 'Applications', val: kpi.total ?? 0, icon: FileText, color: 'var(--brand-600)' },
          { label: 'Awaiting Validation', val: kpi.awaiting ?? 0, icon: Clock, color: 'var(--amber-600)' },
          { label: 'In Officer Review', val: kpi.review ?? 0, icon: User, color: 'var(--brand-600)' },
          { label: 'Open Findings', val: kpi.open ?? 0, icon: Flag, color: 'var(--red-600)' },
          { label: 'Missing-Doc Cases', val: kpi.missing ?? 0, icon: AlertTriangle, color: 'var(--red-600)' },
          { label: '% with Missing Docs', val: `${kpi.missing_pct ?? 0}%`, icon: BarChart2, color: 'var(--amber-600)' },
          { label: 'Pending Verification', val: kpi.pending_ver ?? 0, icon: Clock, color: 'var(--sky-600)' },
          { label: 'Escalated', val: kpi.escalated ?? 0, icon: Shield, color: 'var(--red-600)' },
        ].map((item, idx) => (
          <div key={idx} className="card card-lift" style={{ padding: '16px' }}>
            <div style={{
              width: '34px',
              height: '34px',
              borderRadius: '50%',
              backgroundColor: 'var(--brand-50)',
              color: item.color,
              display: 'grid',
              placeItems: 'center',
              marginBottom: '10px'
            }}>
              <item.icon size={16} />
            </div>
            <div className="font-editorial" style={{ fontSize: '1.9rem', fontWeight: 800, color: 'var(--ink)', lineHeight: '1.1' }}>
              {item.val}
            </div>
            <div style={{ fontSize: '11.5px', color: 'var(--ink-muted)', marginTop: '4px', fontWeight: 500 }}>
              {item.label}
            </div>
          </div>
        ))}
      </div>

      {/* Performance & Charts Row */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '20px' }}>
        {/* Processing Stats */}
        <section className="card" style={{ padding: '22px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '14px' }}>
            Processing & Verification SLA
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13.5px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--ink-muted)' }}>Median Processing Time</span>
              <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{kpi.p50 != null ? `${kpi.p50} s` : '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--ink-muted)' }}>p95 Processing Time</span>
              <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{kpi.p95 != null ? `${kpi.p95} s` : '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--ink-muted)' }}>Usable Verification Responses</span>
              <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{kpi.usable_pct != null ? `${kpi.usable_pct}%` : '—'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: 'var(--ink-muted)' }}>Officer Review Time / Application</span>
              <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{kpi.review_min != null ? `${kpi.review_min} min` : '—'}</span>
            </div>
          </div>
        </section>

        {/* Applications by Status */}
        <section className="card" style={{ padding: '22px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '14px' }}>
            Applications by Status
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {kpi.by_status && Object.keys(kpi.by_status).length > 0 ? (
              Object.entries(kpi.by_status).map(([st, count]) => {
                const pct = kpi.total > 0 ? Math.round((count / kpi.total) * 100) : 0;
                return (
                  <div key={st}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                      <span style={{ fontWeight: 600 }}>{st}</span>
                      <span style={{ fontWeight: 700 }}>{count} ({pct}%)</span>
                    </div>
                    <div className="progress-bar-bg">
                      <div className="progress-bar-fill" style={{ width: `${pct}%` }}></div>
                    </div>
                  </div>
                );
              })
            ) : (
              <p style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>No application data available.</p>
            )}
          </div>
        </section>

        {/* Open Findings by Severity */}
        <section className="card" style={{ padding: '22px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '14px' }}>
            Open Findings by Severity
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[
              { sev: 'high', label: 'High Severity', color: 'var(--red-600)' },
              { sev: 'medium', label: 'Medium Severity', color: 'var(--amber-600)' },
              { sev: 'low', label: 'Low Severity', color: 'var(--sky-600)' },
            ].map(({ sev, label, color }) => {
              const count = (kpi.by_sev && kpi.by_sev[sev]) || 0;
              const openTotal = kpi.open || 1;
              const pct = Math.round((count / openTotal) * 100);
              return (
                <div key={sev}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '12px', marginBottom: '4px' }}>
                    <span style={{ fontWeight: 600 }}>{label}</span>
                    <span style={{ fontWeight: 700 }}>{count}</span>
                  </div>
                  <div className="progress-bar-bg">
                    <div style={{ height: '100%', backgroundColor: color, borderRadius: 'var(--radius-full)', width: `${pct}%` }}></div>
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      {/* Model & Rule Evaluation Section (Officer / Admin) */}
      {!isInstitution && ev && (
        <section className="card" style={{ padding: '24px', backgroundColor: '#fcfbfa' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '4px' }}>
            Model & Rule Evaluation Benchmark (Labelled Synthetic Set)
          </h2>
          <p style={{ fontSize: '12px', color: 'var(--ink-muted)', marginBottom: '16px' }}>
            Generated {ev.generated_at} on {ev.n_applications} applications · {ev.n_documents} documents. Synthetic data only.
          </p>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '14px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>OCR Exact Match</div>
              <div className="font-editorial" style={{ fontSize: '1.6rem', fontWeight: 800 }}>{ev.ocr?.exact_match ?? '—'}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>OCR Field Precision</div>
              <div className="font-editorial" style={{ fontSize: '1.6rem', fontWeight: 800 }}>{ev.ocr?.precision ?? '—'}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>OCR Field Recall</div>
              <div className="font-editorial" style={{ fontSize: '1.6rem', fontWeight: 800 }}>{ev.ocr?.recall ?? '—'}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>Finding Precision</div>
              <div className="font-editorial" style={{ fontSize: '1.6rem', fontWeight: 800 }}>{ev.findings?.precision ?? '—'}</div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>Finding Recall</div>
              <div className="font-editorial" style={{ fontSize: '1.6rem', fontWeight: 800 }}>{ev.findings?.recall ?? '—'}</div>
            </div>
          </div>
          <div style={{ marginTop: '12px', fontSize: '12px', color: 'var(--ink-muted)' }}>
            False-positive rate: <b>{ev.findings?.false_positive_rate ?? '0.00'}</b> (flagged-but-wrong / total flags)
          </div>
        </section>
      )}

      {/* Main Bottom Grid: Applications Table + Recent Activity */}
      <div id="applications-section" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {/* Applications List */}
        <div style={{ flex: '2', minWidth: '0' }}>
          <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
            <div style={{
              padding: '18px 22px',
              borderBottom: '1px solid var(--border-main)',
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'space-between',
              alignItems: 'center',
              gap: '14px',
            }}>
              <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700 }}>
                Applications
              </h2>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ position: 'relative' }}>
                  <input
                    type="text"
                    value={search}
                    onChange={(e) => { setSearch(e.target.value); setPage(1); }}
                    placeholder="Search ID / Institution…"
                    className="form-input"
                    style={{ paddingLeft: '32px', width: '200px', fontSize: '13px' }}
                  />
                  <Search size={15} style={{ position: 'absolute', left: '10px', top: '10px', color: 'var(--ink-faint)' }} />
                </div>
                <select
                  value={statusFilter}
                  onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
                  className="form-select"
                  style={{ width: '160px', fontSize: '13px' }}
                >
                  <option value="">All Statuses</option>
                  {statuses.map((s) => (
                    <option key={s} value={s}>{s}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Application</th>
                    <th>Institution</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Open Flags</th>
                  </tr>
                </thead>
                <tbody>
                  {apps.length > 0 ? (
                    apps.map((a) => (
                      <tr
                        key={a.id}
                        style={{ cursor: 'pointer' }}
                        onClick={() => onNavigate(`/applications/${a.id}`)}
                      >
                        <td style={{ fontWeight: 700 }}>
                          <span style={{ color: 'var(--brand-600)' }}>{a.id}</span>
                        </td>
                        <td>{a.institution_id}</td>
                        <td>{a.category}</td>
                        <td>
                          <StatusBadge type="app" value={a.status} />
                        </td>
                        <td style={{ textAlign: 'right', fontWeight: 700, color: a.open_count > 0 ? 'var(--red-700)' : 'var(--ink-muted)' }}>
                          {a.open_count}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '36px', color: 'var(--ink-muted)' }}>
                        No applications matched your criteria.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {data?.pages > 1 && (
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                padding: '14px 22px',
                borderTop: '1px solid var(--border-main)',
                fontSize: '13px',
              }}>
                <span style={{ color: 'var(--ink-muted)' }}>Page {data.page} of {data.pages}</span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    disabled={data.page <= 1}
                    onClick={() => setPage(p => Math.max(p - 1, 1))}
                    className="btn btn-outline btn-sm"
                  >
                    Previous
                  </button>
                  <button
                    disabled={data.page >= data.pages}
                    onClick={() => setPage(p => p + 1)}
                    className="btn btn-outline btn-sm"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Recent Activity Audit Feed */}
        <div style={{ flex: '1', minWidth: '280px' }}>
          <section className="card" style={{ padding: '22px' }}>
            <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '16px' }}>
              Recent Activity
            </h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {alerts.length > 0 ? (
                alerts.map((al) => (
                  <div key={al.id} style={{ display: 'flex', gap: '12px', alignItems: 'flex-start', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '10px' }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: 'var(--brand-500)', marginTop: '6px', flexShrink: 0 }} />
                    <div style={{ fontSize: '13px' }}>
                      <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{al.app_id}</span> · {al.event?.replace(/_/g, ' ')}
                      <div style={{ fontSize: '11.5px', color: 'var(--ink-muted)' }}>{al.ts} · {al.actor}</div>
                      {al.detail && <div style={{ fontSize: '12px', color: 'var(--ink-secondary)', marginTop: '2px' }}>{al.detail}</div>}
                    </div>
                  </div>
                ))
              ) : (
                <p style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>No recent activity records.</p>
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
