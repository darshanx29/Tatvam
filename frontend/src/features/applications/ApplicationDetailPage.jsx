import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Modal } from '../../components/ui/Modal';
import {
  ArrowLeft,
  Play,
  FileCheck,
  CheckCircle,
  AlertTriangle,
  Upload,
  RefreshCw,
  Eye,
  FileText,
  ShieldCheck,
  Clock,
  ExternalLink,
  MessageSquare,
  Lock,
} from 'lucide-react';

export function ApplicationDetailPage({ appId, onNavigate }) {
  const { user, isOfficer, isInstitution } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  // Modals state
  const [reviewModal, setReviewModal] = useState({ open: false, finding: null, action: 'accept', reason: '' });
  const [respondModal, setRespondModal] = useState({ open: false, finding: null, text: '' });
  const [manualVerifyModal, setManualVerifyModal] = useState({ open: false, document: '', outcome: 'verified', reference: '', note: '' });
  const [obsText, setObsText] = useState('');
  const [recChoice, setRecChoice] = useState('');
  const [recNote, setRecNote] = useState('');
  const [uploadFiles, setUploadFiles] = useState([]);

  const fetchApplication = async () => {
    try {
      const res = await api.getApplication(appId);
      setData(res);
      setRecChoice(res.application?.recommendation || 'recommended');
      setRecNote(res.application?.recommendation_note || '');
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load application');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplication();
  }, [appId]);

  // Polling when running/processing
  useEffect(() => {
    let timer = null;
    if (data?.application?.status === 'Processing' || data?.run?.status === 'running' || data?.run?.status === 'queued') {
      timer = setInterval(async () => {
        try {
          const st = await api.getStatus(appId);
          if (st.application_status !== 'Processing' && st.run?.status === 'done') {
            fetchApplication();
          } else {
            setData(prev => prev ? { ...prev, run: st.run, application: { ...prev.application, status: st.application_status } } : prev);
          }
        } catch {
          // ignore polling errors
        }
      }, 1500);
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [data?.application?.status, data?.run?.status, appId]);

  const handleValidate = async () => {
    try {
      await api.validateApplication(appId);
      fetchApplication();
      setActionMsg('Validation queued. Preliminary checks are running.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSubmitDraft = async () => {
    try {
      await api.submitApplication(appId);
      fetchApplication();
      setActionMsg('Application submitted. Preliminary checks initiated.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleUploadMore = async (e) => {
    e.preventDefault();
    if (!uploadFiles.length) return;
    try {
      const fd = new FormData();
      for (let f of uploadFiles) fd.append('files', f);
      await api.uploadDocuments(appId, fd);
      setUploadFiles([]);
      fetchApplication();
      setActionMsg('Documents uploaded successfully.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReviewSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.reviewFinding(reviewModal.finding.id, {
        action: reviewModal.action,
        reason: reviewModal.reason,
      });
      setReviewModal({ open: false, finding: null, action: 'accept', reason: '' });
      fetchApplication();
      setActionMsg('Review action recorded.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleRespondSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.respondFinding(respondModal.finding.id, respondModal.text);
      setRespondModal({ open: false, finding: null, text: '' });
      fetchApplication();
      setActionMsg('Response recorded for reviewing officers.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleManualVerifySubmit = async (e) => {
    e.preventDefault();
    try {
      await api.manualVerify(appId, {
        document: manualVerifyModal.document,
        outcome: manualVerifyModal.outcome,
        reference: manualVerifyModal.reference,
        note: manualVerifyModal.note,
      });
      setManualVerifyModal({ open: false, document: '', outcome: 'verified', reference: '', note: '' });
      fetchApplication();
      setActionMsg('Manual verification recorded.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleReverifySource = async (docName) => {
    try {
      await api.reverify(appId, docName);
      fetchApplication();
      setActionMsg(`Source retry queued for ${docName}`);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleAddObservation = async (e) => {
    e.preventDefault();
    if (!obsText.trim()) return;
    try {
      await api.addObservation(appId, obsText);
      setObsText('');
      fetchApplication();
      setActionMsg('Observation added.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleSaveRecommendation = async (e) => {
    e.preventDefault();
    try {
      await api.setRecommendation(appId, recChoice, recNote);
      fetchApplication();
      setActionMsg('Recommendation recorded.');
    } catch (err) {
      setError(err.message);
    }
  };

  const handleCloseApplication = async () => {
    if (!window.confirm('Close application demonstration?')) return;
    try {
      await api.closeApplication(appId);
      fetchApplication();
      setActionMsg('Application marked as Closed in prototype.');
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return <div style={{ padding: '60px', textAlign: 'center', color: 'var(--ink-muted)' }}>Loading application details…</div>;
  }

  if (error && !data) {
    return (
      <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
        <AlertTriangle size={32} style={{ color: 'var(--red-600)', margin: '0 auto 12px' }} />
        <h2 className="font-editorial" style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Unable to access application</h2>
        <p style={{ color: 'var(--ink-muted)', marginBottom: '20px' }}>{error}</p>
        <button onClick={() => onNavigate('/dashboard')} className="btn btn-primary">Return to Dashboard</button>
      </div>
    );
  }

  const a = data.application;
  const checklist = data.checklist || [];
  const findings = data.findings || [];
  const verifications = data.verifications || [];
  const docs = data.docs || [];
  const infraDocs = data.infra_docs || [];
  const versions = data.versions || [];
  const notes = data.notes || [];
  const mine = data.mine;
  const run = data.run;
  const recOptions = data.recommendation_options || {};

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '26px' }}>
      {/* Back button & Action notification */}
      <div>
        <button
          onClick={() => onNavigate('/dashboard')}
          className="btn btn-outline btn-sm"
          style={{ marginBottom: '14px' }}
        >
          <ArrowLeft size={14} /> Back to Dashboard
        </button>

        {actionMsg && (
          <div style={{
            padding: '10px 16px',
            backgroundColor: 'var(--green-50)',
            border: '1px solid var(--green-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--green-700)',
            fontSize: '13.5px',
            fontWeight: 600,
            marginBottom: '16px',
          }}>
            {actionMsg}
          </div>
        )}
      </div>

      {/* Main Header Card */}
      <div className="card" style={{ padding: '24px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'flex-start', gap: '16px' }}>
          <div>
            <span className="eyebrow">Application Workspace</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginTop: '4px', flexWrap: 'wrap' }}>
              <h1 className="font-editorial" style={{ fontSize: '2.2rem', fontWeight: 800, margin: 0 }}>
                {a.id}
              </h1>
              <StatusBadge type="app" value={a.status} />
            </div>
            <p style={{ fontSize: '13.5px', color: 'var(--ink-muted)', marginTop: '8px' }}>
              Institution <b>{a.institution_id}</b> · {a.category} · Academic Year {a.academic_year}
              {a.programme && ` · ${a.programme}`}
              {a.intake && ` (Intake: ${a.intake})`}
              {a.last_run && ` · Last run: ${a.last_run}`}
            </p>
          </div>

          {/* Action buttons */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
            {a.status === 'Draft' && mine ? (
              <button onClick={handleSubmitDraft} className="btn btn-primary">
                Submit & Run Checks
              </button>
            ) : (
              <button onClick={handleValidate} className="btn btn-primary">
                <Play size={15} /> Run Validation
              </button>
            )}
            <button onClick={() => onNavigate(`/applications/${a.id}/compliance`)} className="btn btn-secondary">
              <FileCheck size={15} /> Compliance
            </button>
            <button onClick={() => onNavigate(`/applications/${a.id}/audit`)} className="btn btn-secondary">
              <Clock size={15} /> Audit History
            </button>
            <button onClick={() => onNavigate(`/applications/${a.id}/report`)} className="btn btn-secondary">
              <FileText size={15} /> Report
            </button>
          </div>
        </div>

        {/* Real-time processing progress bar */}
        {(a.status === 'Processing' || run?.status === 'running' || run?.status === 'queued') && (
          <div style={{ marginTop: '20px', padding: '16px', backgroundColor: 'var(--brand-50)', borderRadius: 'var(--radius-md)', border: '1px solid var(--brand-200)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px', fontWeight: 600, color: 'var(--brand-800)', marginBottom: '6px' }}>
              <span>{run?.message || 'Processing multimodal checks…'}</span>
              <span>{run?.progress || 0}%</span>
            </div>
            <div className="progress-bar-bg">
              <div className="progress-bar-fill" style={{ width: `${run?.progress || 0}%` }}></div>
            </div>
          </div>
        )}
      </div>

      {/* Grid: Evidence Checklist + Source Verification */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '22px' }}>
        {/* Evidence Checklist */}
        <div className="card" style={{ padding: '22px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '16px' }}>
            Evidence Checklist
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {checklist.map((c, idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  borderRadius: 'var(--radius-md)',
                  backgroundColor: '#fbfaf8',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', fontSize: '13.5px' }}>
                  {c.present ? (
                    <CheckCircle size={18} style={{ color: 'var(--green-600)', flexShrink: 0 }} />
                  ) : (
                    <AlertTriangle size={18} style={{ color: 'var(--red-600)', flexShrink: 0 }} />
                  )}
                  <span style={{ fontWeight: 600, color: 'var(--ink)' }}>{c.title}</span>
                </div>
                <span className={`badge ${c.present ? 'badge-green' : 'badge-red'}`}>
                  {c.present ? 'Present' : 'Missing'}
                </span>
              </div>
            ))}
          </div>

          {/* Upload more documents */}
          {mine && a.status !== 'Processing' && (
            <form onSubmit={handleUploadMore} style={{ marginTop: '20px', paddingTop: '16px', borderTop: '1px solid var(--border-main)' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, marginBottom: '8px' }}>Add supporting document</div>
              <div style={{ display: 'flex', gap: '8px' }}>
                <input
                  type="file"
                  multiple
                  accept=".pdf,.jpg,.jpeg,.png"
                  onChange={(e) => setUploadFiles(Array.from(e.target.files))}
                  style={{ fontSize: '12px', flex: 1 }}
                />
                <button type="submit" disabled={!uploadFiles.length} className="btn btn-primary btn-sm">
                  <Upload size={14} /> Upload
                </button>
              </div>
            </form>
          )}
        </div>

        {/* Source Verification */}
        <div className="card" style={{ padding: '22px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '16px' }}>
            Authoritative Source Verification
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {verifications.length > 0 ? (
              verifications.map((v, idx) => (
                <div
                  key={idx}
                  style={{
                    padding: '12px 14px',
                    borderRadius: 'var(--radius-md)',
                    border: '1px solid var(--border-subtle)',
                    backgroundColor: '#ffffff',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '10px' }}>
                    <div>
                      <div style={{ fontWeight: 700, fontSize: '14px', color: 'var(--ink)' }}>
                        {v.document} {v.manual && <span style={{ fontSize: '11px', color: 'var(--brand-600)' }}>(manual)</span>}
                      </div>
                      <div style={{ fontSize: '12px', color: 'var(--ink-secondary)', marginTop: '2px' }}>
                        {v.detail}
                      </div>
                      <div style={{ fontSize: '11px', color: 'var(--ink-muted)', marginTop: '4px' }}>
                        Source: {v.source} {v.reference && `· Ref: ${v.reference}`} · Attempt: {v.attempt} · {v.timestamp}
                      </div>
                    </div>
                    <StatusBadge type="verification" value={v.status} />
                  </div>

                  {/* Officer Actions for non-verified sources */}
                  {isOfficer && v.status !== 'verified' && (
                    <div style={{ display: 'flex', gap: '8px', marginTop: '10px', paddingTop: '8px', borderTop: '1px solid var(--border-subtle)' }}>
                      {!v.manual && ['source_unavailable', 'pending'].includes(v.status) && (
                        <button
                          onClick={() => handleReverifySource(v.document)}
                          className="btn btn-outline btn-sm"
                          style={{ fontSize: '11.5px' }}
                        >
                          <RefreshCw size={12} /> Retry Source
                        </button>
                      )}
                      <button
                        onClick={() => setManualVerifyModal({ open: true, document: v.document, outcome: 'verified', reference: '', note: '' })}
                        className="btn btn-secondary btn-sm"
                        style={{ fontSize: '11.5px' }}
                      >
                        Record Manual Verification
                      </button>
                    </div>
                  )}
                </div>
              ))
            ) : (
              <p style={{ fontSize: '13px', color: 'var(--ink-muted)' }}>No verification records yet.</p>
            )}
          </div>
        </div>
      </div>

      {/* Findings Section */}
      <section className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border-main)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700 }}>
              Compliance & Anomaly Findings
            </h2>
            <div style={{ fontSize: '12.5px', color: 'var(--ink-muted)' }}>
              Open: {findings.filter(f => ['open', 'escalated', 'evidence_requested'].includes(f.state)).length} items
            </div>
          </div>
        </div>

        <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Rule</th>
                <th>Finding / Evidence</th>
                <th>Severity</th>
                <th>Source</th>
                <th>Observed</th>
                <th>Expected</th>
                <th>Next Step</th>
                <th>State</th>
                <th style={{ textAlign: 'right' }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {findings.length > 0 ? (
                findings.map((f) => (
                  <tr key={f.id} style={{ opacity: ['resolved', 'dismissed'].includes(f.state) ? 0.6 : 1 }}>
                    <td style={{ fontWeight: 700, whiteSpace: 'nowrap' }}>
                      <span style={{ color: 'var(--ink)' }}>{f.rule_id}</span>
                      <div style={{ fontSize: '10.5px', color: 'var(--ink-muted)', fontWeight: 400 }}>v{f.rule_version} · {f.kind}</div>
                    </td>
                    <td>
                      <div style={{ fontWeight: 600, color: 'var(--ink)' }}>{f.title}</div>
                      <div style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>{f.reason}</div>
                      {f.clause && !f.clause.startsWith('<<') && f.clause !== 'n/a' && (
                        <div style={{ fontSize: '11px', color: 'var(--brand-700)', marginTop: '2px' }}>Clause: {f.clause}</div>
                      )}
                      {f.private_detail && (
                        <div style={{ fontSize: '11px', color: 'var(--red-700)', marginTop: '2px' }}>Officer note: {f.private_detail}</div>
                      )}
                      {/* Review trail for finding */}
                      {f.reviews && f.reviews.map((r) => (
                        <div key={r.id} style={{ marginTop: '4px', fontSize: '11px', background: '#faf8f5', padding: '3px 6px', borderRadius: '4px' }}>
                          <b>{r.actor}</b> · {r.action?.replace(/_/g, ' ')}: {r.reason}
                        </div>
                      ))}
                    </td>
                    <td>
                      <StatusBadge type="severity" value={f.severity} />
                    </td>
                    <td style={{ fontSize: '12px' }}>{f.source}</td>
                    <td style={{ fontSize: '12px' }}>{f.observed}</td>
                    <td style={{ fontSize: '12px' }}>{f.expected}</td>
                    <td style={{ fontSize: '12px' }}>{f.next_step}</td>
                    <td>
                      <StatusBadge type="state" value={f.state} />
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      {isOfficer && (
                        <button
                          onClick={() => setReviewModal({ open: true, finding: f, action: 'accept', reason: '' })}
                          className="btn btn-secondary btn-sm"
                        >
                          Review
                        </button>
                      )}
                      {mine && ['open', 'escalated', 'evidence_requested'].includes(f.state) && (
                        <button
                          onClick={() => setRespondModal({ open: true, finding: f, text: '' })}
                          className="btn btn-outline btn-sm"
                        >
                          Respond
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={9} style={{ textAlign: 'center', padding: '32px', color: 'var(--ink-muted)' }}>
                    No findings detected. Preliminary checks passed.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Uploaded Documents Table */}
      <section className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: '18px 24px', borderBottom: '1px solid var(--border-main)' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.3rem', fontWeight: 700 }}>
            Uploaded Documents & OCR Data
          </h2>
          <div style={{ fontSize: '12px', color: 'var(--ink-muted)', marginTop: '2px' }}>
            Optical character recognition output with page-level coordinates. Open viewer to inspect bounding boxes and correct values.
          </div>
        </div>

        <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Document Name</th>
                <th>Type</th>
                <th>OCR Method</th>
                <th>Confidence</th>
                <th>Fields Extracted</th>
                <th>Signature</th>
                <th style={{ textAlign: 'right' }}>Viewer</th>
              </tr>
            </thead>
            <tbody>
              {docs.length > 0 ? (
                docs.map((d) => (
                  <tr key={d.id}>
                    <td style={{ fontWeight: 700, color: 'var(--ink)' }}>{d.name}</td>
                    <td><span className="badge badge-amber">{d.doc_type?.replace(/_/g, ' ')}</span></td>
                    <td style={{ fontSize: '12px' }}>{d.ocr_method?.replace(/_/g, ' ')}</td>
                    <td style={{ fontSize: '12px' }}>
                      Class: {d.class_conf != null ? Math.round(d.class_conf * 100) : '—'}% · OCR: {d.mean_conf != null ? Math.round(d.mean_conf * 100) : '—'}%
                    </td>
                    <td style={{ fontSize: '12px' }}>
                      {d.fields_count} fields
                      {d.low_conf_count > 0 && <span style={{ color: 'var(--red-700)', marginLeft: '6px', fontWeight: 700 }}>({d.low_conf_count} low-confidence)</span>}
                    </td>
                    <td style={{ fontSize: '12px' }}>{d.signature}</td>
                    <td style={{ textAlign: 'right' }}>
                      <button
                        onClick={() => onNavigate(`/documents/${d.id}`)}
                        className="btn btn-outline btn-sm"
                      >
                        <Eye size={14} /> Open Viewer
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7} style={{ textAlign: 'center', padding: '28px', color: 'var(--ink-muted)' }}>
                    No documents uploaded yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Infrastructure Evidence (Advisory) */}
      {infraDocs.length > 0 && (
        <section className="card" style={{ padding: '22px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '6px' }}>
            Infrastructure Evidence Assessment (Advisory)
          </h2>
          <p style={{ fontSize: '12.5px', color: 'var(--ink-muted)', marginBottom: '14px' }}>
            Computer vision measures resolution, sharpness, and brightness to gauge legibility. Physical compliance requires in-person inspection.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {infraDocs.map((inf) => (
              <div key={inf.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px 14px', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
                <span style={{ fontSize: '13.5px', fontWeight: 600 }}>
                  {inf.name} · {inf.quality?.width}×{inf.quality?.height} · Sharpness: {inf.quality?.sharpness} · Brightness: {inf.quality?.brightness}
                </span>
                <span className={`badge ${inf.quality?.issues?.length ? 'badge-amber' : 'badge-green'}`}>
                  {inf.quality?.issues?.length ? inf.quality.issues.join('; ') : 'Usable'}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Officer Observation & Recommendation Section */}
      {isOfficer && (
        <section className="card" style={{ padding: '24px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '28px' }}>
            {/* Add Observation */}
            <div>
              <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '8px' }}>
                Officer Observation
              </h2>
              <form onSubmit={handleAddObservation} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <textarea
                  value={obsText}
                  onChange={(e) => setObsText(e.target.value)}
                  required
                  rows={3}
                  placeholder="Record an official regulatory observation on this file…"
                  className="form-textarea"
                />
                <button type="submit" className="btn btn-secondary" style={{ alignSelf: 'flex-start' }}>
                  <MessageSquare size={15} /> Add Observation
                </button>
              </form>
            </div>

            {/* Recommendation & Closure */}
            <div>
              <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '8px' }}>
                Scrutiny Recommendation & Closure
              </h2>
              <form onSubmit={handleSaveRecommendation} style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                <select
                  value={recChoice}
                  onChange={(e) => setRecChoice(e.target.value)}
                  className="form-select"
                >
                  {Object.entries(recOptions).map(([k, label]) => (
                    <option key={k} value={k}>{label}</option>
                  ))}
                </select>
                <textarea
                  value={recNote}
                  onChange={(e) => setRecNote(e.target.value)}
                  rows={2}
                  placeholder="Recommendation rationale note…"
                  className="form-textarea"
                />
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                  <button type="submit" className="btn btn-primary btn-sm">
                    Save Recommendation
                  </button>
                  <button
                    type="button"
                    onClick={handleCloseApplication}
                    className="btn btn-outline btn-sm"
                  >
                    Close in Prototype
                  </button>
                </div>
              </form>
            </div>
          </div>
        </section>
      )}

      {/* Action Trail / Observations Log */}
      {notes.length > 0 && (
        <section className="card" style={{ padding: '22px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '12px' }}>
            Officer Action & Observation Log
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {notes.map((n) => (
              <div key={n.id} style={{ fontSize: '13px', color: 'var(--ink)' }}>
                <span style={{ fontSize: '11.5px', color: 'var(--ink-muted)' }}>{n.ts}</span> · <b>{n.actor}</b> · {n.action?.replace(/_/g, ' ')} — {n.reason}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Version History */}
      {versions.length > 0 && (
        <section className="card" style={{ padding: '22px' }}>
          <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '10px' }}>
            Application Version Snapshots ({versions.length})
          </h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {versions.map((v, idx) => (
              <div key={idx} style={{ fontSize: '12.5px', color: 'var(--ink)' }}>
                v{v.version} · {v.ts} · <b>{v.actor}</b> · {v.reason}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* MODAL: Review Finding */}
      <Modal
        isOpen={reviewModal.open}
        onClose={() => setReviewModal({ open: false, finding: null, action: 'accept', reason: '' })}
        title={`Review Finding · ${reviewModal.finding?.rule_id || ''}`}
      >
        <form onSubmit={handleReviewSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label className="form-label">Review Action</label>
            <select
              value={reviewModal.action}
              onChange={(e) => setReviewModal({ ...reviewModal, action: e.target.value })}
              className="form-select"
            >
              <option value="accept">Accept Flag</option>
              <option value="dismiss">Dismiss Flag</option>
              <option value="escalate">Escalate for Physical Inspection</option>
              <option value="request_evidence">Request Additional Evidence</option>
            </select>
          </div>

          <div>
            <label className="form-label">Mandatory Rationale Note</label>
            <textarea
              required
              rows={3}
              value={reviewModal.reason}
              onChange={(e) => setReviewModal({ ...reviewModal, reason: e.target.value })}
              placeholder="State the regulatory justification for this action…"
              className="form-textarea"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={() => setReviewModal({ open: false, finding: null, action: 'accept', reason: '' })}
              className="btn btn-outline"
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Record Decision
            </button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Respond to Finding (Institution) */}
      <Modal
        isOpen={respondModal.open}
        onClose={() => setRespondModal({ open: false, finding: null, text: '' })}
        title={`Respond to ${respondModal.finding?.rule_id || 'Finding'}`}
      >
        <form onSubmit={handleRespondSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label className="form-label">Institutional Response / Clarification</label>
            <textarea
              required
              rows={3}
              value={respondModal.text}
              onChange={(e) => setRespondModal({ ...respondModal, text: e.target.value })}
              placeholder="Explain the circumstance or refer to uploaded replacement documents…"
              className="form-textarea"
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={() => setRespondModal({ open: false, finding: null, text: '' })}
              className="btn btn-outline"
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Send Response
            </button>
          </div>
        </form>
      </Modal>

      {/* MODAL: Manual Verification */}
      <Modal
        isOpen={manualVerifyModal.open}
        onClose={() => setManualVerifyModal({ open: false, document: '', outcome: 'verified', reference: '', note: '' })}
        title={`Record Manual Verification · ${manualVerifyModal.document}`}
      >
        <form onSubmit={handleManualVerifySubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label className="form-label">Verification Outcome</label>
            <select
              value={manualVerifyModal.outcome}
              onChange={(e) => setManualVerifyModal({ ...manualVerifyModal, outcome: e.target.value })}
              className="form-select"
            >
              <option value="verified">Verified with Issuer / Council</option>
              <option value="mismatch_detected">Mismatch Confirmed</option>
              <option value="expired">Expired Certificate</option>
              <option value="manual_review_required">Inconclusive / Incomplete Proof</option>
            </select>
          </div>

          <div>
            <label className="form-label">Authoritative Registry Reference</label>
            <input
              value={manualVerifyModal.reference}
              onChange={(e) => setManualVerifyModal({ ...manualVerifyModal, reference: e.target.value })}
              placeholder="e.g. DISP-2026-REG-88"
              className="form-input"
            />
          </div>

          <div>
            <label className="form-label">Mandatory Audit Note</label>
            <textarea
              required
              rows={3}
              value={manualVerifyModal.note}
              onChange={(e) => setManualVerifyModal({ ...manualVerifyModal, note: e.target.value })}
              placeholder="Record details of inquiry, email verification, or portal cross-reference…"
              className="form-textarea"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={() => setManualVerifyModal({ open: false, document: '', outcome: 'verified', reference: '', note: '' })}
              className="btn btn-outline"
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Save Verification
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
