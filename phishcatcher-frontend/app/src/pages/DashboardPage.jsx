/**
 * Dashboard.jsx
 * Main app dashboard showing stats, recent analyses, quick actions, Gmail banner.
 * Fully CSS-variable driven — light & dark mode.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Upload, Shield, AlertTriangle, CheckCircle, TrendingUp,
  FileText, ChevronRight, Mail, Clock, RefreshCw, BarChart3,
} from 'lucide-react';
import { analysisApi, authApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts';

const CHART_COLORS = {
  safe: '#10b981',
  suspicious: '#f59e0b',
  phishing: '#ef4444',
};

/* ─── Helpers ──────────────────────────────────────────────────────────── */
function riskScore(a)     { return a.threat_score ?? a.risk_score ?? 0; }
function riskLabel(s)     { return s >= 70 ? 'High' : s >= 40 ? 'Medium' : 'Safe'; }
function riskBadge(s)     { return s >= 70 ? 'badge badge-danger' : s >= 40 ? 'badge badge-threat' : 'badge badge-success'; }
function riskTextColor(s) { return s >= 70 ? 'var(--danger)' : s >= 40 ? 'var(--threat)' : 'var(--success)'; }

function timeAgo(iso) {
  if (!iso) return '—';
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

/* ─── Stat card ────────────────────────────────────────────────────────── */
function StatCard({ icon: Icon, label, value, color, bg, loading }) {
  return (
    <div className="stat-card theme-transition">
      <div className="flex items-start justify-between mb-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: bg, color }}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
      <div className="stat-value" style={{ color: loading ? 'var(--border)' : undefined }}>
        {loading ? '—' : value}
      </div>
      <div className="stat-label">{label}</div>
    </div>
  );
}

/* ─── Empty state ──────────────────────────────────────────────────────── */
function EmptyState() {
  return (
    <div className="text-center py-16 px-4">
      <img src="/phishcatcher.png" alt="" className="w-14 h-14 object-contain mx-auto mb-4 opacity-25" />
      <h3 className="font-heading font-700 text-lg mb-2" style={{ color: 'var(--text-primary)' }}>
        No analyses yet
      </h3>
      <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
        Upload your first email to get a threat analysis report.
      </p>
      <Link to="/upload" className="btn-primary inline-flex">
        <Upload className="w-4 h-4" /> Upload email
      </Link>
    </div>
  );
}

/* ─── Main ─────────────────────────────────────────────────────────────── */
export default function DashboardPage() {
  const { user }  = useAuth();
  const navigate  = useNavigate();

  const [analyses,    setAnalyses]    = useState([]);
  const [gmailStatus, setGmailStatus] = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [refreshing,  setRefreshing]  = useState(false);

  const fetchData = useCallback(async (showRefreshSpinner = false) => {
    showRefreshSpinner ? setRefreshing(true) : setLoading(true);
    try {
      const [histRes, gmailRes] = await Promise.allSettled([
        analysisApi.getHistory({ pageSize: 8 }),
        authApi.gmail.getStatus(),
      ]);
      if (histRes.status === 'fulfilled') {
        const items = histRes.value.items ?? histRes.value.analyses ?? histRes.value ?? [];
        setAnalyses(Array.isArray(items) ? items : []);
      }
      if (gmailRes.status === 'fulfilled') {
        setGmailStatus(gmailRes.value);
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  // Derived stats
  const total      = analyses.length;
  const phishing   = analyses.filter(a => riskScore(a) >= 70).length;
  const suspicious = analyses.filter(a => riskScore(a) >= 40 && riskScore(a) < 70).length;
  const safe       = total - phishing - suspicious;

  const threatData = useMemo(() => [
    { name: 'Safe', value: safe, color: CHART_COLORS.safe },
    { name: 'Suspicious', value: suspicious, color: CHART_COLORS.suspicious },
    { name: 'Phishing', value: phishing, color: CHART_COLORS.phishing },
  ], [safe, suspicious, phishing]);

  const trendData = useMemo(() => {
    const sorted = [...analyses].sort((a, b) => 
      new Date(a.created_at || a.analyzed_at) - new Date(b.created_at || b.analyzed_at)
    );
    const grouped = {};
    sorted.forEach(a => {
      const date = new Date(a.created_at || a.analyzed_at).toISOString().split('T')[0];
      if (!grouped[date]) grouped[date] = { date, total: 0, phishing: 0, suspicious: 0, safe: 0 };
      grouped[date].total++;
      const s = riskScore(a);
      if (s >= 70) grouped[date].phishing++;
      else if (s >= 40) grouped[date].suspicious++;
      else grouped[date].safe++;
    });
    return Object.values(grouped).slice(-14);
  }, [analyses]);

  const hour      = new Date().getHours();
  const greeting  = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';
  const firstName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || 'there';
  const gmailConnected = gmailStatus?.connected ?? false;

  return (
    <div className="space-y-8 animate-fade-in">

      {/* ── Header ── */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h1 className="page-title">{greeting}, {firstName} 👋</h1>
          <p className="page-subtitle">Here's your email threat overview</p>
        </div>
        <div className="flex items-center gap-2 self-start">
          <button
            onClick={() => fetchData(true)}
            disabled={refreshing}
            className="btn-ghost h-9 px-3 text-sm"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing…' : 'Refresh'}
          </button>
          <Link to="/upload" className="btn-primary h-9 px-4 text-sm">
            <Upload className="w-4 h-4" /> Analyze email
          </Link>
        </div>
      </div>

      {/* ── Stats ── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={FileText}      label="Total analyzed" value={total}      color="var(--brand)"   bg="var(--brand-dim)"   loading={loading} />
        <StatCard icon={CheckCircle}   label="Safe"           value={safe}       color="var(--success)" bg="var(--success-dim)" loading={loading} />
        <StatCard icon={AlertTriangle} label="Suspicious"     value={suspicious} color="var(--threat)"  bg="var(--threat-dim)"  loading={loading} />
        <StatCard icon={Shield}        label="Phishing"       value={phishing}   color="var(--danger)"  bg="var(--danger-dim)"  loading={loading} />
      </div>

      {/* ── Charts ── */}
      {total > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Threat Distribution Pie Chart */}
          <div className="card p-6">
            <h2 className="font-heading font-600 text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
              Threat Distribution
            </h2>
            <div className="h-56 flex items-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={threatData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={70}
                    paddingAngle={5}
                    dataKey="value"
                    nameKey="name"
                  >
                    {threatData.map((entry, index) => (
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

          {/* Trend Area Chart */}
          <div className="card p-6">
            <h2 className="font-heading font-600 text-sm mb-4" style={{ color: 'var(--text-primary)' }}>
              Analysis Trend (Last 14 Days)
            </h2>
            <div className="h-56">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={trendData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorSafe" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.safe} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={CHART_COLORS.safe} stopOpacity={0}/>
                    </linearGradient>
                    <linearGradient id="colorThreat" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor={CHART_COLORS.phishing} stopOpacity={0.3}/>
                      <stop offset="95%" stopColor={CHART_COLORS.phishing} stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis 
                    dataKey="date" 
                    tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                    tickFormatter={(v) => new Date(v).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                    interval={Math.floor(trendData.length / 5)}
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
                  <Area type="monotone" dataKey="safe" stackId="1" stroke={CHART_COLORS.safe} fill="url(#colorSafe)" strokeWidth={2} name="Safe" />
                  <Area type="monotone" dataKey="suspicious" stackId="2" stroke={CHART_COLORS.suspicious} fill={CHART_COLORS.suspicious} fillOpacity={0.3} strokeWidth={2} name="Suspicious" />
                  <Area type="monotone" dataKey="phishing" stackId="3" stroke={CHART_COLORS.phishing} fill="url(#colorThreat)" strokeWidth={2} name="Phishing" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}

      {/* ── Quick actions ── */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {[
          { to: '/upload',         icon: Upload,    title: 'Analyze Email',  desc: 'Upload an .eml file for instant threat detection', color: 'var(--brand)',   bg: 'var(--brand-dim)'   },
          { to: '/analysis',       icon: FileText,  title: 'View History',   desc: 'Browse all your previous analysis reports',       color: 'var(--threat)',  bg: 'var(--threat-dim)'  },
          { to: '/weekly-reports', icon: BarChart3, title: 'Weekly Reports', desc: 'Threat intelligence summaries and trend data',     color: 'var(--success)', bg: 'var(--success-dim)' },
        ].map(item => (
          <Link
            key={item.to}
            to={item.to}
            className="card p-5 flex gap-4 items-start group theme-transition"
            style={{ textDecoration: 'none' }}
          >
            <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: item.bg, color: item.color }}>
              <item.icon className="w-5 h-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-1">
                <p className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>{item.title}</p>
                <ChevronRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-0.5"
                  style={{ color: 'var(--text-muted)' }} />
              </div>
              <p className="text-xs mt-0.5 leading-snug" style={{ color: 'var(--text-muted)' }}>{item.desc}</p>
            </div>
          </Link>
        ))}
      </div>

      {/* ── Recent analyses ── */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>
            Recent analyses
          </h2>
          {analyses.length > 0 && (
            <Link to="/analysis" className="text-sm font-500 hover:underline" style={{ color: 'var(--brand)' }}>
              View all
            </Link>
          )}
        </div>

        <div className="rounded-2xl overflow-hidden"
          style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          {loading ? (
            <div className="p-10 text-center">
              <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading analyses…</p>
            </div>
          ) : analyses.length === 0 ? (
            <EmptyState />
          ) : (
            <table className="table-base">
              <thead>
                <tr>
                  <th>Subject / File</th>
                  <th className="hidden sm:table-cell">Category</th>
                  <th>Risk</th>
                  <th className="hidden md:table-cell">Score</th>
                  <th className="hidden lg:table-cell">Date</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {analyses.map(a => {
                  const s       = riskScore(a);
                  const subject = a.subject ?? a.filename ?? a.email_subject ?? 'Untitled';
                  const cat     = a.threat_category ?? a.category ?? '—';
                  const date    = a.created_at ?? a.analyzed_at;
                  return (
                    <tr
                      key={a.id}
                      className="cursor-pointer"
                      onClick={() => navigate(`/analysis/${a.id}`)}
                    >
                      <td>
                        <span className="font-500 text-sm block truncate max-w-[180px]"
                          style={{ color: 'var(--text-primary)' }}>
                          {subject}
                        </span>
                      </td>
                      <td className="hidden sm:table-cell">
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{cat}</span>
                      </td>
                      <td><span className={riskBadge(s)}>{riskLabel(s)}</span></td>
                      <td className="hidden md:table-cell">
                        <span className="font-heading font-700 text-sm" style={{ color: riskTextColor(s) }}>
                          {s}
                        </span>
                      </td>
                      <td className="hidden lg:table-cell">
                        <span className="text-xs flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                          <Clock className="w-3 h-3" />{timeAgo(date)}
                        </span>
                      </td>
                      <td>
                        <span className="text-xs font-500" style={{ color: 'var(--brand)' }}>View →</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* ── Gmail integration banner ── */}
      <div
        className="rounded-2xl p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4"
        style={gmailConnected
          ? { background: 'var(--success-dim)', border: '1px solid var(--success)' }
          : { background: 'var(--brand-dim)',   border: '1px solid var(--brand)'   }
        }
      >
        <div className="flex items-center gap-4">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: gmailConnected ? 'var(--success)' : 'var(--brand)', color: '#fff' }}
          >
            <Mail className="w-5 h-5" />
          </div>
          <div>
            <p className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>
              {gmailConnected ? 'Gmail connected' : 'Connect Gmail'}
            </p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {gmailConnected
                ? 'PhishCatcher is monitoring your inbox automatically'
                : 'Let PhishCatcher continuously monitor your inbox for threats'
              }
            </p>
          </div>
        </div>
        <Link
          to="/settings"
          className="btn-ghost text-sm shrink-0 h-9 px-4"
          style={gmailConnected
            ? { color: 'var(--success)', borderColor: 'var(--success)' }
            : { color: 'var(--brand)',   borderColor: 'var(--brand)'   }
          }
        >
          {gmailConnected ? 'Manage integration' : 'Set up integration'}
          <ChevronRight className="w-3.5 h-3.5" />
        </Link>
      </div>
    </div>
  );
}