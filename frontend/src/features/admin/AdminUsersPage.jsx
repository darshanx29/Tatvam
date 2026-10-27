import React, { useState, useEffect } from 'react';
import { api } from '../../api';
import { Modal } from '../../components/ui/Modal';
import { Users, UserPlus, Key, ShieldAlert, CheckCircle } from 'lucide-react';

export function AdminUsersPage({ onNavigate }) {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionMsg, setActionMsg] = useState('');

  // New user form state
  const [newEmail, setNewEmail] = useState('');
  const [newName, setNewName] = useState('');
  const [newRole, setNewRole] = useState('scrutiny_officer');
  const [newInstId, setNewInstId] = useState('');
  const [newPassword, setNewPassword] = useState('');

  // Password modal
  const [pwModal, setPwModal] = useState({ open: false, user: null, password: '', error: '' });

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const res = await api.getUsers();
      setUsers(res.users || []);
      setRoles(res.roles || {});
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load user list');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e) => {
    e.preventDefault();
    setError('');
    setActionMsg('');
    try {
      await api.createUser({
        email: newEmail,
        name: newName,
        role: newRole,
        institution_id: newInstId,
        password: newPassword,
      });
      setNewEmail('');
      setNewName('');
      setNewPassword('');
      setNewInstId('');
      fetchUsers();
      setActionMsg(`User ${newEmail} created successfully.`);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleToggleUser = async (user) => {
    try {
      await api.toggleUser(user.id);
      fetchUsers();
      setActionMsg(`Access for ${user.email} updated.`);
    } catch (err) {
      setError(err.message);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setPwModal(prev => ({ ...prev, error: '' }));
    try {
      await api.resetPassword(pwModal.user.id, pwModal.password);
      setPwModal({ open: false, user: null, password: '', error: '' });
      setActionMsg(`Password for ${pwModal.user.email} reset. Existing sessions revoked.`);
    } catch (err) {
      setPwModal(prev => ({ ...prev, error: err.message }));
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div>
        <span className="eyebrow">Identity & Access Management</span>
        <h1 className="font-editorial" style={{ fontSize: '2.4rem', fontWeight: 800, marginTop: '4px' }}>
          Users & Access Control
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--ink-muted)' }}>
          Manage regulatory scrutiny officers, verification agents, system administrators, and institution credentials.
        </p>
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

      {error && (
        <div style={{
          padding: '10px 16px',
          backgroundColor: 'var(--red-50)',
          border: '1px solid var(--red-border)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--red-700)',
          fontSize: '13.5px',
          fontWeight: 600,
        }}>
          {error}
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
        {/* Left: Users Directory */}
        <div style={{ flex: '2', minWidth: '0' }}>
          <section className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '18px 22px', borderBottom: '1px solid var(--border-main)' }}>
              <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700 }}>
                Active Accounts ({users.length})
              </h2>
            </div>

            <div className="table-container" style={{ border: 'none', borderRadius: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>User / Email</th>
                    <th>Role</th>
                    <th>Institution</th>
                    <th>Status</th>
                    <th style={{ textAlign: 'right' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {users.length > 0 ? (
                    users.map((u) => (
                      <tr key={u.id} style={{ opacity: u.active ? 1 : 0.6 }}>
                        <td style={{ fontWeight: 700 }}>
                          <div style={{ color: 'var(--ink)' }}>{u.email}</div>
                          <div style={{ fontSize: '12px', color: 'var(--ink-muted)', fontWeight: 400 }}>{u.name}</div>
                        </td>
                        <td style={{ fontSize: '12.5px' }}>{u.role_label}</td>
                        <td style={{ fontSize: '12px' }}>{u.institution_id || '—'}</td>
                        <td>
                          <span className={`badge ${u.active ? 'badge-green' : 'badge-slate'}`}>
                            {u.active ? 'Active' : 'Disabled'}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                            <button
                              onClick={() => handleToggleUser(u)}
                              className="btn btn-outline btn-sm"
                              style={{ padding: '3px 8px', fontSize: '11px' }}
                            >
                              {u.active ? 'Revoke' : 'Enable'}
                            </button>
                            <button
                              onClick={() => setPwModal({ open: true, user: u, password: '', error: '' })}
                              className="btn btn-secondary btn-sm"
                              style={{ padding: '3px 8px', fontSize: '11px' }}
                            >
                              <Key size={11} /> Reset
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} style={{ textAlign: 'center', padding: '28px', color: 'var(--ink-muted)' }}>
                        No user accounts found.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        {/* Right: Add New User Form */}
        <div style={{ flex: '1', minWidth: '280px' }}>
          <section className="card" style={{ padding: '24px' }}>
            <h2 className="font-editorial" style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '16px' }}>
              Create New User
            </h2>

            <form onSubmit={handleCreateUser} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div>
                <label className="form-label">Email Address</label>
                <input
                  type="email"
                  required
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="e.g. officer2@demo.com"
                  className="form-input"
                />
              </div>

              <div>
                <label className="form-label">Full Name</label>
                <input
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="Dr. S. Sharma"
                  className="form-input"
                />
              </div>

              <div>
                <label className="form-label">System Role</label>
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="form-select"
                >
                  {Object.entries(roles).map(([val, label]) => (
                    <option key={val} value={val}>{label}</option>
                  ))}
                </select>
              </div>

              {newRole === 'institution_admin' && (
                <div>
                  <label className="form-label">Institution ID</label>
                  <input
                    required
                    value={newInstId}
                    onChange={(e) => setNewInstId(e.target.value)}
                    placeholder="e.g. 1-1001"
                    className="form-input"
                  />
                </div>
              )}

              <div>
                <label className="form-label">Temporary Password</label>
                <input
                  type="password"
                  required
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Min 10 chars, uppercase, lowercase, digit"
                  className="form-input"
                />
                <span style={{ fontSize: '11px', color: 'var(--ink-muted)', marginTop: '4px', display: 'block' }}>
                  Policy: At least 10 chars, upper & lower case, at least one digit.
                </span>
              </div>

              <button type="submit" className="btn btn-primary" style={{ marginTop: '8px' }}>
                <UserPlus size={16} /> Create User
              </button>
            </form>
          </section>
        </div>
      </div>

      {/* MODAL: Password Reset */}
      <Modal
        isOpen={pwModal.open}
        onClose={() => setPwModal({ open: false, user: null, password: '', error: '' })}
        title={`Reset Password · ${pwModal.user?.email || ''}`}
      >
        <form onSubmit={handleResetPassword} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {pwModal.error && (
            <div style={{
              padding: '10px 14px',
              backgroundColor: 'var(--red-50)',
              border: '1px solid var(--red-border)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--red-700)',
              fontSize: '12.5px',
            }}>
              {pwModal.error}
            </div>
          )}

          <div>
            <label className="form-label">New Password</label>
            <input
              type="password"
              required
              value={pwModal.password}
              onChange={(e) => setPwModal({ ...pwModal, password: e.target.value })}
              placeholder="Min 10 characters (upper, lower, digit)"
              className="form-input"
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '10px' }}>
            <button
              type="button"
              onClick={() => setPwModal({ open: false, user: null, password: '', error: '' })}
              className="btn btn-outline"
            >
              Cancel
            </button>
            <button type="submit" className="btn btn-primary">
              Update Password
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
