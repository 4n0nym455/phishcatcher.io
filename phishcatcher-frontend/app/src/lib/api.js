const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

// Token management
export const getTokens = () => ({
  accessToken: localStorage.getItem('access_token'),
  refreshToken: localStorage.getItem('refresh_token'),
});

export const setTokens = (tokens) => {
  if (typeof tokens === 'object' && tokens.access_token && tokens.refresh_token) {
    localStorage.setItem('access_token', tokens.access_token);
    localStorage.setItem('refresh_token', tokens.refresh_token);
  } else if (typeof tokens === 'string' && arguments.length === 2) {
    // Legacy support for (accessToken, refreshToken) signature
    localStorage.setItem('access_token', tokens);
    localStorage.setItem('refresh_token', arguments[1]);
  }
};

// Alias for storeTokens to match import in ActivateAccountPage
export const storeTokens = setTokens;

export const clearTokens = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  localStorage.removeItem('phishcatcher_email');
  localStorage.removeItem('phishcatcher_role');
  localStorage.removeItem('phishcatcher_auth');
};

// Generic API fetch with auth
async function apiFetch(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const { accessToken } = getTokens();
  
  const config = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(accessToken && { 'Authorization': `Bearer ${accessToken}` }),
      ...options.headers,
    },
  };

  try {
    const response = await fetch(url, config);
    
    // Handle 401 - try to refresh token
    if (response.status === 401 && !endpoint.includes('/auth/refresh')) {
      console.log('Token expired, attempting refresh for:', endpoint);
      const refreshed = await authApi.refresh();
      if (refreshed) {
        console.log('Token refreshed successfully, retrying request');
        return apiFetch(endpoint, options); // Retry with new token
      } else {
        console.log('Token refresh failed, clearing session');
        clearTokens();
        window.location.href = '/login';
        throw new Error('Session expired');
      }
    }
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      console.error('API Error Response:', error);
      
      // Show detailed validation errors - handle different error structures
      if (error.errors && Array.isArray(error.errors)) {
        const errorDetails = error.errors.map(err => {
          if (typeof err === 'string') return err;
          if (err.field && err.message) return `${err.field}: ${err.message}`;
          if (err.loc && err.msg) return `${err.loc.join('.')}: ${err.msg}`;
          return JSON.stringify(err);
        }).join(', ');
        throw new Error(`Validation error: ${errorDetails}`);
      }
      
      throw new Error(error.detail || `HTTP ${response.status}: ${JSON.stringify(error)}`);
    }
    
    return response.status === 204 ? null : await response.json();
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}

// Auth API endpoints
export const authApi = {
  // Step 1: Login - send credentials, get OTP response
  login: async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(error.detail);
    }
    
    return response.json();
  },

  // Step 2: Verify OTP - get tokens
  verifyOTP: (email, otp) => 
    apiFetch('/auth/verify-otp', {
      method: 'POST',
      body: JSON.stringify({ email, otp }),
    }),

  // Register new user
  register: (userData) => 
    apiFetch('/auth/register', {
      method: 'POST',
      body: JSON.stringify({
        email: userData.email,
        password: userData.password,
        confirm_password: userData.confirmPassword || userData.password,
        full_name: userData.fullName,
        company: userData.company || undefined,
        accept_terms_and_privacy: userData.acceptTermsAndPrivacy || false,
      }),
    }),

  // Get current user info
  getMe: () => apiFetch('/auth/me'),

  // Update profile (authenticated)
  updateProfile: (profileData) => 
    apiFetch('/auth/me', {
      method: 'PUT',
      body: JSON.stringify(profileData),
    }),

  // Delete account (authenticated)
  deleteAccount: (password) => 
    apiFetch('/auth/me/delete', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({ password }),
    }),

  // Logout
  logout: () => apiFetch('/auth/logout', { method: 'POST' }),

  // Change password
  changePassword: (currentPassword, newPassword, confirmPassword) => {
    console.log('Password change data:', {
      current_password: currentPassword,
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    
    // Send passwords directly as backend expects
    const requestData = {
      current_password: currentPassword,
      new_password: newPassword,
    };
    
    console.log('Request data:', JSON.stringify(requestData));
    
    return apiFetch('/auth/me/password', {
      method: 'PUT',
      body: JSON.stringify(requestData),
    });
  },

  // Gmail Integration
  gmail: {
    // Get Gmail auth URL
    getAuthUrl: () => apiFetch('/gmail/auth/url'),
    
    // Get Gmail connection status
    getStatus: () => apiFetch('/gmail/status'),
    
    // Disconnect Gmail
    disconnect: () => apiFetch('/gmail/disconnect', { method: 'POST' }),
    
    // Scan recent emails
    scanEmails: (maxResults = 10) => 
      apiFetch(`/gmail/scan?max_results=${maxResults}`, { method: 'POST' }),
    
    // Toggle auto-scan
    toggleAutoScan: (enabled) => 
      apiFetch('/gmail/auto-scan', {
        method: 'PUT',
        body: JSON.stringify({ enabled }),
      }),
    
    // Mark email as safe
    markSafe: (messageId) => 
      apiFetch(`/gmail/emails/${messageId}/safe`, { method: 'POST' }),
    
    // Report email as phishing
    reportPhishing: (messageId) => 
      apiFetch(`/gmail/emails/${messageId}/phishing`, { method: 'POST' }),
  },

  // Refresh access token
  refresh: async () => {
    const { refreshToken } = getTokens();
    if (!refreshToken) {
      console.log('No refresh token available');
      return false;
    }
    
    try {
      console.log('Attempting to refresh token');
      const response = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      
      if (response.ok) {
        const data = await response.json();
        console.log('Token refresh successful');
        setTokens({
          access_token: data.access_token,
          refresh_token: data.refresh_token
        });
        return true;
      } else {
        console.log('Token refresh failed with status:', response.status);
        return false;
      }
    } catch (error) {
      console.log('Token refresh error:', error);
      return false;
    }
  },

  // Google OAuth URL
  getGoogleAuthUrl: () => apiFetch('/auth/google/url'),

  // Google OAuth callback
  googleCallback: (code, state) => {
    return apiFetch('/auth/google/callback', {
      method: 'POST',
      body: JSON.stringify({ code, state }),
    });
  },

  // Activation endpoints
  verifyActivationToken: (token, email) => {
    return apiFetch('/activate/verify-token', {
      method: 'POST',
      body: JSON.stringify({ token, email }),
    });
  },

  completeActivation: (data) => {
    return apiFetch('/activate/complete', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  },

  resendActivation: (email) => {
    return apiFetch('/activate/resend', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  resendOTP: (email) => {
    return apiFetch('/auth/resend-otp', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  },

  checkActivationStatus: (email) => {
    return apiFetch(`/activate/status/${email}`);
  },

  // Server-side OAuth
  getOAuthTokens: (tokenId) => {
    return apiFetch(`/server/oauth/tokens/${tokenId}`);
  },

  // MFA verification
  verifyMFA: (mfaSessionToken, code) => 
    apiFetch('/auth/mfa/verify', {
      method: 'POST',
      body: JSON.stringify({ mfa_session_token: mfaSessionToken, code }),
    }),

  // Forgot password
  forgotPassword: (email) => 
    apiFetch('/auth/forgot-password', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  // Reset password
  resetPassword: (token, newPassword) => 
    apiFetch('/auth/reset-password', {
      method: 'POST',
      body: JSON.stringify({ token, new_password: newPassword }),
    }),

  // Change password (authenticated)
  changePassword: (currentPassword, newPassword) => 
    apiFetch('/auth/me/password', {
      method: 'PUT',
      body: JSON.stringify({ 
        current_password: currentPassword, 
        new_password: newPassword 
      }),
    }),
  
  // MFA endpoints
  setupMfa: (data) => 
    apiFetch('/auth/mfa/setup', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  enableMfa: (data) => 
    apiFetch('/auth/mfa/enable', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  disableMfa: (data) => 
    apiFetch('/auth/mfa/disable', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  getMfaStatus: () => 
    apiFetch('/auth/mfa/status'),
  
  verifyBackupCode: (backupCode) => 
    apiFetch('/auth/mfa/verify-backup-code', {
      method: 'POST',
      body: JSON.stringify({ backup_code: backupCode }),
    }),
};

// Admin API
export const adminApi = {
  // Get system statistics
  getStats: () => apiFetch('/admin/stats'),
  
  // List users
  listUsers: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('page_size', params.pageSize);
    if (params.search) query.append('search', params.search);
    if (params.isActive !== undefined) query.append('is_active', params.isActive);
    return apiFetch(`/admin/users?${query.toString()}`);
  },
  
  // Get user details
  getUser: (userId) => apiFetch(`/admin/users/${userId}`),
  
  // Update user
  updateUser: (userId, data) => 
    apiFetch(`/admin/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  // Delete user
  deleteUser: (userId, password) => 
    apiFetch(`/admin/users/${userId}`, {
      method: 'DELETE',
      body: JSON.stringify(password),
    }),
  
  // Get audit logs
  getAuditLogs: (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('page_size', params.pageSize);
    if (params.action) query.append('action', params.action);
    if (params.status) query.append('status', params.status);
    if (params.userId) query.append('user_id', params.userId);
    if (params.days) query.append('days', params.days);
    return apiFetch(`/admin/audit-logs?${query.toString()}`);
  },
  
  // Get model info
  getModelInfo: () => apiFetch('/admin/model-info'),
  
  // Retrain model
  retrainModel: () => 
    apiFetch('/admin/model/retrain', { method: 'POST' }),
};

// Analysis API endpoints
export const analysisApi = {
  // Upload email file for analysis
  uploadEmail: async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/analysis/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${getTokens().accessToken}`,
      },
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `Upload failed: ${response.status}`);
    }
    
    return response.json();
  },
  
  // Get analysis history
  getHistory: async (params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.append('page', params.page);
    if (params.pageSize) query.append('page_size', params.pageSize);
    if (params.status) query.append('status', params.status);
    if (params.threatCategory) query.append('threat_category', params.threatCategory);
    
    return apiFetch(`/analysis/history?${query.toString()}`);
  },
  
  // Get analysis details
  getAnalysis: (analysisId) => apiFetch(`/analysis/${analysisId}`),
  
  // Get analysis status
  getStatus: (analysisId) => apiFetch(`/analysis/${analysisId}/status`),
  
  // Delete analysis
  deleteAnalysis: (analysisId) => 
    apiFetch(`/analysis/${analysisId}`, { method: 'DELETE' }),
  
  // Download report
  downloadReport: (analysisId, format = 'pdf') => 
    apiFetch(`/analysis/${analysisId}/download?format=${format}`),
  
  // Get weekly report
  getWeeklyReport: (weekStart) => {
    const query = weekStart ? `?week_start=${weekStart}` : '';
    return apiFetch(`/analysis/reports/weekly${query}`);
  },
};

export default authApi;