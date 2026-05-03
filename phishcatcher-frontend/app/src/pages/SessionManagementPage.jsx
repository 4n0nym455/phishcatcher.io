/**
 * SessionManagementPage.jsx
 * Admin-only: view and manage ALL users' active sessions with expandable details.
 */

import { useState, useEffect } from 'react';
import {
  Clock, Shield, Monitor, Smartphone, Globe, Trash2,
  Loader2, CheckCircle, AlertTriangle, RefreshCw,
  ChevronDown, ChevronUp, MapPin, Info,
} from 'lucide-react';
import { toast } from 'sonner';
import { sessionApi } from '@/lib/api';

function formatDuration(seconds) {
  if (seconds == null) return 'N/A';
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

function formatTime(isoString) {
  if (!isoString) return 'N/A';
  return new Date(isoString).toLocaleString();
}

function getDeviceIcon(userAgent) {
  if (!userAgent) return Monitor;
  const ua = userAgent.toLowerCase();
  if (/mobile|android|iphone|ipad|ipod/i.test(ua)) return Smartphone;
  return Monitor;
}

function getBrowserInfo(userAgent) {
  if (!userAgent) return 'Unknown';
  if (userAgent.includes('Firefox')) return 'Firefox';
  if (userAgent.includes('Edg')) return 'Edge';
  if (userAgent.includes('Chrome')) return 'Chrome';
  if (userAgent.includes('Safari')) return 'Safari';
  return 'Browser';
}

function getOSInfo(userAgent) {
  if (!userAgent) return 'Unknown';
  if (userAgent.includes('Windows')) return 'Windows';
  if (userAgent.includes('Mac OS')) return 'macOS';
  if (userAgent.includes('Linux')) return 'Linux';
  if (userAgent.includes('Android')) return 'Android';
  if (userAgent.includes('iOS') || userAgent.includes('iPhone') || userAgent.includes('iPad')) return 'iOS';
  return 'OS';
}

export default function SessionManagementPage() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedSession, setExpandedSession] = useState(null);
  const [revoking, setRevoking] = useState(null);
  const [cleaning, setCleaning] = useState(false);
  const [userFilter, setUserFilter] = useState('all');

  useEffect(() => {
    fetchSessions();
    const interval = setInterval(fetchSessions, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchSessions = async () => {
    try {
      const data = await sessionApi.listAll();
      setSessions(data.sessions || []);
      setError(null);
    } catch (err) {
      console.error('SessionManagementPage: fetchSessions error', err);
      setError(err.message);
      toast.error(`Failed to load sessions: ${err.message}`);
      setSessions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (userId, sessionId) => {
    setRevoking(sessionId);
    try {
      await sessionApi.revoke(userId, sessionId);
      toast.success('Session revoked');
      if (expandedSession === sessionId) setExpandedSession(null);
      await fetchSessions();
    } catch (err) {
      toast.error(err.message ?? 'Failed to revoke session');
    } finally {
      setRevoking(null);
    }
  };

  const handleCleanup = async () => {
    setCleaning(true);
    try {
      await sessionApi.cleanup();
      toast.success('Expired sessions cleaned');
      await fetchSessions();
    } catch (err) {
      toast.error(err.message ?? 'Failed to cleanup');
    } finally {
      setCleaning(false);
    }
  };

  const uniqueUsers = [...new Set(sessions.map(s => s.user_email))];
  const filteredSessions = userFilter === 'all'
    ? sessions
    : sessions.filter(s => s.user_email === userFilter);

  const groupedByUser = filteredSessions.reduce((acc, s) => {
    if (!acc[s.user_email]) acc[s.user_email] = [];
    acc[s.user_email].push(s);
    return acc;
  }, {});

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--brand)' }} />
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold" style={{ color: 'var(--text-primary)' }}>Active Sessions</h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{sessions.length} session{sessions.length !== 1 ? 's' : ''} across {uniqueUsers.length} user{uniqueUsers.length !== 1 ? 's' : ''}</p>
        </div>
        <button onClick={handleCleanup} disabled={cleaning}
          className="btn-ghost h-9 px-3 text-sm flex items-center gap-2">
          {cleaning ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
          Cleanup
        </button>
      </div>

      {error && (
        <div className="card p-4" style={{ border: '1px solid var(--danger-dim)' }}>
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 shrink-0" style={{ color: 'var(--danger)' }} />
            <div>
              <p className="text-sm font-500" style={{ color: 'var(--danger)' }}>Failed to load sessions</p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{error}</p>
            </div>
            <button onClick={fetchSessions} className="btn-ghost text-xs ml-auto">Retry</button>
          </div>
        </div>
      )}

      {uniqueUsers.length > 1 && (
        <div className="card p-4">
          <div className="flex items-center gap-3">
            <label className="text-sm" style={{ color: 'var(--text-muted)' }}>Filter by user:</label>
            <select value={userFilter} onChange={e => setUserFilter(e.target.value)}
              className="input h-9 text-sm">
              <option value="all">All users ({sessions.length})</option>
              {uniqueUsers.map(email => (
                <option key={email} value={email}>
                  {email} ({sessions.filter(s => s.user_email === email).length})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {filteredSessions.length === 0 ? (
        <div className="card p-12 text-center">
          <Shield className="w-10 h-10 mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No active sessions</p>
        </div>
      ) : (
        <div className="space-y-6">
          {Object.entries(groupedByUser).map(([email, userSessions]) => (
            <div key={email} className="space-y-3">
              <div className="flex items-center gap-3 px-1">
                <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                  style={{ background: 'var(--bg-elevated)' }}>
                  <span className="text-sm font-bold" style={{ color: 'var(--brand)' }}>{email[0].toUpperCase()}</span>
                </div>
                <div>
                  <h3 className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>{email}</h3>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{userSessions.length} active session{userSessions.length !== 1 ? 's' : ''}</p>
                </div>
              </div>

              <div className="space-y-3 pl-0 sm:pl-11">
                {userSessions.map((s) => {
                  const DeviceIcon = getDeviceIcon(s.user_agent);
                  const browser = getBrowserInfo(s.user_agent);
                  const os = getOSInfo(s.user_agent);
                  const isExpiringSoon = s.session_ttl_seconds != null && s.session_ttl_seconds < 600;
                  const isExpanded = expandedSession === s.session_id;
                  const isCurrent = s.is_current === true;

                  return (
                    <div key={s.session_id}
                      className="card overflow-hidden"
                      style={{ border: isCurrent ? '1px solid var(--brand)' : isExpanded ? '1px solid var(--brand-dim)' : '1px solid var(--border)' }}>
                      
                      {/* Session Header */}
                      <div className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
                            style={{ background: isCurrent ? 'var(--brand-dim)' : isExpiringSoon ? 'var(--warning-dim)' : 'var(--success-dim)' }}>
                            {isCurrent ? <Monitor className="w-5 h-5" style={{ color: 'var(--brand)' }} /> : isExpiringSoon ? <AlertTriangle className="w-5 h-5" style={{ color: 'var(--warning)' }} /> : <CheckCircle className="w-5 h-5" style={{ color: 'var(--success)' }} />}
                          </div>
                          
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-2">
                              <DeviceIcon className="w-4 h-4" style={{ color: 'var(--text-secondary)' }} />
                              <span className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>{os} · {browser}</span>
                              {isCurrent
                                ? <span className="px-2 py-0.5 rounded text-xs font-600" style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>This device</span>
                                : <span className="px-2 py-0.5 rounded text-xs font-500" style={{ background: 'var(--success-dim)', color: 'var(--success)' }}>Active</span>}
                            </div>
                            
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                              <div className="flex items-center gap-1.5">
                                <Clock className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                                <span style={{ color: 'var(--text-secondary)' }}>{formatDuration(s.session_ttl_seconds)} left</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <MapPin className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                                <span className="font-mono" style={{ color: 'var(--text-secondary)' }} title={s.ip_address}>{s.ip_address}</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <Clock className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                                <span style={{ color: 'var(--text-secondary)' }}>Age: {s.session_age_minutes}m</span>
                              </div>
                              <div className="flex items-center gap-1.5">
                                <Info className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                                <span style={{ color: 'var(--text-secondary)' }}>Active {s.last_activity_minutes_ago ?? s.session_age_minutes}m ago</span>
                              </div>
                            </div>
                          </div>

                          <div className="flex items-center gap-2 shrink-0">
                            {!isCurrent && (
                              <button onClick={() => handleRevoke(s.user_id, s.session_id)}
                                disabled={revoking === s.session_id}
                                className="btn-ghost h-8 w-8 p-0"
                                style={{ color: 'var(--danger)' }}
                                title="Revoke session">
                                {revoking === s.session_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                              </button>
                            )}
                            <button onClick={() => setExpandedSession(isExpanded ? null : s.session_id)}
                              className="btn-ghost h-8 w-8 p-0"
                              style={{ color: 'var(--text-muted)' }}>
                              {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                            </button>
                          </div>
                        </div>
                      </div>

                      {/* Expandable Details */}
                      {isExpanded && (
                        <div className="px-4 pb-4 border-t" style={{ borderTopColor: 'var(--border)' }}>
                          <div className="space-y-4 pt-4">
                            <div>
                              <h4 className="text-sm font-600 mb-3" style={{ color: 'var(--text-secondary)' }}>Session Information</h4>
                              <div className="space-y-2 text-xs">
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><Shield className="w-3.5 h-3.5" />Session ID</span>
                                  <span className="font-mono text-right max-w-[60%] truncate" style={{ color: 'var(--text-secondary)' }} title={s.session_id}>{s.session_id}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><MapPin className="w-3.5 h-3.5" />IP Address</span>
                                  <span className="font-mono" style={{ color: 'var(--text-secondary)' }}>{s.ip_address}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><Globe className="w-3.5 h-3.5" />User Agent</span>
                                  <span className="text-right max-w-[60%] truncate" style={{ color: 'var(--text-secondary)' }} title={s.user_agent}>{s.user_agent}</span>
                                </div>
                              </div>
                            </div>

                            <div className="pt-3 border-t" style={{ borderTopColor: 'var(--border)' }}>
                              <h4 className="text-sm font-600 mb-3" style={{ color: 'var(--text-secondary)' }}>Timestamps</h4>
                              <div className="space-y-2 text-xs">
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><Clock className="w-3.5 h-3.5" />Login Time</span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{formatTime(s.login_time)}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><Clock className="w-3.5 h-3.5" />Last Activity</span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{formatTime(s.last_activity)}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><Clock className="w-3.5 h-3.5" />Created At</span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{formatTime(s.created_at)}</span>
                                </div>
                              </div>
                            </div>

                            <div className="pt-3 border-t" style={{ borderTopColor: 'var(--border)' }}>
                              <h4 className="text-sm font-600 mb-3" style={{ color: 'var(--text-secondary)' }}>Limits</h4>
                              <div className="space-y-2 text-xs">
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><Clock className="w-3.5 h-3.5" />Session Duration</span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{formatDuration(s.session_ttl_seconds)}</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><Clock className="w-3.5 h-3.5" />Max Duration</span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{s.max_duration_minutes}m</span>
                                </div>
                                <div className="flex justify-between items-center">
                                  <span className="flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}><Clock className="w-3.5 h-3.5" />Session Age</span>
                                  <span style={{ color: 'var(--text-secondary)' }}>{s.session_age_minutes}m</span>
                                </div>
                              </div>
                            </div>

                            {!isCurrent && (
                              <div className="pt-3 border-t flex gap-2" style={{ borderTopColor: 'var(--border)' }}>
                                <button onClick={() => handleRevoke(s.user_id, s.session_id)}
                                  disabled={revoking === s.session_id}
                                className="btn-ghost text-sm"
                                style={{ color: 'var(--danger)', border: '1px solid var(--danger-dim)' }}>
                                {revoking === s.session_id ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                                Revoke This Session
                              </button>
                            </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
