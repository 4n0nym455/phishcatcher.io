/**
 * PhishCatcher API Client
 *
 * Single source of truth for all HTTP calls.
 * Auth token lifecycle:
 *   - access_token  : short-lived (default 120 min), sent in Authorization header
 *   - refresh_token : long-lived (7 days), used once to rotate the pair
 *
 * Token storage uses only two keys:
 *   localStorage.access_token
 *   localStorage.refresh_token
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// ─── Token helpers ────────────────────────────────────────────────────────────

export const getTokens = () => ({
  accessToken:  localStorage.getItem('access_token')  ?? null,
  refreshToken: localStorage.getItem('refresh_token') ?? null,
});

export const storeTokens = ({ access_token, refresh_token }) => {
  if (access_token)  localStorage.setItem('access_token',  access_token);
  if (refresh_token) localStorage.setItem('refresh_token', refresh_token);
};

/** Alias kept for backward compatibility with ActivateAccountPage */
export const setTokens = storeTokens;

export const clearTokens = () => {
  ['access_token', 'refresh_token',
   'phishcatcher_email', 'phishcatcher_role', 'phishcatcher_name',
   'mfa_session_token', 'mfa_user',
   'oauth_state', 'oauth_state_expiry',
  ].forEach(k => localStorage.removeItem(k));
};

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

let _refreshing = null; // singleton promise so concurrent calls don't double-refresh

async function apiFetch(endpoint, options = {}, _retried = false) {
  const url   = `${API_BASE}${endpoint}`;
  const token = getTokens().accessToken;

  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  // Auto-refresh on 401, but never loop
  if (response.status === 401 && !_retried && !endpoint.includes('/auth/refresh')) {
    if (!_refreshing) {
      _refreshing = _doRefresh().finally(() => { _refreshing = null; });
    }
    const refreshed = await _refreshing;
    if (refreshed) return apiFetch(endpoint, options, true);
    clearTokens();
    window.dispatchEvent(new CustomEvent('auth:logout', { detail: 'token_expired' }));
    throw new Error('Session expired. Please log in again.');
  }

  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: `HTTP ${response.status}` }));
    const message = Array.isArray(body.errors)
      ? body.errors.map(e => e.msg ?? e.message ?? JSON.stringify(e)).join('; ')
      : (body.detail ?? `HTTP ${response.status}`);
    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

async function _doRefresh() {
  const { refreshToken } = getTokens();
  if (!refreshToken) return false;
  try {
    const res = await fetch(`${API_BASE}/auth/refresh`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    storeTokens(await res.json());
    return true;
  } catch {
    return false;
  }
}

// ─── Auth API ─────────────────────────────────────────────────────────────────

export const authApi = {
  /**
   * Step 1 – submit credentials → backend sends OTP email.
   * Returns { message, email, mfa_required, mfa_session_token? }
   */
  login: (email, password) => {
    const body = new URLSearchParams({ username: email, password });
    return fetch(`${API_BASE}/auth/login`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    }).then(async res => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Login failed' }));
        throw new Error(err.detail);
      }
      return res.json();
    });
  },

  /**
   * Step 2 – submit OTP → receive tokens (or MFA challenge).
   * Returns OTPVerificationResponse
   */
  verifyOTP: (email, otp) =>
    apiFetch('/auth/verify-otp', {
      method: 'POST',
      body:   JSON.stringify({ email, otp }),
    }),

  /** Resend OTP during the active login window */
  resendOTP: (email) =>
    apiFetch('/auth/resend-otp', {
      method: 'POST',
      body:   JSON.stringify({ email }),
    }),

  /**
   * Step 2b – verify TOTP code when MFA is enabled.
   * mfa_session_token comes from login() or verifyOTP().
   */
  verifyMFA: (mfaSessionToken, code) =>
    apiFetch('/auth/mfa/verify', {
      method: 'POST',
      body:   JSON.stringify({ mfa_session_token: mfaSessionToken, code }),
    }),

  /** Register new user (returns UserResponse). Backend sends activation email. */
  register: ({ email, password, fullName, company, acceptTermsAndPrivacy }) =>
    apiFetch('/auth/register', {
      method: 'POST',
      body:   JSON.stringify({
        email,
        password,
        confirm_password:         password,
        full_name:                fullName,
        company:                  company ?? undefined,
        accept_terms_and_privacy: acceptTermsAndPrivacy,
      }),
    }),

  /** Refresh access + refresh tokens. Called automatically by apiFetch. */
  refresh: () => _doRefresh(),

  /** Invalidate server session + clear local tokens */
  logout: async () => {
    await apiFetch('/auth/logout', { method: 'POST' }).catch(() => {});
  },

  // ── Profile ──────────────────────────────────────────────────────────────

  getMe:          ()     => apiFetch('/auth/me'),
  updateProfile:  (data) => apiFetch('/auth/me', { method: 'PUT', body: JSON.stringify(data) }),
  uploadAvatar: async (file) => {
    const form = new FormData();
    form.append('file', file);
    const { accessToken } = getTokens();
    const res = await fetch(`${API_BASE}/auth/me/avatar`, {
      method: 'POST',
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Avatar upload failed' }));
      throw new Error(err.detail ?? `Avatar upload failed: ${res.status}`);
    }
    return res.json();
  },
  getAvatarUrl: () => apiFetch('/auth/me/avatar'),
  deleteAccount:  (pwd)  => apiFetch('/auth/me/delete', {
    method:  'POST',
    headers: { 'Content-Type': 'application/json' },
    body:    JSON.stringify({ password: pwd }),
  }),

  // ── Password ─────────────────────────────────────────────────────────────

  forgotPassword: (email) =>
    apiFetch('/auth/forgot-password', {
      method: 'POST',
      body:   JSON.stringify({ email }),
    }),

  resetPassword: (token, newPassword) =>
    apiFetch('/auth/reset-password', {
      method: 'POST',
      body:   JSON.stringify({ token, new_password: newPassword }),
    }),

  changePassword: (currentPassword, newPassword) =>
    apiFetch('/auth/me/password', {
      method: 'PUT',
      body:   JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),

  // ── MFA ──────────────────────────────────────────────────────────────────

  getMfaStatus:    ()     => apiFetch('/auth/mfa/status'),
  setupMfa:        (data) => apiFetch('/auth/mfa/setup',  { method: 'POST', body: JSON.stringify(data) }),
  verifyMfaSetup:  (data) => apiFetch('/auth/mfa/verify', { method: 'POST', body: JSON.stringify(data) }),
  enableMfa:       (data) => apiFetch('/auth/mfa/enable',  { method: 'POST', body: JSON.stringify(data) }),
  disableMfa:      (data) => apiFetch('/auth/mfa/disable', { method: 'POST', body: JSON.stringify(data) }),
  verifyBackupCode:(code) => apiFetch('/auth/mfa/verify-backup-code', {
    method: 'POST',
    body:   JSON.stringify({ backup_code: code }),
  }),

  // ── Account activation ────────────────────────────────────────────────────

  verifyActivationToken: (token, email) =>
    apiFetch('/activate/verify-token', {
      method: 'POST',
      body:   JSON.stringify({ token, email }),
    }),

  completeActivation: (data) =>
    apiFetch('/activate/complete', {
      method: 'POST',
      body:   JSON.stringify(data),
    }),

  resendActivation: (email) =>
    apiFetch('/activate/resend', {
      method: 'POST',
      body:   JSON.stringify({ email }),
    }),

  checkActivationStatus: (email) => apiFetch(`/activate/status/${encodeURIComponent(email)}`),

  // ── Google OAuth ──────────────────────────────────────────────────────────

  getGoogleAuthUrl: () => apiFetch('/auth/google/url'),

  /** Exchange authorization code + state for tokens */
  googleCallback: (code, state) =>
    apiFetch('/auth/google/callback', {
      method: 'POST',
      body:   JSON.stringify({ code, state }),
    }),

  /** Retrieve one-time token bundle after server-side OAuth redirect */
  getOAuthTokens: (tokenId) => apiFetch(`/server/oauth/tokens/${tokenId}`),

  // ── Gmail integration ─────────────────────────────────────────────────────

  gmail: {
    getAuthUrl:      ()        => apiFetch('/gmail/auth/url'),
    callback:        (code, state) => apiFetch('/gmail/callback', { method: 'POST', body: JSON.stringify({ code, state }) }),
    getStatus:       ()        => apiFetch('/gmail/status'),
    disconnect:      ()        => apiFetch('/gmail/disconnect', { method: 'POST' }),
    listEmails:      (page = 1, maxResults = 20, q = null) => {
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('max_results', String(maxResults));
      if (q) params.set('q', q);
      return apiFetch(`/gmail/emails?${params}`);
    },
    searchEmails:    (query, page = 1, maxResults = 50) => {
      const params = new URLSearchParams();
      params.set('q', query);
      params.set('page', String(page));
      params.set('max_results', String(maxResults));
      return apiFetch(`/gmail/emails/search?${params}`);
    },
    filterEmails:    (options = {}) => {
      const { filterType, hasAttachments, dateFrom, dateTo, fromAddress, subject, page = 1, maxResults = 50 } = options;
      const params = new URLSearchParams();
      params.set('page', String(page));
      params.set('max_results', String(maxResults));
      if (filterType) params.set('filter_type', filterType);
      if (hasAttachments !== undefined) params.set('has_attachments', String(hasAttachments));
      if (dateFrom) params.set('date_from', dateFrom);
      if (dateTo) params.set('date_to', dateTo);
      if (fromAddress) params.set('from_address', fromAddress);
      if (subject) params.set('subject', subject);
      return apiFetch(`/gmail/emails/filter?${params}`);
    },
    getQueryHelp:    ()        => apiFetch('/gmail/emails/query-builder'),
    queueEmails:     (messageIds) => apiFetch('/gmail/emails/queue', {
      method: 'POST',
      body: JSON.stringify({ message_ids: messageIds }),
    }),
    analyzeEmails:   (messageIds) => apiFetch('/gmail/emails/analyze', {
      method: 'POST',
      body: JSON.stringify({ message_ids: messageIds }),
    }),
    scanEmails:      (n = 10)  => apiFetch(`/gmail/scan?max_results=${n}`, { method: 'POST' }),
    markSafe:        (id) => apiFetch(`/gmail/emails/${id}/safe`,     { method: 'POST' }),
    reportPhishing:  (id) => apiFetch(`/gmail/emails/${id}/phishing`, { method: 'POST' }),
    getQueue:        ()        => apiFetch('/gmail/queue'),
    processQueueItem: (messageId) => apiFetch(`/gmail/queue/${messageId}/process`, { method: 'POST' }),
    deleteQueueItem: (messageId) => apiFetch(`/gmail/queue/${messageId}`, { method: 'DELETE' }),
    clearQueue:      ()        => apiFetch('/gmail/queue/clear', { method: 'POST' }),
  },
};

// ─── Admin API ────────────────────────────────────────────────────────────────

export const adminApi = {
  getStats:    () => apiFetch('/admin/stats'),
  getModelInfo:()  => apiFetch('/admin/model-info'),
  retrainModel:()  => apiFetch('/admin/model/retrain', { method: 'POST' }),
  getAnalytics:(days = 30) => apiFetch(`/admin/analytics?days=${days}`),

  listUsers: ({ page = 1, pageSize = 20, search, isActive, role, sortBy, sortOrder } = {}) => {
    const q = new URLSearchParams({ page, page_size: pageSize });
    if (search   !== undefined) q.set('search',    search);
    if (isActive !== undefined) q.set('is_active', isActive);
    if (role     !== undefined) q.set('role',      role);
    if (sortBy   !== undefined) q.set('sort_by',   sortBy);
    if (sortOrder!== undefined) q.set('sort_order', sortOrder);
    return apiFetch(`/admin/users?${q}`);
  },

  getUser:    (id)         => apiFetch(`/admin/users/${id}`),
  updateUser: (id, data)   => apiFetch(`/admin/users/${id}`, { method: 'PUT',    body: JSON.stringify(data) }),
  deleteUser: (id, payload)=> apiFetch(`/admin/users/${id}`, { method: 'DELETE', body: JSON.stringify(payload) }),

  getAuditLogs: ({ page = 1, pageSize = 50, action, status, days = 7, startDate, endDate, ipAddress, resourceType, userEmail } = {}) => {
    const q = new URLSearchParams({ page, page_size: pageSize, days });
    if (action)       q.set('action', action);
    if (status)       q.set('status', status);
    if (startDate)    q.set('start_date', startDate);
    if (endDate)     q.set('end_date', endDate);
    if (ipAddress)    q.set('ip_address', ipAddress);
    if (resourceType)q.set('resource_type', resourceType);
    if (userEmail)    q.set('user_email', userEmail);
    return apiFetch(`/admin/audit-logs?${q}`);
  },
};

// ─── Analysis API ─────────────────────────────────────────────────────────────

export const analysisApi = {
  uploadEmail: (file, queueOnly = false) => {
    const form = new FormData();
    form.append('file', file);
    const { accessToken } = getTokens();
    const url = queueOnly 
      ? `${API_BASE}/analysis/upload?queue_only=true`
      : `${API_BASE}/analysis/upload`;
    return fetch(url, {
      method:  'POST',
      headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : {},
      body:    form,
    }).then(async res => {
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
        throw new Error(err.detail ?? `Upload failed: ${res.status}`);
      }
      return res.json();
    });
  },

  getHistory: ({ page = 1, pageSize = 20, status, threatCategory } = {}) => {
    const q = new URLSearchParams({ page, page_size: pageSize });
    if (status)        q.set('status',          status);
    if (threatCategory)q.set('threat_category', threatCategory);
    return apiFetch(`/analysis/history?${q}`);
  },

  getAnalysis:  (id) => {
    // Validate ID - accept PostgreSQL UUIDs (with or without dashes) and 32-char hex
    const isValidId = (id) => {
      if (!id || typeof id !== 'string') return false;
      // PostgreSQL UUID: 8-4-4-4-12 format (36 chars)
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      // 32-char hex (UUID without dashes or our custom format)
      const hexRegex = /^[0-9a-f]{32}$/i;
      return uuidRegex.test(id) || hexRegex.test(id);
    };
    if (!id || id === 'None' || id === 'null' || id === 'undefined' || 
        typeof id !== 'string' || id.startsWith('fallback_') || !isValidId(id)) {
      return Promise.reject(new Error('Invalid analysis ID'));
    }
    return apiFetch(`/analysis/${id}`);
  },
  startAnalysis: (id) => {
    const isValidId = (id) => {
      if (!id || typeof id !== 'string') return false;
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      const hexRegex = /^[0-9a-f]{32}$/i;
      return uuidRegex.test(id) || hexRegex.test(id);
    };
    if (!id || id.startsWith('fallback_') || !isValidId(id)) {
      return Promise.reject(new Error('Invalid analysis ID'));
    }
    return apiFetch(`/analysis/${id}/start`, { method: 'POST' });
  },
  getStatus:    (id) => {
    const isValidId = (id) => {
      if (!id || typeof id !== 'string') return false;
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      const hexRegex = /^[0-9a-f]{32}$/i;
      return uuidRegex.test(id) || hexRegex.test(id);
    };
    if (!id || id.startsWith('fallback_') || !isValidId(id)) {
      return Promise.reject(new Error('Invalid analysis ID'));
    }
    return apiFetch(`/analysis/${id}/status`);
  },
  deleteAnalysis:(id) => {
    const isValidId = (id) => {
      if (!id || typeof id !== 'string') return false;
      const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
      const hexRegex = /^[0-9a-f]{32}$/i;
      return uuidRegex.test(id) || hexRegex.test(id);
    };
    if (!id || id.startsWith('fallback_') || !isValidId(id)) {
      return Promise.reject(new Error('Invalid analysis ID'));
    }
    return apiFetch(`/analysis/${id}`, { method: 'DELETE' });
  },
  downloadReport:(id, fmt='pdf') => apiFetch(`/analysis/${id}/download?format=${fmt}`),
  getWeeklyReport:(start) => {
    const q = start ? `?week_start=${start}` : '';
    return apiFetch(`/analysis/reports/weekly${q}`);
  },
};

// ─── ML Prediction API ───────────────────────────────────────────────────────────

export const mlApi = {
  predict: (subject, body) =>
    apiFetch('/ml/predict', {
      method: 'POST',
      body: JSON.stringify({ subject, body }),
    }),

  getModelsStatus: () => apiFetch('/ml/models'),
};

export default authApi;