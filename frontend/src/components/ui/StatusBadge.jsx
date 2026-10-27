import React from 'react';

export function StatusBadge({ type = 'app', value }) {
  if (!value) return null;

  const valStr = String(value);

  if (type === 'app') {
    const map = {
      'Preliminary checks complete': 'badge-green',
      'Closed in prototype': 'badge-green',
      'Officer review': 'badge-amber',
      'Action required': 'badge-red',
      'Verification pending': 'badge-sky',
      'Processing': 'badge-sky',
      'Draft': 'badge-slate',
      'Submitted': 'badge-slate',
    };
    const cls = map[valStr] || 'badge-slate';
    return <span className={`badge ${cls}`}>{valStr}</span>;
  }

  if (type === 'severity') {
    const s = valStr.toLowerCase();
    const map = {
      high: 'badge-red',
      medium: 'badge-amber',
      low: 'badge-sky',
    };
    const cls = map[s] || 'badge-slate';
    return <span className={`badge ${cls}`}>{s.charAt(0).toUpperCase() + s.slice(1)}</span>;
  }

  if (type === 'state') {
    const s = valStr.toLowerCase();
    const map = {
      open: 'badge-amber',
      accepted: 'badge-green',
      resolved: 'badge-green',
      dismissed: 'badge-slate',
      escalated: 'badge-red',
      evidence_requested: 'badge-sky',
    };
    const cls = map[s] || 'badge-slate';
    const label = s.replace(/_/g, ' ');
    return <span className={`badge ${cls}`}>{label.charAt(0).toUpperCase() + label.slice(1)}</span>;
  }

  if (type === 'verification') {
    const v = valStr.toLowerCase();
    const map = {
      verified: 'badge-green',
      mismatch_detected: 'badge-red',
      expired: 'badge-red',
      source_unavailable: 'badge-slate',
      manual_review_required: 'badge-amber',
      pending: 'badge-sky',
    };
    const cls = map[v] || 'badge-slate';
    const label = v.replace(/_/g, ' ');
    return <span className={`badge ${cls}`}>{label.charAt(0).toUpperCase() + label.slice(1)}</span>;
  }

  if (type === 'compliance') {
    const c = valStr.toUpperCase();
    const map = {
      PASS: { cls: 'badge-green', label: 'Compliant' },
      FAIL: { cls: 'badge-red', label: 'Deficient' },
      INCONCLUSIVE: { cls: 'badge-amber', label: 'Inconclusive' },
      NOT_APPLICABLE: { cls: 'badge-slate', label: 'Not Applicable' },
    };
    const item = map[c] || { cls: 'badge-slate', label: c };
    return <span className={`badge ${item.cls}`}>{item.label}</span>;
  }

  return <span className="badge badge-slate">{valStr}</span>;
}
