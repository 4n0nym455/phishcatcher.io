/**
 * AuditLogs.jsx
 * Admin page: security event log with day/action/status filters and load-more.
 */

import { useState, useEffect, useCallback } from 'react';
import { Clock, Loader2, Activity, Filter } from 'lucide-react';
import { adminApi } from '@/lib/api';

const PAGE_SIZE = 50;

const ACTION_COLORS = {
  LOGIN:             'var(--success)',
  LOGOUT:            'var(--text-muted)',
  LOGIN_FAILED:      'var(--danger)',
  OTP_SENT:          'var(--brand)',
  OTP_FAILED:        'var(--danger)',
  MFA_REQUIRED:      'var(--brand)',
  MFA_SUCCESS:       'var(--success)',
  MFA_FAILED:        'var(--danger)',
  MFA_ENABLED:       'var(--success)',
  MFA_DISABLED:      'var(--threat)',
  MFA_BACKUP_CODE_USED: 'var(--threat)',
  MFA_SETUP_INITIATED: 'var(--brand)',
  PASSWORD_CHANGED:  'var(--threat)',
  USER_REGISTERED:   'var(--brand)',
  USER_DELETED:      'var(--danger)',
};

const KNOWN_ACTIONS = Object.keys(ACTION_COLORS);

function fmtDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}

export default function AuditLogs() {
  const [logs,    setLogs]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [days,    setDays]    = useState(7);
  const [action,  setAction]  = useState('');
  const [status,  setStatus]  = useState('');
  const [page,    setPage]    = useState(1);
  const [hasMore, setHasMore] = useState(false);

  const load = useCallback(async (pg = 1, reset = true) => {
    setLoading(true);
    try {
      const res  = await adminApi.getAuditLogs({
        page: pg, pageSize: PAGE_SIZE, days,
        action: action || undefined,
        status: status || undefined,
      });
      const list = res.logs ?? res.items ?? (Array.isArray(res) ? res : []);
      setLogs(prev => reset ? list : [...prev, ...list]);
      setHasMore(list.length === PAGE_SIZE);
      setPage(pg);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, [days, action, status]);

  useEffect(() => { load(1, true); }, [days, action, status]);

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Audit Logs</h1>
        <p className="page-subtitle">Security event history</p>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div>
          <label className="form-label">Time range</label>
          <select value={days} onChange={e => setDays(Number(e.target.value))} className="input-base w-auto">
            {[1, 7, 14, 30, 90].map(d => (
              <option key={d} value={d}>Last {d} day{d !== 1 ? 's' : ''}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="form-label">Action</label>
          <select value={action} onChange={e => setAction(e.target.value)} className="input-base w-auto">
            <option value="">All actions</option>
            {KNOWN_ACTIONS.map(a => (
              <option key={a} value={a}>{a.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </div>
        <div>
          <label className="form-label">Status</label>
          <select value={status} onChange={e => setStatus(e.target.value)} className="input-base w-auto">
            <option value="">All</option>
            <option value="success">Success</option>
            <option value="failure">Failure</option>
          </select>
        </div>
      </div>

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
                  <th>Status</th>
                  <th className="hidden md:table-cell">IP Address</th>
                  <th className="hidden lg:table-cell">Time</th>
                  <th className="hidden xl:table-cell">Details</th>
                </tr>
              </thead>
              <tbody>
                {logs.map(log => (
                  <tr key={log.id ?? `${log.user_id}-${log.created_at}`}>
                    <td>
                      <span
                        className="text-xs font-700 font-mono"
                        style={{ color: ACTION_COLORS[log.action] ?? 'var(--text-secondary)' }}
                      >
                        {(log.action ?? '—').replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="hidden sm:table-cell">
                      <p className="text-xs truncate max-w-[160px]" style={{ color: 'var(--text-secondary)' }}>
                        {log.user_email ?? log.user_id ?? '—'}
                      </p>
                    </td>
                    <td>
                      <span className={log.status === 'success' ? 'badge badge-success' : 'badge badge-danger'}>
                        {log.status ?? '—'}
                      </span>
                    </td>
                    <td className="hidden md:table-cell">
                      <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                        {log.ip_address ?? '—'}
                      </span>
                    </td>
                    <td className="hidden lg:table-cell">
                      <span className="text-xs flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                        <Clock className="w-3 h-3" />
                        {fmtDate(log.created_at)}
                      </span>
                    </td>
                    <td className="hidden xl:table-cell">
                      {log.details && (
                        <span className="text-xs font-mono truncate max-w-[120px] block"
                          style={{ color: 'var(--text-muted)' }}>
                          {typeof log.details === 'string' ? log.details : JSON.stringify(log.details)}
                        </span>
                      )}
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