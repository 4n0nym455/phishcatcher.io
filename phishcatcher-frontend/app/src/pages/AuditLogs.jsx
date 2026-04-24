/**
 * AuditLogs.jsx
 * Admin page: security event log with filters and load-more.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { Clock, Loader2, Activity, X, Download, ChevronDown, ChevronRight, User, Globe, AlertCircle, Hash } from 'lucide-react';
import { toast } from 'sonner';
import { adminApi } from '@/lib/api';

const PAGE_SIZE = 50;

const ACTION_COLORS = {
  LOGIN: 'var(--brand)',
  PASSWORD: 'var(--threat)',
  MFA: 'var(--brand)',
  USER_UPDATE: 'var(--brand)',
  REGISTER: 'var(--brand)',
  PROVIDER: 'var(--success)',
  ANALYSIS: 'var(--brand)',
  ADMIN: 'var(--warning)',
};

const ACTION_LABELS = {
  LOGIN: 'Login',
  PASSWORD: 'Password Change',
  MFA: 'MFA',
  USER_UPDATE: 'User Update',
  REGISTER: 'Registration',
  PROVIDER: 'Provider',
  ANALYSIS: 'Analysis',
  ADMIN: 'Admin',
};

const ACTION_TO_CATEGORY = {
  'LOGIN': ['login', 'logout', 'token', 'login_success', 'login_failure'],
  'PASSWORD': ['password', 'password_changed', 'password_reset'],
  'MFA': ['mfa', 'otp', 'mfa_enabled', 'mfa_disabled', 'otp_sent', 'otp_verified'],
  'USER_UPDATE': ['user_updated', 'user_created', 'user_deleted', 'admin_user_updated', 'admin_user_created'],
  'REGISTER': ['register', 'registered', 'email_verified', 'user_registered'],
  'PROVIDER': ['provider_connected', 'provider_disconnected', 'provider_sync'],
  'ANALYSIS': ['analysis_created', 'analysis_started', 'analysis_completed', 'analysis_failed', 'analysis_deleted', 'report_downloaded'],
  'ADMIN': ['admin_user_created', 'admin_user_updated', 'admin_user_deleted', 'system_setting_changed'],
};

const ACTION_FILTER_VALUES = {
  LOGIN: ['login', 'logout', 'token_refresh', 'token_revoked', 'login_success', 'login_failure', 'login_attempt'],
  PASSWORD: ['password_changed', 'password_reset_requested', 'password_reset_completed'],
  MFA: ['mfa_enabled', 'mfa_disabled', 'mfa_setup_initiated', 'mfa_challenge', 'mfa_success', 'mfa_failure', 'otp_sent', 'otp_verified', 'otp_failed', 'mfa_required', 'mfa_backup_code_used'],
  USER_UPDATE: ['user_updated', 'user_created', 'user_deleted', 'admin_user_created', 'admin_user_updated', 'admin_user_deleted'],
  REGISTER: ['user_registered', 'email_verified'],
  PROVIDER: ['provider_connected', 'provider_disconnected', 'provider_sync_started', 'provider_sync_completed', 'provider_sync_failed'],
  ANALYSIS: ['analysis_created', 'analysis_started', 'analysis_completed', 'analysis_failed', 'analysis_deleted', 'report_downloaded'],
  ADMIN: ['admin_user_created', 'admin_user_updated', 'admin_user_deleted', 'system_setting_changed'],
};

function getActionCategory(action) {
  if (!action) return null;
  const a = action.toLowerCase();
  if (a.includes('login') || a.includes('logout') || a.includes('token')) return 'LOGIN';
  if (a.includes('password')) return 'PASSWORD';
  if (a.includes('mfa') || a.includes('otp')) return 'MFA';
  if (a.includes('admin')) return 'ADMIN';
  if (a.includes('user') && (a.includes('update') || a.includes('created') || a.includes('deleted'))) return 'USER_UPDATE';
  if (a.includes('register') || a.includes('verified')) return 'REGISTER';
  if (a.includes('provider')) return 'PROVIDER';
  if (a.includes('analysis') || a.includes('report')) return 'ANALYSIS';
  return null;
}

function getBackendActions(category) {
  if (!category) return undefined;
  const actions = ACTION_FILTER_VALUES[category];
  return actions ? actions.join(',') : undefined;
}

function getTodayStr() {
  try {
    return new Date().toISOString().split('T')[0];
  } catch {
    return '';
  }
}

function isValidDate(dateStr) {
  if (!dateStr) return false;
  const today = new Date().toISOString().split('T')[0];
  return dateStr <= today;
}

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}

function getResultValue(log) {
  const val = log.status ?? '';
  if (val === 'success') return 'Success';
  if (val === 'failure') return 'Failed';
  return val || '—';
}

function getResultClass(log) {
  const val = log.status ?? '';
  if (val === 'success') return 'badge badge-success';
  if (val === 'failure') return 'badge badge-danger';
  return '';
}

function getStatusValue(log) {
  const action = (log.action ?? '').toLowerCase();
  if (action.includes('locked') || action.includes('disabled')) return 'Disabled';
  if (action.includes('unlocked') || action.includes('enabled')) return 'Enabled';
  return '—';
}

function getStatusClass(log) {
  const action = (log.action ?? '').toLowerCase();
  if (action.includes('locked') || action.includes('disabled')) return 'badge badge-danger';
  if (action.includes('unlocked') || action.includes('enabled')) return 'badge badge-success';
  return '';
}

export default function AuditLogs() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [days, setDays] = useState(7);
  const [customDate, setCustomDate] = useState(false);
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [action, setAction] = useState('');
  const [status, setStatus] = useState('');
  const [resourceType, setResourceType] = useState('');
  const [email, setEmail] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [exportStartDate, setExportStartDate] = useState('');
  const [exportEndDate, setExportEndDate] = useState('');
  const [expandedRow, setExpandedRow] = useState(null);

  const load = useCallback(async (pg = 1, reset = true) => {
    setLoading(true);
    try {
      const params = {
        page: pg,
        pageSize: PAGE_SIZE,
        action: action ? getBackendActions(action) : undefined,
        status: status || undefined,
        userEmail: email || undefined,
        resourceType: resourceType || undefined,
      };

      if (customDate) {
        if (startDate) params.startDate = startDate;
        if (endDate) params.endDate = endDate;
      } else {
        params.days = days;
      }

      const res = await adminApi.getAuditLogs(params);
      const list = res.logs ?? res.items ?? (Array.isArray(res) ? res : []);
      setLogs(prev => reset ? list : [...prev, ...list]);
      setHasMore(list.length === PAGE_SIZE);
      setPage(pg);
    } catch (err) {
      toast.error(err.message ?? 'Failed to load audit logs');
    }
    finally { setLoading(false); }
  }, [days, action, status, resourceType, email, customDate, startDate, endDate]);

  useEffect(() => { load(1, true); }, [days, action, status, resourceType, email, customDate, startDate, endDate]);

  const handleDateTypeChange = (useCustom) => {
    setCustomDate(useCustom);
    if (!useCustom) {
      setStartDate('');
      setEndDate('');
    } else {
      const today = new Date().toISOString().split('T')[0];
      const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      setStartDate(weekAgo);
      setEndDate(today);
    }
  };

  const handleToggleExpand = (logId) => {
    setExpandedRow(expandedRow === logId ? null : logId);
  };

  const stats = (() => {
    const total = logs.length;
    const successes = logs.filter(l => l.status === 'success').length;
    const failures = logs.filter(l => l.status === 'failure').length;
    const uniqueUsers = new Set(logs.map(l => l.user_email).filter(Boolean)).size;
    const successRate = total > 0 ? Math.round((successes / total) * 100) : 0;
    return { total, successes, failures, uniqueUsers, successRate };
  })();

  const handleExportLogs = async () => {
    setExporting(true);
    try {
      const blob = await adminApi.exportAuditLogsReport({
        startDate: exportStartDate || undefined,
        endDate: exportEndDate || undefined,
        action: action ? getBackendActions(action) : undefined,
        status: status || undefined,
        userEmail: email || undefined,
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `audit_log_report_${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Report downloaded successfully');
    } catch (err) {
      toast.error(err.message ?? 'Failed to export report');
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="page-title">Audit Logs</h1>
          <p className="page-subtitle">Security event history</p>
        </div>
        <div className="flex flex-wrap items-end gap-2">
          <div>
            <label className="form-label">Start Date</label>
            <input
              type="date"
              value={exportStartDate}
              max={getTodayStr()}
              onChange={e => {
                const val = e.target.value;
                setExportStartDate(val);
                if (exportEndDate && val > exportEndDate) setExportEndDate(val);
              }}
              className="input-base w-auto"
            />
          </div>
          <div>
            <label className="form-label">End Date</label>
            <input
              type="date"
              value={exportEndDate}
              min={exportStartDate}
              max={getTodayStr()}
              onChange={e => setExportEndDate(e.target.value)}
              className="input-base w-auto"
            />
          </div>
          <button
            onClick={handleExportLogs}
            disabled={exporting}
            className="btn-secondary h-9 px-3 flex items-center gap-1.5"
          >
            {exporting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            <span>Export PDF</span>
          </button>
        </div>
      </div>

      {/* Summary Stats Cards */}
      {!loading && logs.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
          <div className="rounded-xl p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>Total Events</p>
            <p className="text-2xl font-700" style={{ color: 'var(--brand)' }}>{stats.total.toLocaleString()}</p>
          </div>
          <div className="rounded-xl p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>Success Rate</p>
            <p className="text-2xl font-700" style={{ color: 'var(--success)' }}>{stats.successRate}%</p>
          </div>
          <div className="rounded-xl p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>Failed</p>
            <p className="text-2xl font-700" style={{ color: 'var(--danger)' }}>{stats.failures}</p>
          </div>
          <div className="rounded-xl p-4" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
            <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>Unique Users</p>
            <p className="text-2xl font-700" style={{ color: 'var(--text-secondary)' }}>{stats.uniqueUsers}</p>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        {/* Date Type Toggle */}
        <div className="flex items-center gap-2">
          <label className={`text-xs cursor-pointer px-2 py-1 rounded ${!customDate ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-elevated)]'}`}>
            <input type="radio" name="dateType" checked={!customDate} onChange={() => handleDateTypeChange(false)} className="hidden" />
            Quick
          </label>
          <label className={`text-xs cursor-pointer px-2 py-1 rounded ${customDate ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-elevated)]'}`}>
            <input type="radio" name="dateType" checked={customDate} onChange={() => handleDateTypeChange(true)} className="hidden" />
            Custom
          </label>
        </div>

        {/* Days Select (only when not custom) */}
        {!customDate && (
          <div>
            <label className="form-label">Time range</label>
            <select value={days} onChange={e => setDays(Number(e.target.value))} className="input-base w-auto">
              {[1, 7, 14, 30, 90].map(d => (
                <option key={d} value={d}>Last {d} day{d !== 1 ? 's' : ''}</option>
              ))}
            </select>
          </div>
        )}

        {/* Custom Date Range (only when custom) */}
        {customDate && (
          <>
            <div>
              <label className="form-label">From</label>
              <input
                type="date"
                value={startDate}
                max={getTodayStr()}
                onChange={e => {
                  const val = e.target.value;
                  if (isValidDate(val)) {
                    setStartDate(val);
                    if (endDate && val > endDate) setEndDate(val);
                  }
                }}
                className="input-base w-auto"
              />
            </div>
            <div>
              <label className="form-label">To</label>
              <input
                type="date"
                value={endDate}
                min={startDate}
                max={getTodayStr()}
                onChange={e => {
                  const val = e.target.value;
                  if (isValidDate(val)) {
                    setEndDate(val);
                  }
                }}
                className="input-base w-auto"
              />
            </div>
          </>
        )}

        {/* Email Filter */}
        <div>
          <label className="form-label">Email</label>
          <input
            type="text"
            placeholder="Filter by email..."
            value={email}
            onChange={e => setEmail(e.target.value)}
            className="input-base w-auto min-w-[160px]"
          />
        </div>

        {/* Action Filter */}
        <div>
          <label className="form-label">Action</label>
          <select value={action} onChange={e => setAction(e.target.value)} className="input-base w-auto">
            <option value="">All</option>
            {Object.keys(ACTION_LABELS).map(a => (
              <option key={a} value={a}>{ACTION_LABELS[a]}</option>
            ))}
          </select>
        </div>

        {/* Status Filter */}
        <div>
          <label className="form-label">Status</label>
          <select value={status} onChange={e => setStatus(e.target.value)} className="input-base w-auto">
            <option value="">All</option>
            <option value="success">Success</option>
            <option value="failure">Failed</option>
          </select>
        </div>

        {/* Resource Filter */}
        <div>
          <label className="form-label">Resource</label>
          <select value={resourceType} onChange={e => setResourceType(e.target.value)} className="input-base w-auto">
            <option value="">All</option>
            <option value="user">User</option>
            <option value="analysis">Analysis</option>
            <option value="settings">Settings</option>
            <option value="provider">Provider</option>
          </select>
        </div>
      </div>

      {/* Clear Filters */}
      {(email || action || status || resourceType || customDate || startDate || endDate) && (
        <div className="mb-4">
          <button
            onClick={() => { setEmail(''); setAction(''); setStatus(''); setResourceType(''); setCustomDate(false); setDays(7); setStartDate(''); setEndDate(''); }}
            className="text-xs flex items-center gap-1"
            style={{ color: 'var(--text-muted)' }}
          >
            <X className="w-3 h-3" /> Clear filters
          </button>
        </div>
      )}

      {/* Pagination info */}
      {!loading && logs.length > 0 && (
        <p className="text-xs mb-3" style={{ color: 'var(--text-muted)' }}>
          Showing {logs.length} log{logs.length !== 1 ? 's' : ''}
          {hasMore && ' (load more below)'}
        </p>
      )}

      <div className="rounded-2xl overflow-hidden"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        {loading && logs.length === 0 ? (
          <div className="p-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading audit logs…</p>
          </div>
        ) : logs.length === 0 ? (
          <div className="p-12 text-center">
            <Activity className="w-10 h-10 mx-auto mb-4 opacity-25" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No audit logs found for this filter.</p>
          </div>
        ) : (
          <>
            <table className="table-base">
              <thead>
                <tr>
                  <th className="w-10"></th>
                  <th className="hidden lg:table-cell">Time</th>
                  <th>User</th>
                  <th>Action</th>
                  <th className="hidden md:table-cell">IP Address</th>
                  <th className="hidden sm:table-cell">Resource</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <React.Fragment key={log.id ?? `${log.user_id}-${log.created_at}`}>
                    <tr 
                      onClick={() => handleToggleExpand(log.id)}
                      className="cursor-pointer hover:opacity-80 transition-opacity"
                    >
                      <td className="text-center">
                        {expandedRow === log.id ? (
                          <ChevronDown className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                        ) : (
                          <ChevronRight className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                        )}
                      </td>
                      <td className="hidden lg:table-cell">
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                          {fmtDate(log.created_at)}
                        </span>
                      </td>
                      <td>
                        <p className="text-xs truncate max-w-[140px]" style={{ color: 'var(--text-secondary)' }}>
                          {log.user_email ?? log.user_id ?? '—'}
                        </p>
                      </td>
                      <td>
                        <span
                          className="text-xs font-600"
                          style={{ color: ACTION_COLORS[getActionCategory(log.action)] ?? 'var(--text-secondary)' }}
                        >
                          {ACTION_LABELS[getActionCategory(log.action)] || log.action?.replace(/_/g, ' ') || '—'}
                        </span>
                      </td>
                      <td className="hidden md:table-cell">
                        <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                          {log.ip_address ?? '—'}
                        </span>
                      </td>
                      <td className="hidden sm:table-cell">
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                          {log.resource_type ?? '—'}
                        </span>
                      </td>
                      <td>
                        <span className={getResultClass(log)}>
                          {getResultValue(log)}
                        </span>
                      </td>
                    </tr>
                    {expandedRow === log.id && (
                      <tr>
                        <td colSpan={7} className="p-0">
                          <div 
                            className="p-4 grid gap-3"
                            style={{ 
                              background: 'var(--bg-elevated)', 
                              borderTop: '1px solid var(--border)' 
                            }}
                          >
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                              {log.user_agent && (
                                <div>
                                  <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>
                                    <User className="w-3 h-3 inline mr-1" />User Agent
                                  </p>
                                  <p className="text-xs font-mono break-all" style={{ color: 'var(--text-secondary)' }}>
                                    {log.user_agent.length > 200 ? log.user_agent.slice(0, 200) + '...' : log.user_agent}
                                  </p>
                                </div>
                              )}
                              {log.request_method && log.request_path && (
                                <div>
                                  <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>
                                    <Globe className="w-3 h-3 inline mr-1" />Request
                                  </p>
                                  <p className="text-xs font-mono" style={{ color: 'var(--text-secondary)' }}>
                                    <span className="font-600">{log.request_method}</span> {log.request_path}
                                  </p>
                                </div>
                              )}
                              <div>
                                <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>
                                  <Hash className="w-3 h-3 inline mr-1" />Status Code
                                </p>
                                <span 
                                  className="text-xs font-600 px-2 py-0.5 rounded"
                                  style={{ 
                                    background: log.status_code >= 400 ? 'var(--danger-dim)' : 'var(--success-dim)',
                                    color: log.status_code >= 400 ? 'var(--danger)' : 'var(--success)'
                                  }}
                                >
                                  {log.status_code ?? log.status ?? '—'}
                                </span>
                              </div>
                              {log.error_message && (
                                <div>
                                  <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>
                                    <AlertCircle className="w-3 h-3 inline mr-1" />Error
                                  </p>
                                  <p className="text-xs" style={{ color: 'var(--danger)' }}>
                                    {log.error_message}
                                  </p>
                                </div>
                              )}
                              {log.correlation_id && (
                                <div>
                                  <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>Correlation ID</p>
                                  <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                                    {log.correlation_id}
                                  </p>
                                </div>
                              )}
                              {log.resource_id && (
                                <div>
                                  <p className="text-xs font-500 mb-1" style={{ color: 'var(--text-muted)' }}>Resource ID</p>
                                  <p className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                                    {log.resource_id}
                                  </p>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))}
              </tbody>
            </table>

            {hasMore && (
              <div className="p-4 text-center" style={{ borderTop: '1px solid var(--border)' }}>
                <button
                  onClick={() => load(page + 1, false)}
                  disabled={loading}
                  className="btn-ghost text-sm h-9 px-6"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Load more'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}