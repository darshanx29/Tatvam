// ============================================================================
// AICTE SmartVerify REST API Client
// Handles CSRF token, sessions, JSON & Multipart requests
// ============================================================================

let storedCsrf = localStorage.getItem('smartverify_csrf') || '';

export function getCsrfToken() {
  return storedCsrf;
}

export function setCsrfToken(token) {
  if (token) {
    storedCsrf = token;
    localStorage.setItem('smartverify_csrf', token);
  }
}

export async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('/') ? endpoint : `/api/v1/${endpoint}`;
  const headers = options.headers ? { ...options.headers } : {};

  // Attach CSRF token on mutation requests
  if (storedCsrf && ['POST', 'PUT', 'PATCH', 'DELETE'].includes(options.method?.toUpperCase())) {
    headers['X-CSRF-Token'] = storedCsrf;
  }

  // Set application/json content type if sending body and not FormData
  if (options.body && !(options.body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json';
  }

  const res = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',
  });

  const contentType = res.headers.get('content-type') || '';
  let data = null;
  if (contentType.includes('application/json')) {
    data = await res.json();
    if (data && data.csrf_token) {
      setCsrfToken(data.csrf_token);
    }
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const errorMsg = (data && data.error) || (typeof data === 'string' && data) || res.statusText || 'Request failed';
    throw new Error(errorMsg);
  }

  return data;
}

// Auth API
export const api = {
  // Authentication
  async getMe() {
    return apiFetch('/api/v1/me');
  },
  async login(email, password) {
    const res = await apiFetch('/api/v1/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
    if (res.csrf_token) setCsrfToken(res.csrf_token);
    return res;
  },
  async logout() {
    return apiFetch('/api/v1/logout', { method: 'POST' });
  },

  // Dashboard
  async getDashboard(params = {}) {
    const sp = new URLSearchParams();
    if (params.q) sp.set('q', params.q);
    if (params.status) sp.set('status', params.status);
    if (params.page) sp.set('page', params.page);
    const qs = sp.toString() ? `?${sp.toString()}` : '';
    return apiFetch(`/api/v1/dashboard${qs}`);
  },
  async markNotificationsRead() {
    return apiFetch('/api/v1/notifications/read', { method: 'POST' });
  },

  // Applications
  async getApplication(appId) {
    return apiFetch(`/api/v1/applications/${appId}/full`);
  },
  async createApplication(formData) {
    return apiFetch('/api/v1/applications', {
      method: 'POST',
      body: formData, // FormData
    });
  },
  async editApplication(appId, formData) {
    return apiFetch(`/api/v1/applications/${appId}/edit`, {
      method: 'POST',
      body: formData,
    });
  },
  async submitApplication(appId) {
    return apiFetch(`/api/v1/applications/${appId}/submit`, {
      method: 'POST',
    });
  },
  async uploadDocuments(appId, formData) {
    return apiFetch(`/api/v1/applications/${appId}/documents`, {
      method: 'POST',
      body: formData,
    });
  },
  async validateApplication(appId) {
    return apiFetch(`/api/v1/applications/${appId}/validate`, {
      method: 'POST',
    });
  },
  async getStatus(appId) {
    return apiFetch(`/api/v1/applications/${appId}/status`);
  },
  async addObservation(appId, text) {
    return apiFetch(`/api/v1/applications/${appId}/observation`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },
  async setRecommendation(appId, choice, note) {
    return apiFetch(`/api/v1/applications/${appId}/recommendation`, {
      method: 'POST',
      body: JSON.stringify({ choice, note }),
    });
  },
  async closeApplication(appId) {
    return apiFetch(`/api/v1/applications/${appId}/close`, {
      method: 'POST',
    });
  },
  async reverify(appId, documentName) {
    return apiFetch(`/api/v1/applications/${appId}/reverify`, {
      method: 'POST',
      body: JSON.stringify({ document: documentName }),
    });
  },
  async manualVerify(appId, { document, outcome, reference, note }) {
    return apiFetch(`/api/v1/applications/${appId}/manual-verify`, {
      method: 'POST',
      body: JSON.stringify({ document, outcome, reference, note }),
    });
  },
  async getCompliance(appId) {
    return apiFetch(`/api/v1/applications/${appId}/compliance`);
  },
  async getAudit(appId) {
    return apiFetch(`/api/v1/applications/${appId}/audit`);
  },

  // Findings
  async reviewFinding(fid, { action, reason }) {
    return apiFetch(`/api/v1/findings/${fid}/review`, {
      method: 'POST',
      body: JSON.stringify({ action, reason }),
    });
  },
  async respondFinding(fid, text) {
    return apiFetch(`/api/v1/findings/${fid}/respond`, {
      method: 'POST',
      body: JSON.stringify({ text }),
    });
  },

  // Documents
  async getDocument(did) {
    return apiFetch(`/api/v1/documents/${did}`);
  },
  async correctField(fid, { value, reason }) {
    return apiFetch(`/api/v1/fields/${fid}/correct`, {
      method: 'POST',
      body: JSON.stringify({ value, reason }),
    });
  },

  // Admin
  async getRules() {
    return apiFetch('/api/v1/rules');
  },
  async saveRule(ruleId, definition, note) {
    return apiFetch('/api/v1/admin/rules', {
      method: 'POST',
      body: JSON.stringify({ rule_id: ruleId, definition, note }),
    });
  },
  async getUsers() {
    return apiFetch('/api/v1/admin/users');
  },
  async createUser(userData) {
    return apiFetch('/api/v1/admin/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  },
  async toggleUser(uid) {
    return apiFetch(`/api/v1/admin/users/${uid}/toggle`, {
      method: 'POST',
    });
  },
  async resetPassword(uid, password) {
    return apiFetch(`/api/v1/admin/users/${uid}/password`, {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  },
  async getSettings() {
    return apiFetch('/api/v1/admin/settings');
  },
  async saveSettings(settings) {
    return apiFetch('/api/v1/admin/settings', {
      method: 'POST',
      body: JSON.stringify(settings),
    });
  },
  async getSystemAudit() {
    return apiFetch('/api/v1/admin/audit');
  },
  async verifyAuditChain() {
    return apiFetch('/api/v1/admin/audit/verify');
  },
};
