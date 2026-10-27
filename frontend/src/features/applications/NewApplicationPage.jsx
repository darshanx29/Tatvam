import React, { useState } from 'react';
import { api } from '../../api';
import { ArrowLeft, Upload, ArrowRight, Save, AlertCircle } from 'lucide-react';

export function NewApplicationPage({ onNavigate }) {
  const [formData, setFormData] = useState({
    category: 'EoA',
    academic_year: '2026-27',
    programme: 'B.Tech Computer Engineering',
    intake: '120',
    institution_type: 'Private',
  });
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleFileChange = (e) => {
    setFiles(Array.from(e.target.files));
  };

  const handleSubmit = async (actionType) => {
    setError('');
    setLoading(true);
    try {
      const data = new FormData();
      data.append('category', formData.category);
      data.append('academic_year', formData.academic_year);
      data.append('programme', formData.programme);
      data.append('intake', formData.intake);
      data.append('institution_type', formData.institution_type);
      data.append('action', actionType);

      for (let f of files) {
        data.append('files', f);
      }

      const res = await api.createApplication(data);
      if (res.application && res.application.id) {
        onNavigate(`/applications/${res.application.id}`);
      } else {
        onNavigate('/dashboard');
      }
    } catch (err) {
      setError(err.message || 'Failed to submit application');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: '780px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div>
        <button
          onClick={() => onNavigate('/dashboard')}
          className="btn btn-outline btn-sm"
          style={{ marginBottom: '16px' }}
        >
          <ArrowLeft size={15} /> Back to Dashboard
        </button>
        <span className="eyebrow">Application Intake</span>
        <h1 className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '4px' }}>
          New Application
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>
          Save a draft to continue later, or submit to trigger automated multimodal OCR and rule checks immediately.
        </p>
      </div>

      {error && (
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '12px 16px',
          borderRadius: 'var(--radius-md)',
          backgroundColor: 'var(--red-50)',
          border: '1px solid var(--red-border)',
          color: 'var(--red-700)',
          fontSize: '13.5px',
          fontWeight: 600,
        }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      <div className="card" style={{ padding: '32px' }}>
        <form onSubmit={(e) => e.preventDefault()} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div>
            <label className="form-label">Application Category</label>
            <select name="category" value={formData.category} onChange={handleChange} className="form-select">
              <option value="EoA">EoA (Extension of Approval)</option>
              <option value="New Institution">New Institution</option>
              <option value="Increase in Intake">Increase in Intake</option>
              <option value="New Programme">New Programme</option>
              <option value="Change of Site">Change of Site</option>
            </select>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
            <div>
              <label className="form-label">Academic Year</label>
              <input
                name="academic_year"
                value={formData.academic_year}
                onChange={handleChange}
                required
                className="form-input"
              />
            </div>
            <div>
              <label className="form-label">Institution Type</label>
              <select name="institution_type" value={formData.institution_type} onChange={handleChange} className="form-select">
                <option value="Private">Private</option>
                <option value="Government">Government</option>
                <option value="Autonomous">Autonomous</option>
                <option value="University">University</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '16px' }}>
            <div>
              <label className="form-label">Proposed Programme</label>
              <input
                name="programme"
                value={formData.programme}
                onChange={handleChange}
                required
                placeholder="e.g. B.Tech Computer Engineering"
                className="form-input"
              />
            </div>
            <div>
              <label className="form-label">Sanctioned / Proposed Intake</label>
              <input
                name="intake"
                type="number"
                value={formData.intake}
                onChange={handleChange}
                required
                placeholder="e.g. 120"
                className="form-input"
              />
            </div>
          </div>

          <div>
            <label className="form-label">Supporting Evidence & Documents (PDF, JPEG, PNG)</label>
            <div style={{
              border: '2px dashed var(--brand-300)',
              backgroundColor: 'var(--brand-50)',
              borderRadius: 'var(--radius-lg)',
              padding: '28px',
              textAlign: 'center',
            }}>
              <Upload size={32} style={{ color: 'var(--brand-600)', marginBottom: '8px' }} />
              <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink)' }}>
                Drag and drop files here, or browse
              </div>
              <div style={{ fontSize: '12px', color: 'var(--ink-muted)', marginTop: '4px', marginBottom: '14px' }}>
                Accreditation certificate, land NOC, building plan, faculty affidavits
              </div>
              <input
                type="file"
                multiple
                accept=".pdf,.jpg,.jpeg,.png"
                onChange={handleFileChange}
                style={{ fontSize: '13px' }}
              />
              {files.length > 0 && (
                <div style={{ marginTop: '14px', fontSize: '12.5px', color: 'var(--brand-700)', fontWeight: 600 }}>
                  Selected {files.length} file(s): {files.map(f => f.name).join(', ')}
                </div>
              )}
            </div>
          </div>

          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px', paddingTop: '10px' }}>
            <button
              type="button"
              disabled={loading}
              onClick={() => handleSubmit('submit')}
              className="btn btn-primary"
              style={{ padding: '12px 24px', fontSize: '14.5px' }}
            >
              Submit & Run Preliminary Checks <ArrowRight size={16} />
            </button>
            <button
              type="button"
              disabled={loading}
              onClick={() => handleSubmit('draft')}
              className="btn btn-secondary"
              style={{ padding: '12px 22px', fontSize: '14.5px' }}
            >
              <Save size={16} /> Save as Draft
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
