import React, { useState, useEffect } from 'react';
import { api } from '../../api';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ArrowLeft, Printer, Download, FileText } from 'lucide-react';

export function ValidationReportPage({ appId, onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchReportData = async () => {
      try {
        const res = await api.getApplication(appId);
        setData(res);
      } catch (err) {
        setError(err.message || 'Failed to load report data');
      } finally {
        setLoading(false);
      }
    };
    fetchReportData();
  }, [appId]);

  if (loading) {
    return <div style={{ padding: '60px', textAlign: 'center', color: 'var(--ink-muted)' }}>Preparing validation report…</div>;
  }

  if (error || !data) {
    return (
      <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
        <h2 className="font-editorial" style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Unable to load report</h2>
        <p style={{ color: 'var(--ink-muted)', marginBottom: '20px' }}>{error}</p>
        <button onClick={() => onNavigate(`/applications/${appId}`)} className="btn btn-primary">Back to Application</button>
      </div>
    );
  }

  const a = data.application;
  const findings = data.findings || [];
  const verifications = data.verifications || [];
  const notes = data.notes || [];
  const recOptions = data.recommendation_options || {};

  return (
    <div style={{ maxWidth: '960px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="no-print">
        <button
          onClick={() => onNavigate(`/applications/${appId}`)}
          className="btn btn-outline btn-sm"
          style={{ marginBottom: '14px' }}
        >
          <ArrowLeft size={14} /> Back to {appId}
        </button>
      </div>

      <div className="card" style={{ padding: '36px', backgroundColor: '#ffffff' }}>
        {/* Report Top Header */}
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px', borderBottom: '1px solid var(--border-main)', paddingBottom: '20px' }}>
          <div>
            <span className="eyebrow">AICTE SmartVerify · Vidya-Niriksha</span>
            <h1 className="font-editorial" style={{ fontSize: '2.2rem', fontWeight: 800, marginTop: '4px' }}>
              Validation Report · {a.id}
            </h1>
            <p style={{ fontSize: '13.5px', color: 'var(--ink-muted)', marginTop: '4px' }}>
              Institution: <b>{a.institution_id}</b> · Category: <b>{a.category}</b> · Status: <b>{a.status}</b> · Synthetic Test Environment
            </p>
          </div>

          <div className="no-print" style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            <a href={`/applications/${a.id}/report.pdf`} className="btn btn-outline btn-sm">
              <Download size={13} /> PDF
            </a>
            <a href={`/applications/${a.id}/report.csv`} className="btn btn-outline btn-sm">
              <Download size={13} /> CSV
            </a>
            <a href={`/applications/${a.id}/report.json`} className="btn btn-outline btn-sm">
              <Download size={13} /> JSON
            </a>
            <button onClick={() => window.print()} className="btn btn-primary btn-sm">
              <Printer size={13} /> Print Report
            </button>
          </div>
        </div>

        {/* Findings Table */}
        <div style={{ marginTop: '28px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '12px' }}>
            Compliance & Anomaly Findings
          </h2>
          <div className="table-container" style={{ border: '1px solid var(--border-main)' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rule</th>
                  <th>Finding / Observed Evidence</th>
                  <th>Recommended Next Step</th>
                  <th>State</th>
                </tr>
              </thead>
              <tbody>
                {findings.length > 0 ? (
                  findings.map((f) => (
                    <tr key={f.id}>
                      <td style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
                        {f.rule_id} <span style={{ fontSize: '11px', color: 'var(--ink-muted)' }}>v{f.rule_version}</span>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600 }}>{f.title}</div>
                        <div style={{ fontSize: '11.5px', color: 'var(--ink-muted)' }}>
                          {f.source} · Observed: {f.observed} · Expected: {f.expected}
                        </div>
                      </td>
                      <td style={{ fontSize: '12.5px' }}>{f.next_step}</td>
                      <td>
                        <StatusBadge type="state" value={f.state} />
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={4} style={{ textAlign: 'center', padding: '24px', color: 'var(--ink-muted)' }}>
                      Preliminary pass: no adverse findings detected. (Not an official regulatory approval).
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Source Verification */}
        <div style={{ marginTop: '28px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '10px' }}>
            Authoritative Source Verification
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '13.5px' }}>
            {verifications.length > 0 ? (
              verifications.map((v, idx) => (
                <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: '#faf8f5', borderRadius: '6px' }}>
                  <span><b>{v.document}</b> — {v.detail} <span style={{ color: 'var(--ink-muted)', fontSize: '12px' }}>({v.source}, {v.timestamp})</span></span>
                  <StatusBadge type="verification" value={v.status} />
                </div>
              ))
            ) : (
              <p style={{ color: 'var(--ink-muted)' }}>No source verifications recorded.</p>
            )}
          </div>
        </div>

        {/* Official Recommendation */}
        <div style={{ marginTop: '28px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '8px' }}>
            Official Recommendation
          </h2>
          <div style={{ fontSize: '14px', color: 'var(--ink)' }}>
            <b>{recOptions[a.recommendation] || a.recommendation || 'Not yet recorded'}</b>
            {a.recommendation_note && <span> — {a.recommendation_note}</span>}
          </div>
        </div>

        {/* Officer Actions Log */}
        <div style={{ marginTop: '28px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700, marginBottom: '10px' }}>
            Officer Actions & Observations
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px' }}>
            {notes.length > 0 ? (
              notes.map((n) => (
                <div key={n.id}>
                  <span style={{ color: 'var(--ink-muted)' }}>{n.ts}</span> · <b>{n.actor}</b> · {n.action?.replace(/_/g, ' ')} — {n.reason}
                </div>
              ))
            ) : (
              <p style={{ color: 'var(--ink-muted)' }}>No officer observations recorded.</p>
            )}
          </div>
        </div>

        {/* Disclaimer */}
        <div style={{ marginTop: '36px', paddingTop: '16px', borderTop: '1px solid var(--border-main)', fontSize: '11.5px', color: 'var(--ink-muted)', lineHeight: '1.6' }}>
          System recommendation: Resolve or review the listed discrepancies. No automatic adverse regulatory action is executed by the system. All AI findings are advisory decision-support outputs.
        </div>
      </div>
    </div>
  );
}
