import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { 
  Calendar, 
  TrendingUp, 
  AlertTriangle, 
  Shield,
  Download,
  ChevronLeft,
  ChevronRight,
  Eye
} from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi } from '@/lib/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

const CATEGORY_COLORS = {
  phishing: '#0ea5c7',
  malware: '#ef4444',
  spoofing: '#f59e0b',
  suspicious: '#f59e0b',
  safe: '#10b981',
};

function formatWeekRange(weekStart, weekEnd) {
  const start = new Date(weekStart);
  const end = new Date(weekEnd);
  return `${start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${end.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`;
}

function getWeeklyStats(data) {
  if (!data) {
    return [
      { label: 'Total Analyzed', value: '0' },
      { label: 'Threats Detected', value: '0' },
      { label: 'Suspicious', value: '0' },
      { label: 'Detection Rate', value: '0%' },
    ];
  }
  const total = data.total_analyses ?? data.total_emails ?? 0;
  const threats = (data.phishing_detected ?? 0) + (data.malware_detected ?? 0);
  const suspicious = data.suspicious_detected ?? 0;
  const safe = data.safe_emails ?? 0;
  const detectionRate = total > 0 ? ((safe + threats) / total * 100).toFixed(1) : 0;
  
  return [
    { label: 'Total Analyzed', value: total.toLocaleString() },
    { label: 'Threats Detected', value: threats.toString() },
    { label: 'Suspicious', value: suspicious.toString() },
    { label: 'Detection Rate', value: `${detectionRate}%` },
  ];
}

function getDailyData(dailyBreakdown) {
  if (!dailyBreakdown || dailyBreakdown.length === 0) {
    return [
      { day: 'Mon', analyzed: 0, threats: 0, suspicious: 0 },
      { day: 'Tue', analyzed: 0, threats: 0, suspicious: 0 },
      { day: 'Wed', analyzed: 0, threats: 0, suspicious: 0 },
      { day: 'Thu', analyzed: 0, threats: 0, suspicious: 0 },
      { day: 'Fri', analyzed: 0, threats: 0, suspicious: 0 },
      { day: 'Sat', analyzed: 0, threats: 0, suspicious: 0 },
      { day: 'Sun', analyzed: 0, threats: 0, suspicious: 0 },
    ];
  }
  return dailyBreakdown.map(d => ({
    day: d.day ?? 'Unknown',
    analyzed: d.analyzed ?? d.total ?? 0,
    threats: d.threats ?? d.phishing ?? 0,
    suspicious: d.suspicious ?? 0,
  }));
}

function getThreatCategories(data) {
  const categories = [];
  if (data?.phishing_detected > 0) categories.push({ name: 'Phishing', value: data.phishing_detected, color: CATEGORY_COLORS.phishing });
  if (data?.malware_detected > 0) categories.push({ name: 'Malware', value: data.malware_detected, color: CATEGORY_COLORS.malware });
  if (data?.suspicious_detected > 0) categories.push({ name: 'Suspicious', value: data.suspicious_detected, color: CATEGORY_COLORS.suspicious });
  if (data?.safe_emails > 0) categories.push({ name: 'Safe', value: data.safe_emails, color: CATEGORY_COLORS.safe });
  return categories.length > 0 ? categories : [{ name: 'No Data', value: 1, color: '#94a3b8' }];
}

function getTopThreats(topThreats, showSensitive) {
  if (!topThreats || topThreats.length === 0) {
    return [];
  }
  return topThreats.map((t, i) => ({
    id: t.id ?? i,
    subject: t.subject ?? t.subject_line ?? 'Unknown threat',
    sender: t.sender ?? t.from ?? 'Unknown sender',
    count: t.count ?? 1,
    riskScore: Math.round(t.risk_score ?? t.riskScore ?? 0),
    showSensitive,
  }));
}

function getInsights(data) {
  const insights = [];
  const threats = (data?.phishing_detected ?? 0) + (data?.malware_detected ?? 0);
  const total = data?.total_analyses ?? data?.total_emails ?? 0;
  
  if (threats > 0) {
    insights.push({
      icon: TrendingUp,
      color: 'brand',
      title: `${threats} threats detected this week`,
      desc: `${((threats / total) * 100).toFixed(1)}% of analyzed emails contained threats`,
    });
  }
  
  if (data?.average_risk_score > 50) {
    insights.push({
      icon: AlertTriangle,
      color: 'threat',
      title: 'Elevated risk score average',
      desc: `Average risk score of ${Math.round(data.average_risk_score)} indicates increased threat activity`,
    });
  }
  
  if (data?.suspicious_detected > 0) {
    insights.push({
      icon: Shield,
      color: 'success',
      title: `${data.suspicious_detected} suspicious emails flagged`,
      desc: 'These emails require further review but were not confirmed as threats',
    });
  }
  
  if (insights.length === 0 && total > 0) {
    insights.push({
      icon: Shield,
      color: 'success',
      title: 'All clear this week',
      desc: 'No threats detected in analyzed emails',
    });
  }
  
  return insights;
}

const insightBgColors = {
  brand: { bg: 'var(--brand-dim)', border: 'var(--brand)' },
  threat: { bg: 'var(--threat-dim)', border: 'var(--threat)' },
  success: { bg: 'var(--success-dim)', border: 'var(--success)' },
  danger: { bg: 'var(--danger-dim)', border: 'var(--danger)' },
};

export default function WeeklyReportsPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showSensitive, setShowSensitive] = useState(false);

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const result = await analysisApi.getWeeklyReport();
        setData(result);
      } catch (err) {
        setError(err.message ?? 'Failed to load reports.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleDownload = () => {
    if (data?.week_start) {
      toast.success('Downloading weekly report...');
    } else {
      toast.info('No report data available for download');
    }
  };

  const handlePreviousWeek = () => {
    if (data?.week_start) {
      const prevWeek = new Date(data.week_start);
      prevWeek.setDate(prevWeek.getDate() - 7);
      setLoading(true);
      (async () => {
        try {
          const result = await analysisApi.getWeeklyReport(prevWeek.toISOString());
          setData(result);
        } catch (err) {
          toast.error('Failed to load previous week');
        } finally {
          setLoading(false);
        }
      })();
    }
  };

  const handleNextWeek = () => {
    if (data?.week_start) {
      const nextWeek = new Date(data.week_start);
      nextWeek.setDate(nextWeek.getDate() + 7);
      const now = new Date();
      if (nextWeek <= now) {
        setLoading(true);
        (async () => {
          try {
            const result = await analysisApi.getWeeklyReport(nextWeek.toISOString());
            setData(result);
          } catch (err) {
            toast.error('Failed to load next week');
          } finally {
            setLoading(false);
          }
        })();
      } else {
        toast.info('Future weeks not available yet');
      }
    }
  };

  const weeklyStats = getWeeklyStats(data);
  const dailyData = getDailyData(data?.daily_breakdown);
  const threatCategories = getThreatCategories(data);
  const topThreatsList = getTopThreats(data?.top_threats, showSensitive);
  const insights = getInsights(data);
  const currentWeekLabel = data?.week_start && data?.week_end 
    ? formatWeekRange(data.week_start, data.week_end) 
    : 'This Week';

  if (loading) {
    return (
      <div className="space-y-6 sm:space-y-8 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="h-9 w-48 rounded animate-pulse" style={{ background: 'var(--brand-dim)' }} />
            <div className="h-5 w-72 mt-2 rounded animate-pulse" style={{ background: 'var(--brand-dim)', opacity: 0.5 }} />
          </div>
        </div>
        <div className="card p-12 text-center">
          <div className="w-6 h-6 animate-spin mx-auto mb-3" style={{ border: '2px solid var(--brand)', borderTopColor: 'transparent', borderRadius: '50%' }} />
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading reports…</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 sm:space-y-8 animate-fade-in">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="page-title">Weekly Reports</h1>
            <p className="page-subtitle">Phishing threat intelligence summary</p>
          </div>
        </div>
        <div className="alert-error">{error}</div>
      </div>
    );
  }

  return (
    <div className="space-y-6 sm:space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="page-title">Weekly Reports</h1>
          <p className="page-subtitle">Phishing threat intelligence summary</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSensitive(!showSensitive)}
            className="btn-ghost h-9 px-3"
          >
            <Eye className="w-3.5 h-3.5" />
            {showSensitive ? 'Hide' : 'Show'}
          </button>
          <button
            onClick={handleDownload}
            className="btn-primary h-9 px-4"
          >
            <Download className="w-4 h-4" />
            Download
          </button>
        </div>
      </div>

      {/* Week Navigation */}
      <div className="card p-4 flex items-center justify-between">
        <button 
          onClick={handlePreviousWeek}
          className="p-2 rounded-lg hover:bg-brand-dim transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-3">
          <Calendar className="w-5 h-5" style={{ color: 'var(--brand)' }} />
          <span className="font-heading font-semibold">{currentWeekLabel}</span>
        </div>
        <button 
          onClick={handleNextWeek}
          className="p-2 rounded-lg hover:bg-brand-dim transition-colors"
          style={{ color: 'var(--text-muted)' }}
        >
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {weeklyStats.map((stat, index) => (
            <div key={index} className="card p-4 sm:p-6">
              <p className="text-xs sm:text-sm mb-1" style={{ color: 'var(--text-muted)' }}>{stat.label}</p>
              <p className="text-xl sm:text-2xl font-heading font-bold" style={{ color: 'var(--text-primary)' }}>{stat.value}</p>
            </div>
          ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
        {/* Daily Analysis Chart */}
        <div className="lg:col-span-2 card p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Daily Analysis Activity</h3>
          <div className="h-56 sm:h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={dailyData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'var(--bg-surface)', 
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    boxShadow: 'var(--shadow-md)'
                  }}
                />
                <Bar dataKey="analyzed" fill="var(--brand)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="threats" fill="var(--danger)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="suspicious" fill="var(--threat)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="flex items-center gap-4 mt-4 justify-center">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded" style={{ background: 'var(--brand)' }} />
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Analyzed</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded" style={{ background: 'var(--danger)' }} />
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Threats</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded" style={{ background: 'var(--threat)' }} />
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Suspicious</span>
            </div>
          </div>
        </div>

        {/* Threat Categories */}
        <div className="card p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Threat Categories</h3>
          <div className="h-48 sm:h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={threatCategories}
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={70}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {threatCategories.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: 'var(--bg-surface)', 
                    border: '1px solid var(--border)',
                    borderRadius: '8px'
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="grid grid-cols-2 gap-2 mt-4">
            {threatCategories.map((cat, index) => (
              <div key={index} className="flex items-center gap-2">
                <div className="w-3 h-3 rounded" style={{ backgroundColor: cat.color }} />
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{cat.name}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Top Threats This Week */}
      <div className="card p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-heading font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Top Threats This Week</h3>
        {topThreatsList.length > 0 ? (
          <div className="space-y-3">
            {topThreatsList.map((threat, index) => (
              <Link
                key={threat.id}
                to={`/analysis/${threat.id}`}
                className="flex items-center gap-3 sm:gap-4 p-3 rounded-xl hover:bg-brand-dim transition-colors group"
              >
                <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style={{ background: 'var(--danger-dim)' }}>
                  <span className="text-sm font-mono font-bold" style={{ color: 'var(--danger)' }}>#{index + 1}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm font-medium truncate group-hover:text-brand transition-colors ${!showSensitive && 'blur-sensitive'}`}
                    style={{ color: 'var(--text-primary)' }}>
                    {threat.subject}
                  </p>
                  <p className={`text-xs truncate ${!showSensitive && 'blur-sensitive'}`}
                    style={{ color: 'var(--text-muted)' }}>
                    {threat.sender}
                  </p>
                </div>
                <div className="flex items-center gap-3 sm:gap-4">
                  <div className="text-right">
                    <p className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>{threat.count}</p>
                    <p className="text-[10px]" style={{ color: 'var(--text-muted)' }}>reports</p>
                  </div>
                  <div className="px-2 py-1 rounded-md" style={{ background: 'var(--danger-dim)', border: '1px solid var(--danger)' }}>
                    <span className="text-xs font-mono font-bold" style={{ color: 'var(--danger)' }}>{threat.riskScore}%</span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="text-sm text-center py-4" style={{ color: 'var(--text-muted)' }}>No top threats recorded for this week</p>
        )}
      </div>

      {/* Key Insights */}
      <div className="card p-4 sm:p-6">
        <h3 className="text-base sm:text-lg font-heading font-semibold mb-4" style={{ color: 'var(--text-primary)' }}>Key Insights</h3>
        {insights.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {insights.map((insight, index) => {
              const colors = insightBgColors[insight.color] || insightBgColors.success;
              return (
                <div key={index} className="flex items-start gap-3 p-4 rounded-xl border" style={{ background: colors.bg, borderColor: colors.border }}>
                  <insight.icon className="w-5 h-5 mt-0.5 flex-shrink-0" style={{ color: colors.border }} />
                  <div>
                    <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{insight.title}</p>
                    <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>{insight.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-sm text-center py-4" style={{ color: 'var(--text-muted)' }}>No insights available for this week</p>
        )}
      </div>
    </div>
  );
}