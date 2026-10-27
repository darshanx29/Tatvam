import React, { useState, useEffect } from 'react';
import { api } from '../../api';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { ArrowLeft, CheckCircle2, AlertTriangle, HelpCircle, FileCheck } from 'lucide-react';

export function CompliancePage({ appId, onNavigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchCompliance = async () => {
      try {
        const res = await api.getCompliance(appId);
        setData(res);
      } catch (err) {
        setError(err.message || 'Failed to load compliance assessment');
      } finally {
        setLoading(false);
      }
    };
    fetchCompliance();
  }, [appId]);

  if (loading) {
    return <div style={{ padding: '60px', textAlign: 'center', color: 'var(--ink-muted)' }}>Loading compliance assessment…</div>;
  }

  if (error || !data) {
    return (
      <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
        <AlertTriangle size={32} style={{ color: 'var(--red-600)', margin: '0 auto 12px' }} />
        <h2 className="font-editorial" style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Unable to load compliance</h2>
        <p style={{ color: 'var(--ink-muted)', marginBottom: '20px' }}>{error}</p>
        <button onClick={() => onNavigate(`/applications/${appId}`)} className="btn btn-primary">Back to Application</button>
      </div>
    );
  }

  const res = data.res || [];
  const summary = data.summary || { compliant: 0, deficient: 0, inconclusive: 0 };
  const refer = data.refer || [];
  const rulesUsed = data.rules_used || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <button
          onClick={() => onNavigate(`/applications/${appId}`)}
          className="btn btn-outline btn-sm"
          style={{ marginBottom: '14px' }}
        >
          <ArrowLeft size={14} /> Back to {appId}
        </button>
        <span className="eyebrow">Regulatory Compliance</span>
        <h1 className="font-editorial" style={{ fontSize: '2.2rem', fontWeight: 800, marginTop: '4px' }}>
          Compliance Assessment · {appId}
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>
          Every executed rule, with the active rule version and linked evidence. Results are advisory: a compliant result signifies that automated checks passed, not that an approval has been granted.
        </p>
      </div>

      {/* Summary KPI Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '16px', maxWidth: '640px' }}>
        <div className="card" style={{ padding: '20px' }}>
          <div className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, color: 'var(--green-700)' }}>
            {summary.compliant}
          </div>
          <span className="badge badge-green" style={{ marginTop: '6px' }}>Compliant Checks</span>
        </div>

        <div className="card" style={{ padding: '20px' }}>
          <div className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, color: 'var(--red-700)' }}>
            {summary.deficient}
          </div>
          <span className="badge badge-red" style={{ marginTop: '6px' }}>Deficient Items</span>
        </div>

        <div className="card" style={{ padding: '20px' }}>
          <div className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, color: 'var(--amber-700)' }}>
            {summary.inconclusive}
          </div>
          <span className="badge badge-amber" style={{ marginTop: '6px' }}>Inconclusive</span>
        </div>
      </div>

      {/* Inconclusive Referral Notice */}
      {refer.length > 0 && (
        <div style={{
          padding: '16px 20px',
          backgroundColor: 'var(--amber-50)',
          border: '1px solid var(--amber-border)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--amber-700)',
          fontSize: '14px',
          lineHeight: '1.6',
        }}>
          <b>Physical Inspection Recommendation:</b> Infrastructure evidence is inconclusive for {refer.map(x => x.source).join(', ')}. Computer vision cannot verify physical measurements, safety exits or lab capacity; refer to expert inspection team.
        </div>
      )}

      {/* Rules Table */}
      <section className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Rule</th>
                <th>Result</th>
                <th>Evidence (Observed)</th>
                <th>Requirement (Expected)</th>
                <th>Source Document</th>
                <th>Regulatory Clause</th>
              </tr>
            </thead>
            <tbody>
              {res.length > 0 ? (
                res.map((x, idx) => (
                  <tr key={idx}>
                    <td>
                      <div style={{ fontWeight: 700, color: 'var(--ink)' }}>{x.rule_id} <span style={{ fontSize: '11px', color: 'var(--ink-muted)', fontWeight: 400 }}>v{x.rule_version}</span></div>
                      <div style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>{x.title}</div>
                    </td>
                    <td>
                      <StatusBadge type="compliance" value={x.status} />
                    </td>
                    <td style={{ fontSize: '12.5px' }}>{x.observed}</td>
                    <td style={{ fontSize: '12.5px' }}>{x.expected}</td>
                    <td style={{ fontSize: '12.5px' }}>{x.source}</td>
                    <td style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>{x.clause || '—'}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: '36px', color: 'var(--ink-muted)' }}>
                    No assessment records generated yet. Run validation to populate.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {rulesUsed.length > 0 && (
        <div style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>
          Rule versions evaluated: {rulesUsed.join(', ')}. Clauses with placeholders must be updated by regulatory administrators in Administration → Rules.
        </div>
      )}
    </div>
  );
}
