/**
 * AdminDashboard.jsx
 * Platform overview for admins: stats, model info, quick links to admin sub-pages.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Users, Activity, Shield, BarChart3, RefreshCw,
  Loader2, AlertTriangle, Database, TrendingUp,
} from 'lucide-react';
import { toast } from 'sonner';
import { adminApi } from '@/lib/api';

export default function AdminDashboardPage() {
  const [stats,      setStats]     = useState(null);
  const [model,      setModel]     = useState(null);
  const [loading,    setLoading]   = useState(true);
  const [retraining, setRetraining]= useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const [s, m] = await Promise.allSettled([adminApi.getStats(), adminApi.getModelInfo()]);
        if (s.status === 'fulfilled') setStats(s.value);
        if (m.status === 'fulfilled') setModel(m.value);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleRetrain = async () => {
    if (!window.confirm('Start model retraining? This may take several minutes.')) return;
    setRetraining(true);
    try {
      await adminApi.retrainModel();
      toast.success('Retraining started!');
      // Refresh model info
      const m = await adminApi.getModelInfo();
      setModel(m);
    } catch (err) {
      toast.error(err.message ?? 'Failed to start retraining');
    } finally {
      setRetraining(false);
    }
  };

  return (
    <div className="space-y-7 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="page-title">Admin Dashboard</h1>
          <p className="page-subtitle">Platform overview and management</p>
        </div>
        <div className="flex gap-2 flex-wrap self-start sm:self-auto">
          <Link to="/admin/users"      className="btn-ghost h-9 px-3 text-sm"><Users    className="w-4 h-4" />Users</Link>
          <Link to="/admin/audit-logs" className="btn-ghost h-9 px-3 text-sm"><Activity className="w-4 h-4" />Audit logs</Link>
          <Link to="/admin/model"      className="btn-ghost h-9 px-3 text-sm"><Database className="w-4 h-4" />AI Model</Link>
        </div>
      </div>

      {loading ? (
        <div className="text-center py-16">
          <Loader2 className="w-7 h-7 animate-spin mx-auto" style={{ color: 'var(--brand)' }} />
        </div>
      ) : (
        <>
          {/* Platform stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { icon: Users,         label: 'Total users',        value: stats?.total_users       ?? '—', color: 'var(--brand)',   bg: 'var(--brand-dim)'   },
              { icon: Activity,      label: 'Active (30d)',       value: stats?.active_users      ?? '—', color: 'var(--success)', bg: 'var(--success-dim)' },
              { icon: Shield,        label: 'Emails analyzed',    value: stats?.total_emails      ?? '—', color: 'var(--threat)',  bg: 'var(--threat-dim)'  },
              { icon: AlertTriangle, label: 'Threats detected',   value: stats?.threats_detected  ?? '—', color: 'var(--danger)',  bg: 'var(--danger-dim)'  },
            ].map(s => (
              <div key={s.label} className="stat-card">
                <div className="w-10 h-10 rounded-xl flex items-center justify-center mb-3"
                  style={{ background: s.bg, color: s.color }}>
                  <s.icon className="w-5 h-5" />
                </div>
                <div className="stat-value">{s.value}</div>
                <div className="stat-label">{s.label}</div>
              </div>
            ))}
          </div>

          {/* Additional stats row */}
          {stats && (
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: 'Avg threat score',   value: stats.avg_threat_score   ? `${stats.avg_threat_score.toFixed(1)}` : '—' },
                { label: 'Pending activations', value: stats.pending_activations ?? '—' },
                { label: 'Gmail connections',   value: stats.gmail_connections   ?? '—' },
                { label: 'MFA enabled users',   value: stats.mfa_enabled_users   ?? '—' },
              ].map(s => (
                <div key={s.label} className="card p-4 text-center">
                  <div className="font-heading font-700 text-xl mb-0.5" style={{ color: 'var(--text-primary)' }}>{s.value}</div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.label}</div>
                </div>
              ))}
            </div>
          )}

          {/* Model info */}
          {model && (
            <div className="card p-6">
              <div className="flex items-center justify-between mb-5">
                <h2 className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
                  AI Model Status
                </h2>
                <button onClick={handleRetrain} disabled={retraining} className="btn-ghost h-9 px-3 text-sm">
                  {retraining
                    ? <><Loader2 className="w-3.5 h-3.5 animate-spin" />Retraining…</>
                    : <><RefreshCw className="w-3.5 h-3.5" />Retrain</>
                  }
                </button>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { label: 'Version',   value: model.version ?? '—' },
                  { label: 'Accuracy',  value: model.accuracy ? `${(model.accuracy * 100).toFixed(1)}%` : '—' },
                  { label: 'Status',    value: model.status ?? 'active' },
                  { label: 'Trained',   value: model.last_trained ? new Date(model.last_trained).toLocaleDateString() : '—' },
                ].map(s => (
                  <div key={s.label} className="rounded-xl p-3"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                    <p className="text-xs font-700 uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
                    <p className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>{s.value}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Quick access cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {[
              { to: '/admin/users',      icon: Users,     title: 'User Management', desc: 'View, edit, activate or deactivate user accounts', color: 'var(--brand)',   bg: 'var(--brand-dim)'   },
              { to: '/admin/audit-logs', icon: Activity,  title: 'Audit Logs',      desc: 'Security event history with filters and search',   color: 'var(--threat)',  bg: 'var(--threat-dim)'  },
              { to: '/admin/model',      icon: Database,  title: 'Model Management',desc: 'AI model stats, performance metrics, and retraining', color: 'var(--success)', bg: 'var(--success-dim)' },
            ].map(item => (
              <Link key={item.to} to={item.to}
                className="card p-5 flex gap-4 items-start group theme-transition"
                style={{ textDecoration: 'none' }}>
                <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
                  style={{ background: item.bg, color: item.color }}>
                  <item.icon className="w-5 h-5" />
                </div>
                <div>
                  <p className="font-600 text-sm mb-0.5" style={{ color: 'var(--text-primary)' }}>{item.title}</p>
                  <p className="text-xs leading-snug" style={{ color: 'var(--text-muted)' }}>{item.desc}</p>
                </div>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}