import { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { 
  Calendar, 
  TrendingUp, 
  AlertTriangle, 
  Shield,
  Download,
  ChevronLeft,
  ChevronRight,
  Eye,
  RefreshCw,
  Search,
  FileText,
  Clock,
  Loader2,
  CheckSquare,
  Square,
  X,
  CheckCircle,
  Trash2,
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
  LineChart,
  Line,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts';

const CATEGORY_COLORS = {
  phishing: '#FF4D8D',
  malware: '#FF6B35',
  spoofing: '#FFD166',
  suspicious: '#FFD166',
  safe: '#27D3C7',
};

const RADAR_COLORS = {
  phishing: '#FF4D8D',
  malware: '#FF6B35',
  suspicious: '#FFD166',
  safe: '#27D3C7',
};

const PIE_COLORS = ['#ef4444', '#8b5cf6', '#f59e0b', '#10b981'];

function getTodayStr() {
  return new Date().toISOString().split('T')[0];
}

function formatDateRange(start, end) {
  const s = new Date(start);
  const e = new Date(end);
  return `${s.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${e.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`;
}

function formatDate(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

function getDefaultDates() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 7);
  return {
    startDate: start.toISOString().split('T')[0],
    endDate: end.toISOString().split('T')[0]
  };
}

function getPresetDates(preset) {
  const end = new Date();
  const start = new Date();
  
  switch (preset) {
    case '7days':
      start.setDate(start.getDate() - 7);
      break;
    case '30days':
      start.setDate(start.getDate() - 30);
      break;
    case '90days':
      start.setDate(start.getDate() - 90);
      break;
    case 'year':
      start.setFullYear(start.getFullYear() - 1);
      break;
    case 'month':
      start.setDate(1);
      end.setDate(0);
      break;
    default:
      start.setDate(start.getDate() - 7);
  }
  
  return {
    startDate: start.toISOString().split('T')[0],
    endDate: end.toISOString().split('T')[0]
  };
}

function getDefaultIndividualDates() {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);
  return {
    startDate: start.toISOString().split('T')[0],
    endDate: end.toISOString().split('T')[0]
  };
}

function isValidDateRange(start, end) {
  if (!start || !end) return { valid: false, message: 'Please select both start and end dates' };
  
  const startDate = new Date(start);
  const endDate = new Date(end);
  const today = new Date();
  today.setHours(23, 59, 59, 999);
  
  if (startDate > today || endDate > today) {
    return { valid: false, message: 'Cannot select future dates' };
  }
  
  if (startDate > endDate) {
    return { valid: false, message: 'Start date must be before end date' };
  }
  
  const daysDiff = Math.ceil((endDate - startDate) / (1000 * 60 * 60 * 24));
  if (daysDiff > 365) {
    return { valid: false, message: 'Date range cannot exceed 1 year' };
  }
  
  return { valid: true };
}

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

function score(a) { return a.threat_score ?? a.risk_score ?? 0; }
function riskLabel(s) { return s >= 70 ? 'High' : s >= 40 ? 'Medium' : 'Safe'; }
function riskBadge(s) { return s >= 70 ? 'badge badge-danger' : s >= 40 ? 'badge badge-threat' : 'badge badge-success'; }
function riskColor(s) { return s >= 70 ? 'var(--danger)' : s >= 40 ? 'var(--threat)' : 'var(--success)'; }

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState('summary');
  
  return (
    <div className="space-y-6 sm:space-y-8 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-heading font-700" style={{ color: 'var(--text-primary)' }}>
            Reports
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Analyze email threats with comprehensive reports
          </p>
        </div>
      </div>

      <div className="flex gap-1 p-1 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
        <button
          onClick={() => setActiveTab('summary')}
          className={`flex-1 px-4 py-2 rounded-md text-sm font-500 transition-all ${
            activeTab === 'summary'
              ? 'bg-[var(--brand)] text-white shadow-sm'
              : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'
          }`}
        >
          Summary
        </button>
        <button
          onClick={() => setActiveTab('individual')}
          className={`flex-1 px-4 py-2 rounded-md text-sm font-500 transition-all ${
            activeTab === 'individual'
              ? 'bg-[var(--brand)] text-white shadow-sm'
              : 'text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'
          }`}
        >
          Individual
        </button>
      </div>

      {activeTab === 'summary' && <SummaryTab />}
      {activeTab === 'individual' && <IndividualTab />}
    </div>
  );
}

function SummaryTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [preset, setPreset] = useState('7days');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const defaults = getDefaultDates();
    setStartDate(defaults.startDate);
    setEndDate(defaults.endDate);
  }, []);

  const loadReport = (start, end) => {
    setLoading(true);
    (async () => {
      try {
        const result = await analysisApi.getReport(start, end);
        setData(result);
        setError('');
      } catch (err) {
        setError(err.message ?? 'Failed to load report');
      } finally {
        setLoading(false);
      }
    })();
  };

  useEffect(() => {
    if (startDate && endDate) {
      const validation = isValidDateRange(startDate, endDate);
      if (validation.valid) {
        loadReport(startDate, endDate);
      }
    }
  }, [startDate, endDate]);

  const handlePresetClick = (presetValue) => {
    setPreset(presetValue);
    const dates = getPresetDates(presetValue);
    setStartDate(dates.startDate);
    setEndDate(dates.endDate);
  };

  const handlePreviousPeriod = () => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diff = end - start;
    const newStart = new Date(start.getTime() - diff - 1);
    const newEnd = new Date(start.getTime() - 1);
    setStartDate(newStart.toISOString().split('T')[0]);
    setEndDate(newEnd.toISOString().split('T')[0]);
  };

  const handleNextPeriod = () => {
    const start = new Date(startDate);
    const end = new Date(endDate);
    const diff = end - start;
    const now = new Date();
    const newStart = new Date(start.getTime() + diff + 1);
    const newEnd = new Date(end.getTime() + diff + 1);
    
    if (newEnd > now) {
      toast.info('Cannot view future periods');
      return;
    }
    
    setStartDate(newStart.toISOString().split('T')[0]);
    setEndDate(newEnd.toISOString().split('T')[0]);
  };

  const handleDownload = async () => {
    if (!data) {
      toast.info('Generate a report first');
      return;
    }
    try {
      setDownloading(true);
      toast.success('Generating PDF report...');
      const blob = await analysisApi.downloadSummaryReport(startDate, endDate);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `phishcatcher-summary-${startDate}-to-${endDate}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Report downloaded');
    } catch (err) {
      toast.error(err.message ?? 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const stats = useMemo(() => {
    if (!data) {
      return [
        { label: 'Total Analyzed', value: '0' },
        { label: 'Threats', value: '0' },
        { label: 'Suspicious', value: '0' },
        { label: 'Safe', value: '0' },
      ];
    }
    const total = data.total_analyses ?? data.total_emails ?? 0;
    const threats = (data.phishing_detected ?? 0) + (data.malware_detected ?? 0);
    const suspicious = data.suspicious_detected ?? 0;
    const safe = data.safe_emails ?? 0;
    
    return [
      { label: 'Total Analyzed', value: total.toLocaleString() },
      { label: 'Threats', value: threats.toString() },
      { label: 'Suspicious', value: suspicious.toString() },
      { label: 'Safe', value: safe.toString() },
    ];
  }, [data]);

  const pieData = useMemo(() => {
    if (!data) return [];
    const items = [];
    if (data.phishing_detected > 0) items.push({ name: 'Phishing', value: data.phishing_detected, color: '#FF4D8D' });
    if (data.malware_detected > 0) items.push({ name: 'Malware', value: data.malware_detected, color: '#FF6B35' });
    if (data.suspicious_detected > 0) items.push({ name: 'Suspicious', value: data.suspicious_detected, color: '#FFD166' });
    if (data.safe_emails > 0) items.push({ name: 'Safe', value: data.safe_emails, color: '#27D3C7' });
    return items.length > 0 ? items : [{ name: 'No Data', value: 1, color: '#94a3b8' }];
  }, [data]);

  const lineData = useMemo(() => {
    if (!data?.daily_breakdown?.length) return [];
    return data.daily_breakdown.map(d => ({
      day: d.day?.slice(5) || d.day,
      analyzed: d.analyzed ?? d.total ?? 0,
      threats: d.threats ?? d.phishing ?? 0,
    }));
  }, [data]);

  const categoryData = useMemo(() => {
    if (!data) return [];
    const total = data.total_analyses || 1;
    return [
      { name: 'Phishing', value: Math.round((data.phishing_detected / total) * 100) || 0 },
      { name: 'Malware', value: Math.round((data.malware_detected / total) * 100) || 0 },
      { name: 'Suspicious', value: Math.round((data.suspicious_detected / total) * 100) || 0 },
      { name: 'Safe', value: Math.round((data.safe_emails / total) * 100) || 0 },
    ];
  }, [data]);

  const topThreats = useMemo(() => {
    if (!data?.top_threats?.length) return [];
    return data.top_threats.slice(0, 10).map((t, i) => ({
      id: t.id ?? i,
      subject: t.subject ?? t.subject_line ?? 'Unknown threat',
      sender: t.sender ?? t.from ?? 'Unknown sender',
      riskScore: Math.round(t.risk_score ?? t.riskScore ?? 0),
      category: t.category ?? t.threat_category ?? 'Unknown',
    }));
  }, [data]);

  const currentRangeLabel = data?.period_start && data?.period_end 
    ? formatDateRange(data.period_start, data.period_end) 
    : 'Select a date range';

  const today = getTodayStr();

  if (loading && !data) {
    return (
      <div className="card p-12 text-center">
        <div className="w-6 h-6 animate-spin mx-auto mb-3" style={{ border: '2px solid var(--brand)', borderTopColor: 'transparent', borderRadius: '50%' }} />
        <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading report…</p>
      </div>
    );
  }

  return (
    <>
      <div className="card p-4 sm:p-6">
        <div className="flex flex-col lg:flex-row lg:items-end gap-4">
          <div className="flex flex-col sm:flex-row gap-4 flex-1">
            <div className="flex-1">
              <label className="form-label">From</label>
              <input
                type="date"
                value={startDate}
                max={today}
                onChange={e => setStartDate(e.target.value)}
                className="input-base w-full"
              />
            </div>
            <div className="flex-1">
              <label className="form-label">To</label>
              <input
                type="date"
                value={endDate}
                min={startDate}
                max={today}
                onChange={e => setEndDate(e.target.value)}
                className="input-base w-full"
              />
            </div>
          </div>
          <button
            onClick={handleDownload}
            disabled={downloading || !data}
            className="btn-primary h-10 px-6 flex items-center gap-2"
          >
            {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Download
          </button>
        </div>

        <div className="flex flex-wrap gap-2 mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
          <button
            onClick={() => handlePresetClick('7days')}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${preset === '7days' ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-elevated)] hover:bg-[var(--brand-dim)]'}`}
          >
            Last 7 days
          </button>
          <button
            onClick={() => handlePresetClick('30days')}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${preset === '30days' ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-elevated)] hover:bg-[var(--brand-dim)]'}`}
          >
            Last 30 days
          </button>
          <button
            onClick={() => handlePresetClick('90days')}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${preset === '90days' ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-elevated)] hover:bg-[var(--brand-dim)]'}`}
          >
            Last 90 days
          </button>
          <button
            onClick={() => handlePresetClick('year')}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${preset === 'year' ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-elevated)] hover:bg-[var(--brand-dim)]'}`}
          >
            Last Year
          </button>
          <button
            onClick={() => handlePresetClick('month')}
            className={`text-xs px-3 py-1.5 rounded-full transition-colors ${preset === 'month' ? 'bg-[var(--brand)] text-white' : 'bg-[var(--bg-elevated)] hover:bg-[var(--brand-dim)]'}`}
          >
            This Month
          </button>
          
          <div className="flex items-center gap-1 ml-auto">
            <button onClick={handlePreviousPeriod} className="p-1.5 rounded hover:bg-[var(--bg-elevated)]">
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="text-xs px-2" style={{ color: 'var(--text-muted)' }}>
              {currentRangeLabel}
            </span>
            <button onClick={handleNextPeriod} className="p-1.5 rounded hover:bg-[var(--bg-elevated)]">
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {error && (
        <div className="card p-4 border-l-4" style={{ borderColor: 'var(--danger)', background: 'var(--danger-dim)' }}>
          <p className="text-sm" style={{ color: 'var(--danger)' }}>{error}</p>
        </div>
      )}

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map(s => (
          <div key={s.label} className="card p-4 text-center">
            <div className="font-heading font-700 text-2xl sm:text-3xl mb-1" style={{ color: 'var(--text-primary)' }}>
              {loading ? <Loader2 className="w-6 h-6 animate-spin mx-auto" style={{ color: 'var(--text-muted)' }} /> : s.value}
            </div>
            <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.label}</div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card p-4 sm:p-6">
          <h3 className="font-heading font-600 text-base mb-4" style={{ color: 'var(--text-primary)' }}>
            Risk Distribution
          </h3>
          <div className="h-64">
            {pieData.length > 1 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={80}
                    paddingAngle={4}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color || PIE_COLORS[index % PIE_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No threat data</p>
              </div>
            )}
          </div>
        </div>

        <div className="card p-4 sm:p-6">
          <h3 className="font-heading font-600 text-base mb-4" style={{ color: 'var(--text-primary)' }}>
            Category Breakdown
          </h3>
          <div className="h-64">
            {categoryData.length > 0 && categoryData.some(c => c.value > 0) ? (
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={categoryData} cx="50%" cy="50%" outerRadius="70%">
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                  <PolarRadiusAxis tick={{ fill: 'var(--text-muted)', fontSize: 10 }} domain={[0, 100]} />
                  <Radar name="Categories" dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.4} />
                  <Tooltip
                    contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}
                    formatter={(value) => [`${value}%`, 'Percentage']}
                  />
                </RadarChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-full flex items-center justify-center">
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No category data</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="card p-4 sm:p-6">
        <h3 className="font-heading font-600 text-base mb-4" style={{ color: 'var(--text-primary)' }}>
          Daily Analysis Trend
        </h3>
        <div className="h-64">
          {lineData.length > 0 ? (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={lineData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: 8 }}
                />
                <Line type="monotone" dataKey="analyzed" name="Analyzed" stroke="var(--brand)" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="threats" name="Threats" stroke="var(--danger)" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          ) : (
            <div className="h-full flex items-center justify-center">
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No trend data available</p>
            </div>
          )}
        </div>
      </div>

      {topThreats.length > 0 && (
        <div className="card p-4 sm:p-6">
          <h3 className="font-heading font-600 text-base mb-4" style={{ color: 'var(--text-primary)' }}>
            Top Threats
          </h3>
          <div className="space-y-3">
            {topThreats.slice(0, 5).map(item => (
              <div key={item.id} className="flex items-start gap-3 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
                <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0" style={{ background: 'var(--danger-dim)' }}>
                  <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-500 truncate" style={{ color: 'var(--text-primary)' }}>
                    {item.subject}
                  </p>
                  <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                    {item.sender}
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <span className="text-xs font-600 px-2 py-0.5 rounded" style={{ background: 'var(--danger)', color: 'white' }}>
                    {item.riskScore}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </>
  );
}

function IndividualTab() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchId, setSearchId] = useState('');
  const [searchSubject, setSearchSubject] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [riskFilter, setRiskFilter] = useState('all');
  const [selectedItems, setSelectedItems] = useState([]);
  const [downloading, setDownloading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [page, setPage] = useState(1);

  const PAGE_SIZE = 50;

  useEffect(() => {
    const defaults = getDefaultIndividualDates();
    setStartDate(defaults.startDate);
    setEndDate(defaults.endDate);
  }, []);

  const loadItems = async (pg = 1, reset = true) => {
    if (pg === 1) setLoading(true);
    else setLoadingMore(true);
    
    try {
      const res = await analysisApi.getHistory({ page: pg, pageSize: PAGE_SIZE });
      const list = res.items ?? res.analyses ?? (Array.isArray(res) ? res : []);
      
      const filtered = list.filter(item => {
        const itemDate = item.created_at || item.analyzed_at;
        const inDateRange = (!startDate || itemDate >= startDate) && (!endDate || itemDate <= endDate + 'T23:59:59');
        return inDateRange;
      });
      
      setItems(prev => reset ? filtered : [...prev, ...filtered]);
      setHasMore(list.length === PAGE_SIZE);
      setPage(pg);
    } catch (err) {
      toast.error(err.message ?? 'Failed to load analyses');
    } finally {
      setLoading(false);
      setLoadingMore(false);
    }
  };

  useEffect(() => {
    loadItems(1, true);
  }, [startDate, endDate]);

  const filteredItems = useMemo(() => {
    return items.filter(item => {
      const s = score(item);
      
      const matchesId = !searchId || 
        (item.id && item.id.toLowerCase().includes(searchId.toLowerCase()));
      
      const subject = item.subject ?? item.email_metadata?.subject ?? item.file_name ?? '';
      const matchesSubject = !searchSubject || 
        subject.toLowerCase().includes(searchSubject.toLowerCase());
      
      const matchesRisk = riskFilter === 'all' || 
        (riskFilter === 'high' && s >= 70) ||
        (riskFilter === 'medium' && s >= 40 && s < 70) ||
        (riskFilter === 'safe' && s < 40);
      
      return matchesId && matchesSubject && matchesRisk;
    });
  }, [items, searchId, searchSubject, riskFilter]);

  const handleToggleSelect = (item) => {
    if (selectedItems.some(i => i.id === item.id)) {
      setSelectedItems(prev => prev.filter(i => i.id !== item.id));
    } else if (selectedItems.length < 5) {
      setSelectedItems(prev => [...prev, item]);
    } else {
      toast.warning('Maximum 5 analyses can be selected');
    }
  };

  const handleSelectAll = () => {
    if (selectedItems.length === filteredItems.length) {
      setSelectedItems([]);
    } else {
      const toSelect = filteredItems.slice(0, 5 - selectedItems.length);
      setSelectedItems(prev => {
        const existing = prev.filter(i => !filteredItems.some(f => f.id === i.id));
        return [...existing, ...toSelect];
      });
    }
  };

  const handleDownloadCombined = async () => {
    if (selectedItems.length === 0) {
      toast.info('Select at least one analysis');
      return;
    }
    
    try {
      setDownloading(true);
      toast.success('Generating combined report...');
      const ids = selectedItems.map(i => i.id);
      const blob = await analysisApi.downloadBatchReport(ids);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `phishcatcher-combined-${getTodayStr()}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Report downloaded');
    } catch (err) {
      toast.error(err.message ?? 'Download failed');
    } finally {
      setDownloading(false);
    }
  };

  const handleClearFilters = () => {
    setSearchId('');
    setSearchSubject('');
    setRiskFilter('all');
  };

  const today = getTodayStr();

  return (
    <>
      <div className="card p-4 sm:p-6">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div>
            <label className="form-label">Search by ID</label>
            <input
              type="text"
              placeholder="Partial ID match..."
              value={searchId}
              onChange={e => setSearchId(e.target.value)}
              className="input-base w-full"
            />
          </div>
          <div>
            <label className="form-label">Search by Subject</label>
            <input
              type="text"
              placeholder="Partial subject match..."
              value={searchSubject}
              onChange={e => setSearchSubject(e.target.value)}
              className="input-base w-full"
            />
          </div>
          <div>
            <label className="form-label">From</label>
            <input
              type="date"
              value={startDate}
              max={today}
              onChange={e => setStartDate(e.target.value)}
              className="input-base w-full"
            />
          </div>
          <div>
            <label className="form-label">To</label>
            <input
              type="date"
              value={endDate}
              min={startDate}
              max={today}
              onChange={e => setEndDate(e.target.value)}
              className="input-base w-full"
            />
          </div>
        </div>
        
        <div className="flex flex-wrap items-center gap-3 mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
          <div className="flex gap-2">
            {['all', 'high', 'medium', 'safe'].map(filter => (
              <button
                key={filter}
                onClick={() => setRiskFilter(filter)}
                className={`px-3 py-1.5 rounded-lg text-xs font-600 transition-all border ${
                  riskFilter === filter 
                    ? filter === 'high' ? 'bg-[var(--danger)] text-white border-[var(--danger)]' :
                      filter === 'medium' ? 'bg-[var(--threat)] text-white border-[var(--threat)]' :
                      filter === 'safe' ? 'bg-[var(--success)] text-white border-[var(--success)]' :
                      'bg-[var(--brand)] text-white border-[var(--brand)]'
                    : 'bg-[var(--bg-surface)] text-[var(--text-secondary)] border-[var(--border)]'
                }`}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>
          
          {(searchId || searchSubject || riskFilter !== 'all') && (
            <button
              onClick={handleClearFilters}
              className="text-xs flex items-center gap-1 px-2 py-1 rounded hover:bg-[var(--bg-elevated)]"
              style={{ color: 'var(--text-muted)' }}
            >
              <X className="w-3 h-3" />
              Clear filters
            </button>
          )}
          
          <div className="ml-auto flex items-center gap-3">
            <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {selectedItems.length} of 5 selected
            </span>
            <button
              onClick={handleDownloadCombined}
              disabled={downloading || selectedItems.length === 0}
              className="btn-primary h-9 px-4 text-sm flex items-center gap-2"
            >
              {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
              Download Combined
            </button>
          </div>
        </div>
      </div>

      <div className="rounded-2xl overflow-hidden" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        {loading ? (
          <div className="p-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading analyses…</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 mx-auto mb-4 opacity-25" style={{ color: 'var(--text-muted)' }} />
            <p className="font-heading font-700 text-base mb-1" style={{ color: 'var(--text-primary)' }}>
              No analyses found
            </p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Try adjusting your filters
            </p>
          </div>
        ) : (
          <>
            <table className="table-base">
              <thead>
                <tr>
                  <th className="w-10">
                    <button onClick={handleSelectAll} className="p-1">
                      {selectedItems.length === filteredItems.length && filteredItems.length > 0 ? (
                        <CheckSquare className="w-4 h-4" style={{ color: 'var(--brand)' }} />
                      ) : (
                        <Square className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                      )}
                    </button>
                  </th>
                  <th>Subject / File</th>
                  <th className="hidden sm:table-cell">Category</th>
                  <th>Risk</th>
                  <th className="hidden md:table-cell">Score</th>
                  <th className="hidden lg:table-cell">Analyzed</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map(a => {
                  const s = score(a);
                  const subject = a.subject ?? a.email_metadata?.subject ?? a.file_name ?? a.filename ?? 'Untitled';
                  const cat = a.threat_category ?? a.category ?? '—';
                  const date = a.created_at ?? a.analyzed_at;
                  const isSelected = selectedItems.some(i => i.id === a.id);
                  
                  return (
                    <tr key={a.id}>
                      <td className="w-10">
                        <button 
                          onClick={() => handleToggleSelect(a)}
                          disabled={!isSelected && selectedItems.length >= 5}
                          className="p-1"
                        >
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4" style={{ color: 'var(--brand)' }} />
                          ) : (
                            <Square className="w-4 h-4" style={{ color: selectedItems.length >= 5 ? 'var(--text-light)' : 'var(--text-muted)' }} />
                          )}
                        </button>
                      </td>
                      <td>
                        <Link 
                          to={`/analysis/${a.id}`}
                          className="font-500 text-sm hover:underline truncate block max-w-[200px]"
                          style={{ color: 'var(--text-primary)' }}
                        >
                          {subject}
                        </Link>
                      </td>
                      <td className="hidden sm:table-cell">
                        <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{cat}</span>
                      </td>
                      <td><span className={riskBadge(s)}>{riskLabel(s)}</span></td>
                      <td className="hidden md:table-cell">
                        <span className="font-heading font-700 text-sm" style={{ color: riskColor(s) }}>{s}</span>
                      </td>
                      <td className="hidden lg:table-cell">
                        <span className="text-xs flex items-center gap-1" style={{ color: 'var(--text-muted)' }}>
                          <Clock className="w-3 h-3" />{timeAgo(date)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {hasMore && (
              <div className="p-4 text-center" style={{ borderTop: '1px solid var(--border)' }}>
                <button
                  onClick={() => loadItems(page + 1, false)}
                  disabled={loadingMore}
                  className="btn-ghost text-sm h-9 px-6"
                >
                  {loadingMore ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Load more'}
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </>
  );
}
