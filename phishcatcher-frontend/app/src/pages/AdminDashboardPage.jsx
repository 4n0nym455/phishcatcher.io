/**
 * AdminDashboard.jsx
 * Platform overview for admins: stats, quick links to admin sub-pages.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  Users, Shield, BarChart3,
  Loader2, AlertTriangle, RefreshCw, Activity,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar,
  BarChart, Bar, PieChart, Pie, Cell, Legend,
} from 'recharts';
import { adminApi } from '@/lib/api';

const COLORS = {
  brand: '#6366f1',
  success: '#10b981',
  threat: '#f59e0b',
  danger: '#ef4444',
  purple: '#8b5cf6',
  pink: '#ec4899',
  cyan: '#06b6d4',
};

const PIE_COLORS = [COLORS.danger, COLORS.threat, COLORS.success, COLORS.brand, COLORS.purple, COLORS.pink, COLORS.cyan];

export default function AdminDashboardPage() {
  const [stats,      setStats]     = useState(null);
  const [analytics,  setAnalytics] = useState(null);
  const [loading,    setLoading]   = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [period,     setPeriod]    = useState(30);

  const fetchData = async () => {
    if (!refreshing) setLoading(true);
    try {
      const [s, a] = await Promise.allSettled([
        adminApi.getStats(),
        adminApi.getAnalytics(period)
      ]);
      if (s.status === 'fulfilled') setStats(s.value);
      if (a.status === 'fulfilled') setAnalytics(a.value);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [period]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        adminApi.getStats().then(setStats).catch(() => {});
      }
    };
    
    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData();
  };

  const handlePeriodChange = (days) => {
    setPeriod(days);
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
              { icon: Activity,      label: 'Active users',      value: stats?.users?.active    ?? '—', color: 'var(--success)', bg: 'var(--success-dim)' },
              { icon: Shield,        label: 'Emails analyzed',   value: stats?.total_emails      ?? '—', color: 'var(--threat)',  bg: 'var(--threat-dim)'  },
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
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-heading font-700 text-sm" style={{ color: 'var(--text-muted)' }}>OVERVIEW</h2>
            <button
              onClick={handleRefresh}
              disabled={loading || refreshing}
              className="p-1.5 rounded-lg transition-opacity hover:opacity-70 disabled:opacity-40"
              style={{ color: 'var(--text-muted)' }}
              title="Refresh stats"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
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

          {/* Quick access cards */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[
              { to: '/admin/users',      icon: Users,     title: 'User Management', desc: 'View, edit, activate or deactivate user accounts', color: 'var(--brand)',   bg: 'var(--brand-dim)'   },
              { to: '/admin/audit-logs', icon: Activity,  title: 'Audit Logs',      desc: 'Security event history with filters and search',   color: 'var(--threat)',  bg: 'var(--threat-dim)'  },
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

          {/* Analytics Charts */}
          {analytics && (
            <>
              {/* Period selector */}
              <div className="flex items-center justify-between">
                <h2 className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>
                  Analytics Overview
                </h2>
                <div className="flex gap-1 bg-[var(--bg-elevated)] p-1 rounded-lg">
                  {[7, 30, 90].map(d => (
                    <button
                      key={d}
                      onClick={() => handlePeriodChange(d)}
                      className={`px-3 py-1.5 text-xs font-500 rounded-md transition-all ${
                        period === d
                          ? 'bg-[var(--brand)] text-white'
                          : 'text-[var(--text-muted)] hover:text-[var(--text-primary)]'
                      }`}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
              </div>

              {/* Area Chart - Daily Analyses */}
              <div className="card p-6">
                <h3 className="font-heading font-600 text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
                  Email Analysis Trends
                </h3>
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={analytics.daily_analyses} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.brand} stopOpacity={0.3}/>
                          <stop offset="95%" stopColor={COLORS.brand} stopOpacity={0}/>
                        </linearGradient>
                        <linearGradient id="colorPhishing" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={COLORS.danger} stopOpacity={0.3}/>
                          <stop offset="95%" stopColor={COLORS.danger} stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                        tickFormatter={(v) => {
                          const d = new Date(v);
                          return period <= 14 ? d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : d.toLocaleDateString(undefined, { month: 'short' });
                        }}
                        interval={Math.floor(analytics.daily_analyses.length / 6)}
                      />
                      <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                      <Tooltip
                        contentStyle={{ 
                          background: 'var(--bg-surface)', 
                          border: '1px solid var(--border)', 
                          borderRadius: '8px',
                          color: 'var(--text-primary)'
                        }}
                      />
                      <Area type="monotone" dataKey="total" stroke={COLORS.brand} fill="url(#colorTotal)" strokeWidth={2} name="Total" />
                      <Area type="monotone" dataKey="phishing" stroke={COLORS.danger} fill="url(#colorPhishing)" strokeWidth={2} name="Phishing" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Charts Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Radar Chart - Threat Categories */}
                <div className="card p-6">
                  <h3 className="font-heading font-600 text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
                    Threat Category Distribution
                  </h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <RadarChart data={analytics.category_breakdown.map((c, i) => ({ ...c, fill: PIE_COLORS[i % PIE_COLORS.length] }))}>
                        <PolarGrid stroke="var(--border)" />
                        <PolarAngleAxis dataKey="category" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <PolarRadiusAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                        <Radar name="Count" dataKey="count" stroke={COLORS.brand} fill={COLORS.brand} fillOpacity={0.3} strokeWidth={2} />
                      </RadarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Bar Chart - Risk Distribution */}
                <div className="card p-6">
                  <h3 className="font-heading font-600 text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
                    Risk Score Distribution
                  </h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={analytics.risk_distribution} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                        <XAxis dataKey="range" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{ 
                            background: 'var(--bg-surface)', 
                            border: '1px solid var(--border)', 
                            borderRadius: '8px',
                            color: 'var(--text-primary)'
                          }}
                        />
                        <Bar dataKey="count" name="Emails" radius={[4, 4, 0, 0]}>
                          {analytics.risk_distribution.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={index < 2 ? COLORS.success : index < 4 ? COLORS.threat : COLORS.danger} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* Pie Chart - Current Status */}
                <div className="card p-6">
                  <h3 className="font-heading font-600 text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
                    Current Threat Status
                  </h3>
                  <div className="h-64 flex items-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={[
                            { name: 'Phishing', value: analytics.current_threat_status?.phishing ?? analytics.daily_analyses.reduce((a, b) => a + b.phishing, 0), color: COLORS.danger },
                            { name: 'Suspicious', value: analytics.current_threat_status?.suspicious ?? analytics.daily_analyses.reduce((a, b) => a + b.suspicious, 0), color: COLORS.threat },
                            { name: 'Safe', value: analytics.current_threat_status?.safe ?? analytics.daily_analyses.reduce((a, b) => a + b.safe, 0), color: COLORS.success },
                          ]}
                          cx="50%"
                          cy="50%"
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                          nameKey="name"
                        >
                          {[
                            { name: 'Phishing', value: analytics.current_threat_status?.phishing ?? analytics.daily_analyses.reduce((a, b) => a + b.phishing, 0), color: COLORS.danger },
                            { name: 'Suspicious', value: analytics.current_threat_status?.suspicious ?? analytics.daily_analyses.reduce((a, b) => a + b.suspicious, 0), color: COLORS.threat },
                            { name: 'Safe', value: analytics.current_threat_status?.safe ?? analytics.daily_analyses.reduce((a, b) => a + b.safe, 0), color: COLORS.success },
                          ].map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip
                          contentStyle={{ 
                            background: 'var(--bg-surface)', 
                            border: '1px solid var(--border)', 
                            borderRadius: '8px',
                            color: 'var(--text-primary)'
                          }}
                        />
                        <Legend 
                          verticalAlign="middle" 
                          align="right"
                          layout="vertical"
                          iconType="circle"
                          formatter={(value) => <span style={{ color: 'var(--text-secondary)', fontSize: '12px' }}>{value}</span>}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* User Activity Chart */}
                <div className="card p-6">
                  <h3 className="font-heading font-600 text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
                    User Activity (30d)
                  </h3>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={analytics.user_activity} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorNewUsers" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={COLORS.purple} stopOpacity={0.3}/>
                            <stop offset="95%" stopColor={COLORS.purple} stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="colorActiveUsers" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={COLORS.cyan} stopOpacity={0.3}/>
                            <stop offset="95%" stopColor={COLORS.cyan} stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                        <XAxis 
                          dataKey="date" 
                          tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                          tickFormatter={(v) => {
                            const d = new Date(v);
                            return period <= 14 ? d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : d.toLocaleDateString(undefined, { month: 'short' });
                          }}
                          interval={Math.floor(analytics.user_activity.length / 6)}
                        />
                        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                        <Tooltip
                          contentStyle={{ 
                            background: 'var(--bg-surface)', 
                            border: '1px solid var(--border)', 
                            borderRadius: '8px',
                            color: 'var(--text-primary)'
                          }}
                        />
                        <Area type="monotone" dataKey="new_users" stroke={COLORS.purple} fill="url(#colorNewUsers)" strokeWidth={2} name="New Users" />
                        <Area type="monotone" dataKey="active_users" stroke={COLORS.cyan} fill="url(#colorActiveUsers)" strokeWidth={2} name="Active Users" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}