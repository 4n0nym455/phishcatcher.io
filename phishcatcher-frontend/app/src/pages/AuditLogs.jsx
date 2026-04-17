/**
 * AuditLogs.jsx
 * Admin page: security event log with filters and load-more.
 */

import { useState, useEffect, useCallback } from 'react';
import { Clock, Loader2, Activity, X } from 'lucide-react';
import { toast } from 'sonner';
import { adminApi } from '@/lib/api';

const PAGE_SIZE = 50;

const ACTION_COLORS = {
  LOGIN: 'var(--brand)',
  PASSWORD: 'var(--threat)',
  MFA: 'var(--brand)',
  USER_UPDATE: 'var(--brand)',
  REGISTER: 'var(--brand)',
};

const ACTION_LABELS = {
  LOGIN: 'Login',
  PASSWORD: 'Password Change',
  MFA: 'MFA',
  USER_UPDATE: 'User Update',
  REGISTER: 'Account Registration',
};

const ACTION_TO_CATEGORY = {
  'LOGIN': ['login', 'logout', 'token', 'login_success', 'login_failure'],
  'PASSWORD': ['password', 'password_changed', 'password_reset'],
  'MFA': ['mfa', 'otp', 'mfa_enabled', 'mfa_disabled', 'otp_sent', 'otp_verified'],
  'USER_UPDATE': ['user_updated', 'user_created', 'user_deleted', 'admin_user_updated', 'admin_user_created'],
  'REGISTER': ['register', 'registered', 'email_verified', 'user_registered'],
};

const ACTION_FILTER_VALUES = {
  LOGIN: ['login', 'logout', 'token_refresh', 'token_revoked', 'login_success', 'login_failure'],
  PASSWORD: ['password_changed', 'password_reset_requested', 'password_reset_completed'],
  MFA: ['mfa_enabled', 'mfa_disabled', 'mfa_setup_initiated', 'mfa_challenge', 'mfa_success', 'mfa_failure', 'otp_sent', 'otp_verified', 'otp_failed', 'mfa_required', 'mfa_backup_code_used'],
  USER_UPDATE: ['user_updated', 'user_created', 'user_deleted', 'admin_user_created', 'admin_user_updated', 'admin_user_deleted'],
  REGISTER: ['user_registered', 'email_verified'],
};

function getActionCategory(action) {
  if (!action) return null;
  const a = action.toLowerCase();
  if (a.includes('login') || a.includes('logout') || a.includes('token')) return 'LOGIN';
  if (a.includes('password')) return 'PASSWORD';
  if (a.includes('mfa') || a.includes('otp')) return 'MFA';
  if (a.includes('user') && (a.includes('update') || a.includes('created') || a.includes('deleted'))) return 'USER_UPDATE';
  if (a.includes('register') || a.includes('verified')) return 'REGISTER';
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
  const [result, setResult] = useState('');
  const [status, setStatus] = useState('');
  const [email, setEmail] = useState('');
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const load = useCallback(async (pg = 1, reset = true) => {
    setLoading(true);
    try {
      const params = {
        page: pg,
        pageSize: PAGE_SIZE,
        action: action ? getBackendActions(action) : undefined,
        status: status || result || undefined,
        userEmail: email || undefined,
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
  }, [days, action, result, status, email, customDate, startDate, endDate]);

  useEffect(() => { load(1, true); }, [days, action, result, status, email, customDate, startDate, endDate]);

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

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Audit Logs</h1>
        <p className="page-subtitle">Security event history</p>
      </div>

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

        {/* Result Filter */}
        <div>
          <label className="form-label">Result</label>
          <select value={result} onChange={e => setResult(e.target.value)} className="input-base w-auto">
            <option value="">All</option>
            <option value="success">Success</option>
            <option value="failure">Failed</option>
          </select>
        </div>

        {/* Status Filter */}
        <div>
          <label className="form-label">Status</label>
          <select value={status} onChange={e => setStatus(e.target.value)} className="input-base w-auto">
            <option value="">All</option>
            <option value="enabled">Enabled</option>
            <option value="disabled">Disabled</option>
          </select>
        </div>
      </div>

      {/* Clear Filters */}
      {(email || action || result || status || customDate || startDate || endDate) && (
        <div className="mb-4">
          <button
            onClick={() => { setEmail(''); setAction(''); setResult(''); setStatus(''); setCustomDate(false); setDays(7); setStartDate(''); setEndDate(''); }}
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
                  <th>Action</th>
                  <th className="hidden sm:table-cell">User</th>
                  <th>Result</th>
                  <th>Status</th>
                  <th className="hidden lg:table-cell">Time</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id ?? `${log.user_id}-${log.created_at}`}>
                    <td>
                      <span
                        className="text-xs font-600"
                        style={{ color: ACTION_COLORS[getActionCategory(log.action)] ?? 'var(--text-secondary)' }}
                      >
                        {/* Show raw action if category mapping fails */}
                        {ACTION_LABELS[getActionCategory(log.action)] || log.action?.replace(/_/g, ' ') || '—'}
                      </span>
                    </td>
                    <td className="hidden sm:table-cell">
                      <p className="text-xs truncate max-w-[160px]" style={{ color: 'var(--text-secondary)' }}>
                        {log.user_email ?? log.user_id ?? '—'}
                      </p>
                    </td>
                    <td>
                      <span className={getResultClass(log)}>
                        {getResultValue(log)}
                      </span>
                    </td>
                    <td>
                      <span className={getStatusClass(log)}>
                        {getStatusValue(log)}
                      </span>
                    </td>
                    <td className="hidden lg:table-cell">
                      <span className="text-xs flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                        <Clock className="w-3 h-3" />
                        {fmtDate(log.created_at)}
                      </span>
                    </td>
                  </tr>
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