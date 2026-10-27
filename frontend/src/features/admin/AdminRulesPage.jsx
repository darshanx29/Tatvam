import React, { useState, useEffect } from 'react';
import { api } from '../../api';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Modal } from '../../components/ui/Modal';
import { Layers, Plus, Edit, AlertCircle, CheckCircle } from 'lucide-react';

export function AdminRulesPage({ onNavigate }) {
  const [rules, setRules] = useState([]);
  const [types, setTypes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  // Edit modal
  const [editModal, setEditModal] = useState({
    open: false,
    ruleId: null,
    jsonText: '',
    note: '',
    jsonError: '',
  });

  const fetchRules = async () => {
    setLoading(true);
    try {
      const res = await api.getRules();
      setRules(res.items || []);
      setTypes(res.types || []);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load rules');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleOpenEdit = (rule) => {
    const tpl = rule || {
      id: 'R-NEW-01',
      version: '1.0',
      title: 'New Mandatory Evidence Check',
      type: 'required_doc',
      categories: ['EoA'],
      severity: 'medium',
      clause: 'Approval Process Handbook Chapter 2',
      remedy: 'Upload certificate',
      doc_type: 'eoa_prior_approval',
      effective_from: new Date().toISOString().split('T')[0],
      effective_to: null,
      active: true,
      applies_when: {},
    };
    setEditModal({
      open: true,
      ruleId: rule ? rule.id : null,
      jsonText: JSON.stringify(tpl, null, 2),
      note: '',
      jsonError: '',
    });
  };

  const handleSaveRule = async (e) => {
    e.preventDefault();
    setEditModal(prev => ({ ...prev, jsonError: '' }));
    let defn;
    try {
      defn = JSON.parse(editModal.jsonText);
    } catch (err) {
      setEditModal(prev => ({ ...prev, jsonError: `Invalid JSON syntax: ${err.message}` }));
      return;
    }

    try {
      const res = await api.saveRule(editModal.ruleId, defn, editModal.note);
      setEditModal({ open: false, ruleId: null, jsonText: '', note: '', jsonError: '' });
      fetchRules();
      setActionMsg(`Rule ${defn.id} saved as version ${res.version}. Prior versions retained for audit.`);
    } catch (err) {
      setEditModal(prev => ({ ...prev, jsonError: err.message }));
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-end', gap: '16px' }}>
        <div>
          <span className="eyebrow">Regulatory Administration</span>
          <h1 className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '4px' }}>
            Checklists & Rules Management
          </h1>
          <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>
            Every change creates an immutable new version with an effective validity window. Earlier versions are locked and preserved for historic appeal audits.
          </p>
        </div>
        <button onClick={() => handleOpenEdit(null)} className="btn btn-primary">
          <Plus size={16} /> New Rule
        </button>
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

      {loading ? (
        <div style={{ padding: '40px', textAlign: 'center', color: 'var(--ink-muted)' }}>Loading rules directory…</div>
      ) : error ? (
        <div className="card" style={{ padding: '24px', color: 'var(--red-700)' }}>{error}</div>
      ) : (
        <section className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rule ID & Title</th>
                  <th>Type</th>
                  <th>Categories</th>
                  <th>Conditions</th>
                  <th>Severity</th>
                  <th>Version</th>
                  <th>Effective Period</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {rules.length > 0 ? (
                  rules.map((r) => (
                    <tr key={r.id}>
                      <td style={{ fontWeight: 700 }}>
                        <div style={{ color: 'var(--ink)' }}>{r.id}</div>
                        <div style={{ fontSize: '11.5px', color: 'var(--ink-muted)', fontWeight: 400 }}>{r.title}</div>
                      </td>
                      <td style={{ fontSize: '12px' }}>{r.type}</td>
                      <td style={{ fontSize: '12px' }}>{r.categories?.join(', ')}</td>
                      <td style={{ fontSize: '11.5px' }}>{r.applies_when && Object.keys(r.applies_when).length ? JSON.stringify(r.applies_when) : '—'}</td>
                      <td>
                        <StatusBadge type="severity" value={r.severity} />
                      </td>
                      <td style={{ fontSize: '12.5px' }}>v{r.version}</td>
                      <td style={{ fontSize: '11.5px', color: 'var(--ink-muted)' }}>
                        {r.effective_from} → {r.effective_to || 'open'}
                      </td>
                      <td>
                        {r.active === false ? (
                          <span className="badge badge-slate">Inactive</span>
                        ) : r.in_force ? (
                          <span className="badge badge-green">In Force</span>
                        ) : (
                          <span className="badge badge-amber">Not in Force</span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          onClick={() => handleOpenEdit(r)}
                          className="btn btn-outline btn-sm"
                          style={{ padding: '4px 10px', fontSize: '12px' }}
                        >
                          <Edit size={12} /> Edit
                        </button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} style={{ textAlign: 'center', padding: '30px', color: 'var(--ink-muted)' }}>
                      No rules found in repository.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* MODAL: Rule Editor */}
      <Modal
        isOpen={editModal.open}
        onClose={() => setEditModal({ open: false, ruleId: null, jsonText: '', note: '', jsonError: '' })}
        title={editModal.ruleId ? `Edit Rule · ${editModal.ruleId}` : 'Create New Rule'}
        maxWidth="680px"
      >
        <form onSubmit={handleSaveRule} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {editModal.jsonError && (
            <div style={{
              padding: '10px 14px',
              backgroundColor: 'var(--red-50)',
              border: '1px solid var(--red-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--red-700)',
              fontSize: '12.5px',
            }}>
              {editModal.jsonError}
            </div>
          )}

          <div>
            <label className="form-label">Rule JSON Definition</label>
            <textarea
              required
              rows={14}
              value={editModal.jsonText}
              onChange={(e) => setEditModal({ ...editModal, jsonText: e.target.value })}
              className="form-textarea font-mono"
              style={{ fontSize: '12px', lineHeight: '1.4' }}
            />
          </div>

          <div>
            <label className="form-label">Change Justification Note (Audit log)</label>
            <input
              required
              value={editModal.note}
              onChange={(e) => setEditModal({ ...editModal, note: e.target.value })}
              placeholder="e.g. Updated approval handbook clause 2.4 reference"
              className="form-input"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={() => setEditModal({ open: false, ruleId: null, jsonText: '', note: '', jsonError: '' })}
              className="btn btn-outline"
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Save Rule Version
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
