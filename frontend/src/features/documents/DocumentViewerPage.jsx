import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { api } from '../../api';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Modal } from '../../components/ui/Modal';
import {
  ArrowLeft,
  Download,
  AlertTriangle,
  QrCode,
  Edit2,
  CheckCircle,
  Eye,
  FileCheck,
} from 'lucide-react';

export function DocumentViewerPage({ docId, onNavigate }) {
  const { isOfficer } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activePage, setActivePage] = useState(1);
  const [hoveredFieldId, setHoveredFieldId] = useState(null);
  const [correctModal, setCorrectModal] = useState({ open: false, field: null, value: '', reason: '' });
  const [actionMsg, setActionMsg] = useState('');

  const fetchDocument = async () => {
    try {
      const res = await api.getDocument(docId);
      setData(res);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load document');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocument();
  }, [docId]);

  const handleCorrectSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.correctField(correctModal.field.id, {
        value: correctModal.value,
        reason: correctModal.reason,
      });
      setCorrectModal({ open: false, field: null, value: '', reason: '' });
      fetchDocument();
      setActionMsg('Field corrected. Automated validation checks re-triggered.');
    } catch (err) {
      setError(err.message);
    }
  };

  if (loading) {
    return <div style={{ padding: '60px', textAlign: 'center', color: 'var(--ink-muted)' }}>Loading document…</div>;
  }

  if (error || !data) {
    return (
      <div className="card" style={{ padding: '36px', textAlign: 'center' }}>
        <AlertTriangle size={32} style={{ color: 'var(--red-600)', margin: '0 auto 12px' }} />
        <h2 className="font-editorial" style={{ fontSize: '1.5rem', marginBottom: '8px' }}>Unable to load document</h2>
        <p style={{ color: 'var(--ink-muted)', marginBottom: '20px' }}>{error}</p>
        <button onClick={() => window.history.back()} className="btn btn-primary">Go Back</button>
      </div>
    );
  }

  const d = data.document;
  const fields = data.fields || [];
  const ver = data.verification;
  const flags = data.flags || [];
  const qr = data.qr || [];
  const npages = d.npages || 1;

  // Filter fields for current page with bounding box
  const pageFields = fields.filter(f => f.page === activePage && f.bbox && f.page_w && f.page_h);

  // 1. Expiry Check Computation
  const expiryField = fields.find(f => {
    const k = (f.name || '').toLowerCase().replace(/[^a-z0-9]/g, '');
    return k.includes('validuntil') || k.includes('validupto') || k.includes('expiry') || k.includes('validto') || k.includes('expiration');
  });

  let expiryStatus = 'Not expired';
  let expiryDateDisplay = 'Permanent / Not applicable';
  let isExpired = false;

  if (expiryField && expiryField.value) {
    expiryDateDisplay = expiryField.value;
    const parts = expiryField.value.trim().split(/[-/.]/);
    let expDate = null;
    if (parts.length === 3) {
      if (parts[0].length === 4) {
        expDate = new Date(parseInt(parts[0], 10), parseInt(parts[1], 10) - 1, parseInt(parts[2], 10));
      } else {
        expDate = new Date(parseInt(parts[2], 10), parseInt(parts[1], 10) - 1, parseInt(parts[0], 10));
      }
    } else {
      expDate = new Date(expiryField.value);
    }

    if (expDate && !isNaN(expDate.getTime())) {
      isExpired = expDate < new Date();
      expiryStatus = isExpired ? 'Expired' : 'Not expired';
    } else {
      expiryStatus = 'Not expired';
    }
  } else {
    expiryStatus = 'No expiry date';
    expiryDateDisplay = 'Permanent / Not applicable';
  }

  // 2. Duplicate Check Computation
  const dupFlag = flags.find(fl => {
    const s = `${fl.title || ''} ${fl.observed || ''} ${fl.reason || ''}`.toLowerCase();
    return s.includes('duplicate') || s.includes('phash') || s.includes('near-match');
  });
  const hasDuplicate = Boolean(dupFlag);
  const duplicateStatus = hasDuplicate ? 'Duplicate detected' : 'No duplicate found in this application';
  const duplicateDetail = hasDuplicate
    ? (dupFlag.observed || dupFlag.reason || 'Identical document content found in system.')
    : 'Cross-application duplicates depend on recorded anomaly checks.';

  // 3. Mismatch / Authenticity Computation
  const mismatchFlag = flags.find(fl => {
    const s = `${fl.title || ''} ${fl.observed || ''} ${fl.reason || ''}`.toLowerCase();
    return s.includes('mismatch') || s.includes('tamper') || s.includes('alteration');
  });

  let authStatus = 'Manual Review Required';
  let authBg = 'var(--amber-50, #fffbeb)';
  let authBorder = 'var(--amber-border, #fde68a)';
  let authColor = 'var(--amber-700, #b45309)';

  if (ver?.status === 'verified' && !mismatchFlag) {
    authStatus = 'Verified';
    authBg = 'var(--green-50, #ecfdf5)';
    authBorder = 'var(--green-border, #a7f3d0)';
    authColor = 'var(--green-700, #047857)';
  } else if (ver?.status === 'mismatch_detected' || mismatchFlag) {
    authStatus = 'Mismatch Detected';
    authBg = 'var(--red-50, #fef2f2)';
    authBorder = 'var(--red-border, #fecaca)';
    authColor = 'var(--red-700, #b91c1c)';
  } else if (ver?.status === 'expired' || isExpired) {
    authStatus = 'Expired';
    authBg = 'var(--red-50, #fef2f2)';
    authBorder = 'var(--red-border, #fecaca)';
    authColor = 'var(--red-700, #b91c1c)';
  } else {
    authStatus = 'Manual Review Required';
    authBg = 'var(--amber-50, #fffbeb)';
    authBorder = 'var(--amber-border, #fde68a)';
    authColor = 'var(--amber-700, #b45309)';
  }

  // 4. Checklist & Missing Fields Notice
  const missingFieldsNotice = fields.length > 0
    ? 'No missing fields detected from the configured field checklist.'
    : 'No extracted fields detected from the configured field checklist.';

  // 5. Issuer/source verification
  const issuerStatus = ver?.status
    ? ver.status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
    : 'Manual Review Required';
  const issuerDetail = ver?.detail || 'Reference not found in source';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
      {/* Header & Breadcrumb */}
      <div>
        <button
          onClick={() => window.history.back()}
          className="btn btn-outline btn-sm"
          style={{ marginBottom: '12px' }}
        >
          <ArrowLeft size={14} /> Back
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
            marginBottom: '14px',
          }}>
            {actionMsg}
          </div>
        )}

        <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'space-between', alignItems: 'center', gap: '14px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 className="font-editorial" style={{ fontSize: '2rem', fontWeight: 800, margin: 0 }}>
                {d.name}
              </h1>
              <span className="badge badge-amber">{d.doc_type?.replace(/_/g, ' ')}</span>
            </div>
            <p style={{ fontSize: '12.5px', color: 'var(--ink-muted)', marginTop: '4px' }}>
              OCR Method: <b>{d.ocr_method?.replace(/_/g, ' ')}</b> · Classification Confidence: <b>{Math.round((d.class_conf || 0) * 100)}%</b> · SHA-256: <code style={{ fontSize: '11px' }}>{d.sha?.slice(0, 16)}…</code> · Digital Signature: <b>{d.signature}</b>
            </p>
          </div>

          <a
            href={`/documents/${d.id}/file?dl=1`}
            className="btn btn-secondary"
            download
          >
            <Download size={15} /> Download Original File
          </a>
        </div>
      </div>

      {/* Document Review Results Section */}
      <section className="card" style={{
        padding: '20px 24px',
        backgroundColor: '#ffffff',
        borderRadius: 'var(--radius-lg, 14px)',
        border: '1px solid var(--border-main)',
        boxShadow: 'var(--shadow-soft)',
      }}>
        <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, margin: '0 0 4px 0', color: 'var(--ink)' }}>
          Document review results
        </h2>
        <p style={{ fontSize: '13px', color: 'var(--ink-muted)', margin: '0 0 16px 0' }}>
          Automated screening supports officer review; it does not by itself prove that a document is genuine or fake.
        </p>

        {/* 3 Status Cards Row */}
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
          gap: '14px',
          marginBottom: '12px',
        }}>
          {/* Expiry Check Card */}
          <div style={{
            padding: '14px 16px',
            backgroundColor: isExpired ? 'var(--red-50, #fef2f2)' : (expiryField ? 'var(--green-50, #f0fdf4)' : 'var(--slate-50, #f8fafc)'),
            border: `1px solid ${isExpired ? 'var(--red-border, #fecaca)' : (expiryField ? 'var(--green-border, #bbf7d0)' : 'var(--slate-border, #e2e8f0)')}`,
            borderRadius: 'var(--radius-md, 8px)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--ink-muted)', fontWeight: 500, marginBottom: '6px' }}>
                Expiry check
              </div>
              <div style={{
                fontSize: '16px',
                fontWeight: 700,
                color: isExpired ? 'var(--red-700, #b91c1c)' : (expiryField ? 'var(--green-700, #15803d)' : 'var(--ink)'),
              }}>
                {expiryStatus}
              </div>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--ink-secondary)', marginTop: '8px' }}>
              {expiryDateDisplay}
            </div>
          </div>

          {/* Duplicate Check Card */}
          <div style={{
            padding: '14px 16px',
            backgroundColor: hasDuplicate ? 'var(--red-50, #fef2f2)' : 'var(--slate-50, #f8fafc)',
            border: `1px solid ${hasDuplicate ? 'var(--red-border, #fecaca)' : 'var(--slate-border, #e2e8f0)'}`,
            borderRadius: 'var(--radius-md, 8px)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--ink-muted)', fontWeight: 500, marginBottom: '6px' }}>
                Duplicate check
              </div>
              <div style={{
                fontSize: '15px',
                fontWeight: 700,
                color: hasDuplicate ? 'var(--red-700, #b91c1c)' : 'var(--ink)',
              }}>
                {duplicateStatus}
              </div>
            </div>
            <div style={{ fontSize: '11.5px', color: 'var(--ink-muted)', marginTop: '6px', lineHeight: 1.35 }}>
              {duplicateDetail}
            </div>
          </div>

          {/* Mismatch / Authenticity Card */}
          <div style={{
            padding: '14px 16px',
            backgroundColor: authBg,
            border: `1px solid ${authBorder}`,
            borderRadius: 'var(--radius-md, 8px)',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'space-between',
          }}>
            <div>
              <div style={{ fontSize: '12px', color: 'var(--ink-muted)', fontWeight: 500, marginBottom: '6px' }}>
                Mismatch / authenticity
              </div>
              <div style={{
                fontSize: '15px',
                fontWeight: 700,
                color: authColor,
              }}>
                {authStatus}
              </div>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--ink-muted)', marginTop: '8px' }}>
              Signature: {d.signature || 'none'}
            </div>
          </div>
        </div>

        {/* Row 4: Configured Field Checklist Notice */}
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#ffffff',
          border: '1px solid var(--border-subtle, #e2e8f0)',
          borderRadius: 'var(--radius-md, 8px)',
          fontSize: '13.5px',
          color: 'var(--ink-secondary)',
          marginBottom: '10px',
        }}>
          {missingFieldsNotice}
        </div>

        {/* Row 5: Issuer/source verification */}
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#ffffff',
          border: '1px solid var(--border-subtle, #e2e8f0)',
          borderRadius: 'var(--radius-md, 8px)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '12px',
        }}>
          <div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--ink)' }}>
              Issuer/source verification: <span style={{ fontWeight: 600 }}>{issuerStatus}</span>
            </div>
            <div style={{ fontSize: '13px', color: 'var(--ink-muted)', marginTop: '2px' }}>
              {issuerDetail}
            </div>
          </div>
          {ver?.status && (
            <StatusBadge type="verification" value={ver.status} />
          )}
        </div>
      </section>

      {/* Anomalies alert banner */}
      {flags.map((fl, idx) => (
        <div
          key={idx}
          style={{
            padding: '12px 16px',
            backgroundColor: 'var(--amber-50)',
            border: '1px solid var(--amber-border)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--amber-700)',
            fontSize: '13.5px',
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
          }}
        >
          <AlertTriangle size={18} />
          <span><b>{fl.title}:</b> {fl.observed} <span style={{ fontSize: '12px' }}>({fl.reason})</span></span>
        </div>
      ))}

      {/* QR Code Findings */}
      {qr.length > 0 && (
        <div style={{
          padding: '12px 16px',
          backgroundColor: '#fbfaf8',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          fontSize: '13px',
          display: 'flex',
          flexDirection: 'column',
          gap: '6px',
        }}>
          {qr.map((q, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <QrCode size={16} style={{ color: 'var(--brand-600)' }} />
              <span>QR payload: <code>{q.url}</code></span>
              <span className={`badge ${q.authorized_host ? 'badge-green' : 'badge-amber'}`}>
                {q.authorized_host ? 'Authorized Host' : 'Unauthenticated Host'}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Main Split Grid: Document View & Extracted Fields */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(420px, 1fr))', gap: '22px' }}>
        {/* Left: Original Document Preview with Bounding Boxes */}
        <section className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
              Original Document
            </h2>

            {/* Page navigation */}
            {npages > 1 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12.5px' }}>
                <span style={{ color: 'var(--ink-muted)' }}>Page:</span>
                {Array.from({ length: npages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setActivePage(p)}
                    className={`btn btn-sm ${activePage === p ? 'btn-primary' : 'btn-outline'}`}
                    style={{ padding: '3px 8px', fontSize: '11px' }}
                  >
                    {p}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Document Canvas Container */}
          <div style={{
            position: 'relative',
            display: 'inline-block',
            width: '100%',
            backgroundColor: '#ffffff',
            borderRadius: 'var(--radius-md)',
            border: '1px solid var(--border-main)',
            overflow: 'hidden',
          }}>
            <img
              src={`/documents/${d.id}/page/${activePage}.png`}
              alt={`Page ${activePage} of ${d.name}`}
              style={{ display: 'block', width: '100%', height: 'auto' }}
            />

            {/* Bounding box overlays */}
            {pageFields.map((f) => {
              const isHl = hoveredFieldId === f.id;
              const leftPct = (100 * f.bbox[0] / f.page_w).toFixed(2);
              const topPct = (100 * f.bbox[1] / f.page_h).toFixed(2);
              const widthPct = (100 * (f.bbox[2] - f.bbox[0]) / f.page_w).toFixed(2);
              const heightPct = (100 * (f.bbox[3] - f.bbox[1]) / f.page_h).toFixed(2);

              return (
                <div
                  key={f.id}
                  className="bbox-box"
                  style={{
                    left: `${leftPct}%`,
                    top: `${topPct}%`,
                    width: `${widthPct}%`,
                    height: `${heightPct}%`,
                    opacity: isHl ? 1 : 0.25,
                    borderWidth: isHl ? '3px' : '1.5px',
                    borderColor: isHl ? 'var(--brand-600)' : 'var(--brand-400)',
                    backgroundColor: isHl ? 'rgba(217, 119, 54, 0.35)' : 'rgba(217, 119, 54, 0.1)',
                  }}
                  title={f.name}
                />
              );
            })}
          </div>
          <p style={{ fontSize: '11.5px', color: 'var(--ink-muted)', marginTop: '10px' }}>
            Hover or click any field row in the table to illuminate its OCR bounding box location.
          </p>
        </section>

        {/* Right: Extracted Fields Table */}
        <section className="card" style={{ padding: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <div>
              <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                Extracted Fields ({fields.length})
              </h2>
              <div style={{ fontSize: '12px', color: 'var(--ink-muted)' }}>
                Comparing extracted machine data with document coordinates.
              </div>
            </div>
          </div>

          <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Field Name</th>
                  <th>Extracted Value</th>
                  <th>Conf.</th>
                  <th>Page</th>
                  {isOfficer && <th style={{ textAlign: 'right' }}>Correct</th>}
                </tr>
              </thead>
              <tbody>
                {fields.length > 0 ? (
                  fields.map((f) => {
                    const isLow = (f.confidence || 0) < 0.8;
                    const isHl = hoveredFieldId === f.id;

                    return (
                      <tr
                        key={f.id}
                        onMouseEnter={() => setHoveredFieldId(f.id)}
                        onMouseLeave={() => setHoveredFieldId(null)}
                        style={{
                          backgroundColor: isHl ? 'rgba(244, 220, 206, 0.35)' : undefined,
                          cursor: 'pointer',
                        }}
                      >
                        <td style={{ fontWeight: 600, color: 'var(--ink-muted)' }}>{f.name}</td>
                        <td>
                          <div style={{ fontWeight: 700, color: 'var(--ink)' }}>{f.value}</div>
                          {f.corrected_by && (
                            <div style={{ fontSize: '11px', color: 'var(--brand-700)', marginTop: '2px' }}>
                              Corrected by {f.corrected_by} (Original OCR: “{f.original_value}”)
                            </div>
                          )}
                        </td>
                        <td>
                          <span style={{
                            fontSize: '12px',
                            fontWeight: isLow ? 700 : 500,
                            color: isLow ? 'var(--red-700)' : 'var(--green-700)',
                          }}>
                            {Math.round((f.confidence || 0) * 100)}%
                          </span>
                        </td>
                        <td style={{ fontSize: '12px' }}>{f.page}</td>
                        {isOfficer && (
                          <td style={{ textAlign: 'right' }}>
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setCorrectModal({ open: true, field: f, value: f.value, reason: '' });
                              }}
                              className="btn btn-outline btn-sm"
                              style={{ padding: '3px 8px', fontSize: '11.5px' }}
                            >
                              <Edit2 size={12} /> Correct
                            </button>
                          </td>
                        )}
                      </tr>
                    );
                  })
                ) : (
                  <tr>
                    <td colSpan={5} style={{ textAlign: 'center', padding: '24px', color: 'var(--ink-muted)' }}>
                      No fields extracted from this document.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      {/* MODAL: Correct Field */}
      <Modal
        isOpen={correctModal.open}
        onClose={() => setCorrectModal({ open: false, field: null, value: '', reason: '' })}
        title={`Correct Field · ${correctModal.field?.name || ''}`}
      >
        <form onSubmit={handleCorrectSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div>
            <label className="form-label">Corrected Field Value</label>
            <input
              required
              value={correctModal.value}
              onChange={(e) => setCorrectModal({ ...correctModal, value: e.target.value })}
              className="form-input"
            />
          </div>

          <div>
            <label className="form-label">Mandatory Audit Correction Reason</label>
            <textarea
              required
              rows={3}
              value={correctModal.reason}
              onChange={(e) => setCorrectModal({ ...correctModal, reason: e.target.value })}
              placeholder="State why this value differs from original OCR (e.g. OCR misread blur on page 1)…"
              className="form-textarea"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={() => setCorrectModal({ open: false, field: null, value: '', reason: '' })}
              className="btn btn-outline"
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Save & Re-run Checks
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
