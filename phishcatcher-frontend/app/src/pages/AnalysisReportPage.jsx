/**
 * AnalysisReport.jsx
 * Full threat report for a single analysis: score, indicators, links, headers, recommendations.
 */

import React, { useState, useEffect } from 'react';
import { useNavigate, useParams, Link } from 'react-router-dom';
import { toast } from 'sonner';
import { 
  AlertTriangle, 
  Clock, 
  Download, 
  Trash2, 
  Loader2, 
  Mail,
  Shield,
  Link as LinkIcon,
  Paperclip,
  ArrowLeft, CheckCircle, ChevronDown, ChevronUp, ExternalLink, Globe, User,
  Eye, EyeOff, Info, FileText, Search
} from 'lucide-react';
import { analysisApi } from '@/lib/api';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import MLAnalysisCard from '@/components/MLAnalysisCard';
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';

/* ─── Sensitive text component ──────────────────────────────────────────── */
function SensitiveText({ children, blurSensitive, className = '' }) {
  return (
    <span className={`${blurSensitive ? 'blur-sm select-none' : ''} ${className}`}>
      {children}
    </span>
  );
}

/* ─── Helpers ──────────────────────────────────────────────────────────── */
function getScore(a)    { return a.threat_score ?? a.risk_score ?? 0; }
function riskLabel(s)   { return s >= 70 ? 'High Risk' : s >= 40 ? 'Medium Risk' : 'Safe'; }
function riskColor(s)   { return s >= 70 ? 'var(--danger)'  : s >= 40 ? 'var(--threat)'  : 'var(--success)'; }
function riskBgColor(s) { return s >= 70 ? 'var(--danger-dim)' : s >= 40 ? 'var(--threat-dim)' : 'var(--success-dim)'; }
function riskBadge(s)   { return s >= 70 ? 'badge badge-danger' : s >= 40 ? 'badge badge-threat' : 'badge badge-success'; }
function fmtDate(iso)   {
  if (!iso) return '—';
  return new Date(iso).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

/* ─── Expandable section ───────────────────────────────────────────────── */
function Section({ title, icon: Icon, accentColor, children, open: defaultOpen = true }) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="rounded-2xl overflow-hidden"
      style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-5 py-4"
        style={{ borderBottom: open ? '1px solid var(--border)' : 'none' }}
      >
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{
              background: accentColor ? `${accentColor}1a` : 'var(--bg-elevated)',
              color: accentColor ?? 'var(--text-muted)',
            }}>
            <Icon className="w-3.5 h-3.5" />
          </div>
          <span className="font-heading font-700 text-sm" style={{ color: 'var(--text-primary)' }}>{title}</span>
        </div>
        {open
          ? <ChevronUp  className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
          : <ChevronDown className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />}
      </button>
      {open && <div className="px-5 py-4">{children}</div>}
    </div>
  );
}

/* ─── Info row ─────────────────────────────────────────────────────────── */
function InfoRow({ label, value, warn }) {
  return (
    <div className="flex gap-3 py-2" style={{ borderBottom: '1px solid var(--border)' }}>
      <span className="text-xs font-600 uppercase tracking-wide w-24 shrink-0 pt-0.5"
        style={{ color: 'var(--text-muted)' }}>
        {label}
      </span>
      <span className="text-sm flex items-center gap-1.5 flex-wrap break-all"
        style={{ color: warn ? 'var(--danger)' : 'var(--text-secondary)' }}>
        {warn && <AlertTriangle className="w-3.5 h-3.5 shrink-0" />}
        {value || '—'}
      </span>
    </div>
  );
}

/* ─── Main ─────────────────────────────────────────────────────────────── */
export default function AnalysisReportPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [analysis, setAnalysis] = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState('');
  const [deleting, setDeleting] = useState(false);
  const [blurSensitive, setBlurSensitive] = useState(true);
  const [showHeaders, setShowHeaders] = useState(false);
  const [expandedFinding, setExpandedFinding] = useState(null);
  const [analysisList, setAnalysisList] = useState([]);

  // Fetch analysis list for dropdown
  useEffect(() => {
    const fetchAnalysisList = async () => {
      try {
        const response = await analysisApi.getHistory({ page: 1, pageSize: 50 });
        if (response.items) {
          setAnalysisList(response.items);
        }
      } catch (err) {
        console.error('Failed to fetch analysis list:', err);
      }
    };
    fetchAnalysisList();
  }, []);

  useEffect(() => {
    // Validate ID - be permissive since IDs can come in various formats
    const isValidId = (id) => {
      if (!id || typeof id !== 'string') return false;
      if (id === 'None' || id === 'null' || id === 'undefined') return false;
      if (id.startsWith('fallback_')) return false;
      return id.length >= 8;
    };
    
    if (!isValidId(id)) {
      setError('Invalid analysis ID');
      setLoading(false);
      return;
    }
    
    (async () => {
      setLoading(true);
      setError('');
      try {
        const data = await analysisApi.getAnalysis(id);
        setAnalysis(data);
      } catch (err) {
        console.error('Failed to load analysis:', err);
        setError(err.message ?? 'Failed to load analysis report.');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  const handleAnalysisSelect = (newId) => {
    if (newId && newId !== id) {
      navigate(`/analysis/${newId}`, { replace: true });
    }
  };

  const handleDelete = async () => {
    if (!window.confirm('Delete this analysis? This cannot be undone.')) return;
    setDeleting(true);
    try {
      await analysisApi.deleteAnalysis(id);
      toast.success('Analysis deleted');
      navigate('/analysis', { replace: true });
    } catch (err) {
      toast.error(err.message ?? 'Delete failed');
      setDeleting(false);
    }
  };

  const handleDownload = async () => {
    try {
      toast.success('Generating report...');
      const blob = await analysisApi.downloadReport(id, 'pdf');
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `phishcatcher-report-${id}.pdf`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success('Report downloaded');
    } catch (err) {
      toast.error(err.message ?? 'Download failed');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin mx-auto mb-3" style={{ color: 'var(--brand)' }} />
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading report…</p>
        </div>
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="max-w-lg mx-auto text-center py-16">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
          style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
          <AlertTriangle className="w-7 h-7" />
        </div>
        <h2 className="font-heading font-700 text-xl mb-2" style={{ color: 'var(--text-primary)' }}>
          Report not found
        </h2>
        <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
          {error || 'This analysis report could not be found.'}
        </p>
        <Link to="/analysis" className="btn-ghost inline-flex">
          <ArrowLeft className="w-4 h-4" /> Back to history
        </Link>
      </div>
    );
  }

  const s          = getScore(analysis);
  const subject    = analysis.subject ?? analysis.email_metadata?.subject ?? analysis.file_name ?? analysis.email_subject ?? analysis.filename ?? 'Untitled';
  const category   = analysis.threat_category ?? analysis.category ?? '—';
  const summary    = analysis.summary ?? analysis.description ?? '';
  const sender     = analysis.email_metadata?.sender ?? analysis.sender ?? analysis.from ?? analysis.email_headers?.['From'] ?? '';
  const replyTo    = analysis.email_metadata?.reply_to ?? analysis.reply_to ?? analysis.email_headers?.['Reply-To'] ?? '';
  const indicators = analysis.indicators ?? analysis.threat_indicators ?? [];
  const links      = analysis.malicious_urls ?? analysis.suspicious_links ?? analysis.links_analyzed ?? [];
  const attachments = analysis.attachments_analyzed ?? [];
  const recs       = analysis.recommendations ?? [];
  const headers    = analysis.email_headers ?? {};

  const riskColors = {
    bg: s >= 70 ? 'rgba(255, 77, 141, 0.15)' : s >= 40 ? 'rgba(255, 209, 102, 0.15)' : 'rgba(39, 211, 199, 0.15)',
    text: s >= 70 ? '#FF4D8D' : s >= 40 ? '#FFD166' : '#27D3C7',
    border: s >= 70 ? 'rgba(255, 77, 141, 0.25)' : s >= 40 ? 'rgba(255, 209, 102, 0.25)' : 'rgba(39, 211, 199, 0.25)',
    label: s >= 70 ? 'High Risk' : s >= 40 ? 'Medium Risk' : 'Safe'
  };

  const severityColors = {
    critical: 'rgba(255, 77, 141, 0.15) #FF4D8D rgba(255, 77, 141, 0.25)',
    high: 'rgba(255, 209, 102, 0.15) #FFD166 rgba(255, 209, 102, 0.25)',
    medium: 'rgba(123, 97, 255, 0.15) #7B61FF rgba(123, 97, 255, 0.25)',
    low: 'rgba(39, 211, 199, 0.15) #27D3C7 rgba(39, 211, 199, 0.25)',
  };

  return (
    <div className="space-y-4 sm:space-y-6">

      {/* Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="flex items-center gap-3 sm:gap-4">
          <button
            onClick={() => navigate('/analysis')}
            className="w-9 w-9 sm:w-10 h-9 sm:h-10 rounded-lg border bg-transparent hover:bg-brand-dim flex items-center justify-center transition-colors"
            style={{ borderColor: 'var(--brand)', color: 'var(--brand)' }}
          >
            <ArrowLeft className="w-4 sm:w-5 h-4 sm:h-5" />
          </button>
          <div>
            <h1 className="text-xl sm:text-2xl font-heading font-800" style={{ color: 'var(--text-primary)' }}>Analysis Results</h1>
            <p className="text-xs sm:text-sm" style={{ color: 'var(--text-muted)' }}>ID: {id} • Analyzed {fmtDate(analysis.created_at ?? analysis.analyzed_at)}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* Analysis ID Dropdown */}
          <Select value={id} onValueChange={handleAnalysisSelect}>
            <SelectTrigger 
              className="h-9 sm:h-10 min-w-[180px] sm:min-w-[240px] text-xs sm:text-sm border rounded-lg transition-colors"
              style={{ 
                borderColor: 'var(--brand)', 
                color: 'var(--text-primary)',
                backgroundColor: 'transparent'
              }}
            >
              <SelectValue placeholder="Select analysis..." />
            </SelectTrigger>
            <SelectContent className="max-h-[400px]">
              <div className="px-2 py-1.5 text-[10px] text-muted-foreground uppercase tracking-wide font-semibold">
                Recent Analyses
              </div>
              {analysisList.length === 0 ? (
                <div className="px-2 py-4 text-center text-sm text-muted-foreground">
                  No analyses found
                </div>
              ) : (
                analysisList.map((item) => (
                  <SelectItem 
                    key={item.id} 
                    value={item.id} 
                    className="text-xs py-2 cursor-pointer hover:bg-brand-dim"
                  >
                    <div className="flex flex-col gap-0.5">
                      <span className="font-mono text-[10px] sm:text-xs truncate max-w-[220px]">{item.id}</span>
                      <span className="text-[9px] sm:text-[10px] text-muted-foreground truncate">
                        {item.subject || item.file_name || 'Untitled'} • {item.risk_score ?? 0}%
                      </span>
                    </div>
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          
          {/* Blur Toggle */}
          <button
            onClick={() => setBlurSensitive(!blurSensitive)}
            className="h-9 sm:h-10 px-3 rounded-lg border bg-transparent hover:bg-brand-dim text-xs sm:text-sm flex items-center gap-1.5 transition-colors"
            style={{ borderColor: 'var(--brand)', color: 'var(--brand)' }}
          >
            {blurSensitive ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
            {blurSensitive ? 'Show' : 'Hide'}
          </button>
          
          <button
            onClick={handleDownload}
            className="h-9 sm:h-10 px-3 rounded-lg border bg-transparent hover:bg-brand-dim text-xs sm:text-sm flex items-center gap-1.5 transition-colors"
            style={{ borderColor: 'var(--brand)', color: 'var(--brand)' }}
          >
            <Download className="w-4 h-4" />
            <span className="hidden sm:inline">Download</span>
          </button>
        </div>
      </div>

      {/* Main Analysis Card */}
      <div className="card-strong p-5 sm:p-8">
        <div className="flex flex-col lg:flex-row gap-6 sm:gap-8">
          {/* Left: Email Info */}
          <div className="flex-1">
            {/* Email Header */}
            <div className="flex items-start gap-3 sm:gap-4 mb-5 sm:mb-6">
              <div className="w-11 sm:w-14 h-11 sm:h-14 rounded-xl flex items-center justify-center flex-shrink-0"
                style={{ background: riskColors.bg }}>
                <Mail className="w-5 sm:w-7 h-5 sm:h-7" style={{ color: riskColors.text }} />
              </div>
              <div className="flex-1 min-w-0">
                <h2 className="text-base sm:text-xl font-heading font-600 mb-1" style={{ color: 'var(--text-primary)' }}>
                  <SensitiveText blurSensitive={blurSensitive}>{subject}</SensitiveText>
                </h2>
                <div className="flex flex-wrap items-center gap-1.5 sm:gap-2 text-xs sm:text-sm">
                  <span style={{ color: 'var(--text-muted)' }}>From:</span>
                  <span style={{ color: 'var(--text-primary)' }}><SensitiveText blurSensitive={blurSensitive}>{sender}</SensitiveText></span>
                </div>
                {analysis.email_metadata?.recipient && (
                  <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm mt-0.5">
                    <span style={{ color: 'var(--text-muted)' }}>To:</span>
                    <span style={{ color: 'var(--text-primary)' }}><SensitiveText blurSensitive={blurSensitive}>{Array.isArray(analysis.email_metadata.recipient) ? analysis.email_metadata.recipient[0] : analysis.email_metadata.recipient}</SensitiveText></span>
                  </div>
                )}
              </div>
            </div>

            {/* Risk Score Display */}
            <div className="flex flex-col sm:flex-row items-center gap-4 sm:gap-6 mb-5 sm:mb-6">
              <div className="w-20 sm:w-24 h-20 sm:h-24 rounded-2xl flex flex-col items-center justify-center flex-shrink-0"
                style={{ background: riskColors.bg, border: `2px solid ${riskColors.border}` }}>
                <span className="text-2xl sm:text-3xl font-mono font-800" style={{ color: riskColors.text }}>
                  {s}%
                </span>
                <span className="text-xs" style={{ color: riskColors.text }}>Risk</span>
              </div>
              <div className="text-center sm:text-left">
                <div className="inline-block px-3 py-1 rounded-lg text-xs font-medium mb-2" 
                  style={{ background: riskColors.bg, color: riskColors.text, border: `1px solid ${riskColors.border}` }}>
                  {riskColors.label}
                </div>
                <p className="text-xs sm:text-sm max-w-md" style={{ color: 'var(--text-muted)' }}>
                  {s >= 70 ? 'This email exhibits multiple characteristics commonly associated with phishing attempts. Review the findings below and take appropriate precautions.' 
                    : s >= 40 ? 'This email has some suspicious elements that require attention. Review the findings below.'
                    : 'No significant threats detected in this email. It appears to be safe.'}
                </p>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-3 gap-2 sm:gap-4">
              <div className="p-3 sm:p-4 rounded-xl" style={{ background: 'rgba(123, 97, 255, 0.1)', border: '1px solid rgba(123, 97, 255, 0.15)' }}>
                <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
                  <Globe className="w-3.5 sm:w-4 h-3.5 sm:h-4" style={{ color: '#7B61FF' }} />
                  <span className="text-[10px] sm:text-xs" style={{ color: 'var(--text-muted)' }}>Links</span>
                </div>
                <p className="text-sm sm:text-lg font-mono font-medium" style={{ color: '#7B61FF' }}>
                  {analysis.links_analyzed?.length ?? 0}
                </p>
              </div>
              <div className="p-3 sm:p-4 rounded-xl" style={{ background: 'rgba(123, 97, 255, 0.1)', border: '1px solid rgba(123, 97, 255, 0.15)' }}>
                <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
                  <Paperclip className="w-3.5 sm:w-4 h-3.5 sm:h-4" style={{ color: '#7B61FF' }} />
                  <span className="text-[10px] sm:text-xs" style={{ color: 'var(--text-muted)' }}>Attachments</span>
                </div>
                <p className="text-sm sm:text-lg font-mono font-medium" style={{ color: '#7B61FF' }}>
                  {analysis.attachments_analyzed?.length ?? 0}
                </p>
              </div>
              <div className="p-3 sm:p-4 rounded-xl" style={{ background: 'rgba(39, 211, 199, 0.1)', border: '1px solid rgba(39, 211, 199, 0.15)' }}>
                <div className="flex items-center gap-1.5 sm:gap-2 mb-1.5 sm:mb-2">
                  <Clock className="w-3.5 sm:w-4 h-3.5 sm:h-4" style={{ color: '#27D3C7' }} />
                  <span className="text-[10px] sm:text-xs" style={{ color: 'var(--text-muted)' }}>Analysis Time</span>
                </div>
                <p className="text-sm sm:text-lg font-mono font-medium" style={{ color: '#27D3C7' }}>&lt;1s</p>
              </div>
            </div>
          </div>

          {/* Right: Radar Chart */}
          {analysis.risk_factors && (
            <div className="lg:w-56 xl:w-64">
              <h3 className="text-xs sm:text-sm font-medium mb-3 sm:mb-4" style={{ color: 'var(--text-muted)' }}>Risk Factor Analysis</h3>
              <div className="h-48 sm:h-56 lg:h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart data={[
                    { factor: 'Sender', value: analysis.risk_factors.sender_reputation ?? 0, fullMark: 100 },
                    { factor: 'Content', value: analysis.risk_factors.content_risk ?? 0, fullMark: 100 },
                    { factor: 'Links', value: analysis.risk_factors.link_risk ?? 0, fullMark: 100 },
                    { factor: 'Attachments', value: analysis.risk_factors.attachment_risk ?? 0, fullMark: 100 },
                    { factor: 'Auth', value: analysis.risk_factors.authentication_risk ?? 0, fullMark: 100 },
                  ]}>
                    <PolarGrid stroke="rgba(123, 97, 255, 0.2)" />
                    <PolarAngleAxis dataKey="factor" tick={{ fill: '#A7B0D5', fontSize: 10 }} />
                    <PolarRadiusAxis angle={90} domain={[0, 100]} tick={false} axisLine={false} />
                    <Radar
                      name="Risk Score"
                      dataKey="value"
                      stroke={riskColors.text}
                      strokeWidth={2}
                      fill={riskColors.text}
                      fillOpacity={0.25}
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#0F1635', 
                        border: '1px solid rgba(123, 97, 255, 0.25)',
                        borderRadius: '12px',
                        color: 'white'
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Summary ── */}
      {summary && (
        <Section title="ML Summary" icon={Shield} accentColor="var(--brand)">
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{summary}</p>
        </Section>
      )}

      {/* ── ML Analysis ── */}
      <MLAnalysisCard analysis={analysis} />

      {/* ── Score Breakdown ── */}
      {analysis.risk_factors && (
        <Section title="Score Breakdown" icon={Shield} accentColor="var(--brand)">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Radar Chart */}
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={[
                  { subject: 'Sender', value: analysis.risk_factors.sender_reputation, fullMark: 100 },
                  { subject: 'Content', value: analysis.risk_factors.content_risk, fullMark: 100 },
                  { subject: 'Links', value: analysis.risk_factors.link_risk, fullMark: 100 },
                  { subject: 'Attachments', value: analysis.risk_factors.attachment_risk, fullMark: 100 },
                  { subject: 'Auth', value: analysis.risk_factors.authentication_risk, fullMark: 100 },
                ]}>
                  <PolarGrid stroke="var(--border)" />
                  <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 12 }} />
                  <PolarRadiusAxis angle={30} domain={[0, 100]} tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                  <Radar
                    name="Risk Score"
                    dataKey="value"
                    stroke={s >= 70 ? 'var(--danger)' : s >= 40 ? 'var(--threat)' : 'var(--success)'}
                    fill={s >= 70 ? 'var(--danger)' : s >= 40 ? 'var(--threat)' : 'var(--success)'}
                    fillOpacity={0.3}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            
            {/* Score Cards */}
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Sender Reputation', value: analysis.risk_factors.sender_reputation, key: 'sender_reputation' },
                { label: 'Content Risk', value: analysis.risk_factors.content_risk, key: 'content_risk' },
                { label: 'Link Risk', value: analysis.risk_factors.link_risk, key: 'link_risk' },
                { label: 'Attachment Risk', value: analysis.risk_factors.attachment_risk, key: 'attachment_risk' },
                { label: 'Authentication', value: analysis.risk_factors.authentication_risk, key: 'authentication_risk' },
              ].map(item => (
                <div key={item.key} className="rounded-xl p-3" style={{ 
                  background: item.value >= 70 ? 'var(--danger-dim)' : item.value >= 40 ? 'var(--threat-dim)' : 'var(--success-dim)',
                  border: `1px solid ${item.value >= 70 ? 'var(--danger)' : item.value >= 40 ? 'var(--threat)' : 'var(--success)'}`
                }}>
                  <div className="font-heading font-700 text-lg" style={{ 
                    color: item.value >= 70 ? 'var(--danger)' : item.value >= 40 ? 'var(--threat)' : 'var(--success)'
                  }}>{item.value}</div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{item.label}</div>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-4 p-4 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
            <h4 className="font-600 text-sm mb-2" style={{ color: 'var(--text-primary)' }}>
              Why this score?
            </h4>
            <ul className="text-sm space-y-2" style={{ color: 'var(--text-secondary)' }}>
              {analysis.risk_factors.sender_reputation >= 70 && (
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-[var(--danger)] mt-0.5" />
                  <span>Sender domain has poor reputation or is newly registered</span>
                </li>
              )}
              {analysis.risk_factors.content_risk >= 70 && (
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-[var(--danger)] mt-0.5" />
                  <span>Email content contains suspicious patterns (urgency, threats, errors)</span>
                </li>
              )}
              {analysis.risk_factors.link_risk >= 70 && (
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-[var(--danger)] mt-0.5" />
                  <span>Contains malicious or suspicious URLs</span>
                </li>
              )}
              {analysis.risk_factors.attachment_risk >= 70 && (
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-[var(--danger)] mt-0.5" />
                  <span>Contains dangerous or suspicious attachments</span>
                </li>
              )}
              {analysis.risk_factors.authentication_risk >= 70 && (
                <li className="flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 text-[var(--danger)] mt-0.5" />
                  <span>Email failed authentication checks (SPF/DKIM/DMARC)</span>
                </li>
              )}
              {s < 40 && (
                <li className="flex items-start gap-2">
                  <CheckCircle className="w-4 h-4 text-[var(--success)] mt-0.5" />
                  <span>No significant threats detected</span>
                </li>
              )}
            </ul>
          </div>
        </Section>
      )}

      {/* ── Findings ── */}
      {(analysis.findings?.length > 0) && (
        <div className="card p-4 sm:p-6">
          <h3 className="text-base sm:text-lg font-heading font-600 mb-4 sm:mb-6" style={{ color: 'var(--text-primary)' }}>Detailed Findings</h3>
          <div className="space-y-3 sm:space-y-4">
            {analysis.findings.map((finding, i) => {
              const isExpanded = expandedFinding === i;
              const severityColor = finding.severity === 'critical' ? 'var(--danger)' 
                : finding.severity === 'high' ? 'var(--threat)' 
                : 'var(--brand)';
              return (
                <div className="border rounded-xl overflow-hidden" style={{ borderColor: 'var(--border)' }}>
                  <button
                    onClick={() => setExpandedFinding(isExpanded ? null : i)}
                    className="w-full flex items-center gap-3 sm:gap-4 p-3 sm:p-4 hover:bg-brand-dim transition-colors text-left"
                    style={{ background: 'var(--bg-elevated)' }}
                  >
                    <div className={`w-8 sm:w-10 h-8 sm:h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
                      finding.severity === 'critical' ? 'bg-danger-dim' :
                      finding.severity === 'high' ? 'bg-threat-dim' :
                      'bg-brand-dim'
                    }`}>
                      {finding.type === 'domain' && <Globe className={`w-4 sm:w-5 h-4 sm:h-5 ${
                        finding.severity === 'critical' ? 'text-danger' :
                        finding.severity === 'high' ? 'text-threat' :
                        'text-brand'
                      }`} />}
                      {finding.type === 'content' && <FileText className={`w-4 sm:w-5 h-4 sm:h-5 ${
                        finding.severity === 'critical' ? 'text-danger' :
                        finding.severity === 'high' ? 'text-threat' :
                        'text-brand'
                      }`} />}
                      {finding.type === 'link' && <LinkIcon className={`w-4 sm:w-5 h-4 sm:h-5 ${
                        finding.severity === 'critical' ? 'text-danger' :
                        finding.severity === 'high' ? 'text-threat' :
                        'text-brand'
                      }`} />}
                      {finding.type === 'sender' && <User className={`w-4 sm:w-5 h-4 sm:h-5 ${
                        finding.severity === 'critical' ? 'text-danger' :
                        finding.severity === 'high' ? 'text-threat' :
                        'text-brand'
                      }`} />}
                      {!finding.type && <AlertTriangle className={`w-4 sm:w-5 h-4 sm:h-5 ${
                        finding.severity === 'critical' ? 'text-danger' :
                        finding.severity === 'high' ? 'text-threat' :
                        'text-brand'
                      }`} />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="font-medium text-sm sm:text-base" style={{ color: 'var(--text-primary)' }}>{finding.title}</h4>
                        <span className={`text-[10px] px-2 py-0.5 rounded ${
                          finding.severity === 'critical' ? 'bg-danger-dim text-danger' :
                          finding.severity === 'high' ? 'bg-threat-dim text-threat' :
                          finding.severity === 'medium' ? 'bg-brand-dim text-brand' :
                          'bg-success-dim text-success'
                        }`}>
                          {finding.severity?.toUpperCase() || 'INFO'}
                        </span>
                      </div>
                      <p className="text-xs sm:text-sm mt-0.5 line-clamp-1" style={{ color: 'var(--text-muted)' }}>{finding.description}</p>
                    </div>
                    {isExpanded ? (
                      <ChevronUp className="w-4 sm:w-5 h-4 sm:h-5" style={{ color: 'var(--text-muted)' }} />
                    ) : (
                      <ChevronDown className="w-4 sm:w-5 h-4 sm:h-5" style={{ color: 'var(--text-muted)' }} />
                    )}
                  </button>
                  
                  {isExpanded && (
                    <div className="px-3 sm:px-4 pb-3 sm:pb-4 pt-2" style={{ background: 'var(--bg-surface)', borderTop: '1px solid var(--border)' }}>
                      <div className="flex items-start gap-2 sm:gap-3">
                        <Info className="w-4 sm:w-5 h-4 sm:h-5 mt-0.5 flex-shrink-0" style={{ color: 'var(--brand)' }} />
                        <div>
                          <p className="text-xs sm:text-sm mb-2" style={{ color: 'var(--text-secondary)' }}>{finding.description}</p>
                          <div className="flex items-start gap-2">
                            <CheckCircle className="w-3.5 sm:w-4 h-3.5 sm:h-4 mt-0.5 flex-shrink-0" style={{ color: 'var(--success)' }} />
                            <p className="text-xs sm:text-sm" style={{ color: 'var(--text-muted)' }}>
                              <span style={{ color: 'var(--success)', fontWeight: 500 }}>Recommendation: </span>
                              {finding.recommendation}
                            </p>
                          </div>
                          {finding.evidence && (
                            <div className="mt-2 p-2 rounded-lg text-xs font-mono" style={{ background: 'var(--bg-surface)', color: 'var(--text-secondary)' }}>
                              {JSON.stringify(finding.evidence, null, 2)}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Email details ── */}
      <Section title="Email Details" icon={Mail} accentColor="var(--brand)">
        <div style={{ borderTop: '1px solid var(--border)' }}>
          <InfoRow label="Subject" value={subject} />
          <InfoRow label="From"    value={sender}   warn={s >= 70} />
          {analysis.email_metadata?.recipient && (
            <InfoRow label="To" value={analysis.email_metadata.recipient} />
          )}
          {analysis.email_metadata?.cc?.length > 0 && (
            <InfoRow label="CC" value={analysis.email_metadata.cc.join(', ')} />
          )}
          {replyTo && <InfoRow label="Reply-To" value={replyTo} warn={replyTo !== sender && !!replyTo} />}
          {analysis.email_metadata?.date && (
            <InfoRow label="Date" value={fmtDate(analysis.email_metadata.date)} />
          )}
          {analysis.email_metadata?.message_id && <InfoRow label="Msg-ID" value={analysis.email_metadata.message_id} />}
        </div>
      </Section>

      {/* ── Threat Intelligence ── */}
      {(analysis.threat_intelligence || analysis.ml_analysis) && (
        <Section title="Threat Intelligence Analysis" icon={Shield} accentColor="var(--danger)" open={s >= 40}>
          <div className="space-y-6">
            {/* Overall TI Summary */}
            {analysis.threat_intelligence && (
              <>
                <div className="grid grid-cols-3 gap-3">
                  <div className="p-4 rounded-xl text-center" style={{ background: 'var(--bg-elevated)' }}>
                    <div className="font-heading font-700 text-2xl" style={{ 
                      color: analysis.threat_intelligence.overall_risk_score >= 70 ? 'var(--danger)' 
                        : analysis.threat_intelligence.overall_risk_score >= 40 ? 'var(--threat)' : 'var(--success)' 
                    }}>
                      {analysis.threat_intelligence.overall_risk_score ?? 0}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>TI Risk Score</div>
                  </div>
                  <div className="p-4 rounded-xl text-center" style={{ background: 'var(--bg-elevated)' }}>
                    <div className="font-heading font-700 text-2xl" style={{ color: 'var(--danger)' }}>
                      {analysis.threat_intelligence.indicators?.length ?? 0}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Threats Found</div>
                  </div>
                  <div className="p-4 rounded-xl text-center" style={{ background: 'var(--bg-elevated)' }}>
                    <div className="font-heading font-700 text-2xl" style={{ color: 'var(--warning)' }}>
                      {analysis.threat_intelligence.warnings?.length ?? 0}
                    </div>
                    <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Warnings</div>
                  </div>
                </div>

                {/* API Results Breakdown */}
                <div>
                  <h4 className="font-600 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>
                    API Check Results
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {/* AbuseIPDB */}
                    <div className="p-3 rounded-xl" style={{ 
                      background: analysis.threat_intelligence.indicators?.some(i => i.api_name === 'abuseipdb' && i.details?.malicious) 
                        ? 'var(--danger-dim)' : 'var(--success-dim)',
                      border: `1px solid ${analysis.threat_intelligence.indicators?.some(i => i.api_name === 'abuseipdb' && i.details?.malicious) ? 'var(--danger)' : 'var(--success)'}`
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        {analysis.threat_intelligence.indicators?.some(i => i.api_name === 'abuseipdb' && i.details?.malicious) ? (
                          <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                        ) : (
                          <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                        )}
                        <span className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>AbuseIPDB (IP)</span>
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {analysis.threat_intelligence.indicators?.find(i => i.api_name === 'abuseipdb')?.details?.malicious 
                          ? `Malicious - ${analysis.threat_intelligence.indicators.find(i => i.api_name === 'abuseipdb').details.malicious}`
                          : 'IP reputation clean'}
                      </div>
                    </div>

                    {/* AbuseIPDB Domain */}
                    <div className="p-3 rounded-xl" style={{ 
                      background: analysis.threat_intelligence.indicators?.some(i => i.api_name === 'abuseipdb_domain' && i.details?.num_reported_ips > 0) 
                        ? 'var(--danger-dim)' : 'var(--success-dim)',
                      border: `1px solid ${analysis.threat_intelligence.indicators?.some(i => i.api_name === 'abuseipdb_domain' && i.details?.num_reported_ips > 0) ? 'var(--danger)' : 'var(--success)'}`
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        {analysis.threat_intelligence.indicators?.some(i => i.api_name === 'abuseipdb_domain' && i.details?.num_reported_ips > 0) ? (
                          <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                        ) : (
                          <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                        )}
                        <span className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>AbuseIPDB (Domain)</span>
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {(() => {
                          const ind = analysis.threat_intelligence.indicators?.find(i => i.api_name === 'abuseipdb_domain');
                          return ind?.details?.num_reported_ips > 0 
                            ? `${ind.details.num_reported_ips} IPs reported, ${ind.details.num_distinct_ips} distinct`
                            : 'Domain clean';
                        })()}
                      </div>
                    </div>

                    {/* RDAP (Domain Age) */}
                    <div className="p-3 rounded-xl" style={{ 
                      background: analysis.threat_intelligence.indicators?.some(i => i.api_name === 'rdap' && i.details?.age_in_days < 30) 
                        ? 'var(--threat-dim)' : 'var(--success-dim)',
                      border: `1px solid ${analysis.threat_intelligence.indicators?.some(i => i.api_name === 'rdap' && i.details?.age_in_days < 30) ? 'var(--threat)' : 'var(--success)'}`
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        {analysis.threat_intelligence.indicators?.some(i => i.api_name === 'rdap' && i.details?.age_in_days < 30) ? (
                          <AlertTriangle className="w-4 h-4" style={{ color: 'var(--threat)' }} />
                        ) : (
                          <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                        )}
                        <span className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>RDAP (Domain Age)</span>
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {(() => {
                          const ind = analysis.threat_intelligence.indicators?.find(i => i.api_name === 'rdap');
                          return ind?.details?.age_in_days !== undefined
                            ? `Domain age: ${ind.details.age_in_days} days`
                            : 'Check unavailable';
                        })()}
                      </div>
                    </div>

                    {/* PhishTank */}
                    <div className="p-3 rounded-xl" style={{ 
                      background: analysis.threat_intelligence.indicators?.some(i => i.api_name === 'phishtank' && i.details?.in_database) 
                        ? 'var(--danger-dim)' : 'var(--success-dim)',
                      border: `1px solid ${analysis.threat_intelligence.indicators?.some(i => i.api_name === 'phishtank' && i.details?.in_database) ? 'var(--danger)' : 'var(--success)'}`
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        {analysis.threat_intelligence.indicators?.some(i => i.api_name === 'phishtank' && i.details?.in_database) ? (
                          <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                        ) : (
                          <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                        )}
                        <span className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>PhishTank</span>
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {analysis.threat_intelligence.indicators?.find(i => i.api_name === 'phishtank')?.details?.in_database 
                          ? 'URL found in phishing database'
                          : 'URL not in phishing database'}
                      </div>
                    </div>

                    {/* VirusTotal */}
                    <div className="p-3 rounded-xl" style={{ 
                      background: analysis.threat_intelligence.indicators?.some(i => i.api_name === 'virustotal' && i.details?.malicious > 0) 
                        ? 'var(--danger-dim)' : 'var(--success-dim)',
                      border: `1px solid ${analysis.threat_intelligence.indicators?.some(i => i.api_name === 'virustotal' && i.details?.malicious > 0) ? 'var(--danger)' : 'var(--success)'}`
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        {analysis.threat_intelligence.indicators?.some(i => i.api_name === 'virustotal' && i.details?.malicious > 0) ? (
                          <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                        ) : (
                          <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                        )}
                        <span className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>VirusTotal</span>
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {(() => {
                          const ind = analysis.threat_intelligence.indicators?.find(i => i.api_name === 'virustotal');
                          return ind?.details?.malicious > 0 
                            ? `${ind.details.malicious} detections`
                            : 'No threats detected';
                        })()}
                      </div>
                    </div>

                    {/* URLScan */}
                    <div className="p-3 rounded-xl" style={{ 
                      background: analysis.threat_intelligence.indicators?.some(i => i.api_name === 'urlscan' && i.details?.categories?.length > 0) 
                        ? 'var(--threat-dim)' : 'var(--success-dim)',
                      border: `1px solid ${analysis.threat_intelligence.indicators?.some(i => i.api_name === 'urlscan' && i.details?.categories?.length > 0) ? 'var(--threat)' : 'var(--success)'}`
                    }}>
                      <div className="flex items-center gap-2 mb-2">
                        {analysis.threat_intelligence.indicators?.some(i => i.api_name === 'urlscan' && i.details?.categories?.length > 0) ? (
                          <AlertTriangle className="w-4 h-4" style={{ color: 'var(--threat)' }} />
                        ) : (
                          <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                        )}
                        <span className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>URLScan</span>
                      </div>
                      <div className="text-xs" style={{ color: 'var(--text-muted)' }}>
                        {(() => {
                          const ind = analysis.threat_intelligence.indicators?.find(i => i.api_name === 'urlscan');
                          return ind?.details?.categories?.length > 0
                            ? `Categories: ${ind.details.categories.join(', ')}`
                            : 'Scan results clean';
                        })()}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Detailed Indicators */}
                {analysis.threat_intelligence.indicators?.length > 0 && (
                  <div>
                    <h4 className="font-600 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>
                      Detailed Threat Indicators
                    </h4>
                    <div className="space-y-2">
                      {analysis.threat_intelligence.indicators.map((ind, i) => (
                        <div key={i} className="p-4 rounded-xl" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                              <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                              <span className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>
                                {ind.api_name?.toUpperCase() ?? 'Unknown API'}
                              </span>
                            </div>
                            {ind.details?.malicious && (
                              <span className="badge badge-danger">Malicious</span>
                            )}
                          </div>
                          <div className="text-xs space-y-1" style={{ color: 'var(--text-muted)' }}>
                            <div><span className="font-500">Indicator:</span> {ind.indicator_type}: {ind.indicator_value}</div>
                            {ind.details && Object.entries(ind.details).map(([k, v]) => (
                              <div key={k}><span className="font-500">{k}:</span> {typeof v === 'object' ? JSON.stringify(v) : String(v)}</div>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Warnings */}
                {analysis.threat_intelligence.warnings?.length > 0 && (
                  <div>
                    <h4 className="font-600 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>
                      Warnings
                    </h4>
                    <div className="space-y-2">
                      {analysis.threat_intelligence.warnings.map((warn, i) => (
                        <div key={i} className="flex items-start gap-3 p-3 rounded-xl" style={{ background: 'var(--threat-dim)', border: '1px solid var(--threat)' }}>
                          <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--threat)' }} />
                          <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{warn}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* ML Analysis */}
            {analysis.ml_analysis && (
              <div>
                <h4 className="font-600 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>
                  Machine Learning Analysis
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="p-4 rounded-xl" style={{ background: 'var(--danger-dim)', border: '1px solid var(--danger)' }}>
                    <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Phishing Probability</div>
                    <div className="flex items-end gap-2">
                      <span className="font-heading font-700 text-3xl" style={{ color: 'var(--danger)' }}>
                        {Math.round((analysis.ml_analysis.phishing_probability ?? 0) * 100)}%
                      </span>
                    </div>
                    <div className="mt-2 h-2 rounded-full" style={{ background: 'var(--border)' }}>
                      <div className="h-full rounded-full" style={{ width: `${(analysis.ml_analysis.phishing_probability ?? 0) * 100}%`, background: 'var(--danger)' }} />
                    </div>
                  </div>
                  <div className="p-4 rounded-xl" style={{ background: 'var(--success-dim)', border: '1px solid var(--success)' }}>
                    <div className="text-xs mb-1" style={{ color: 'var(--text-muted)' }}>Safe Probability</div>
                    <div className="flex items-end gap-2">
                      <span className="font-heading font-700 text-3xl" style={{ color: 'var(--success)' }}>
                        {Math.round((analysis.ml_analysis.safe_probability ?? 0) * 100)}%
                      </span>
                    </div>
                    <div className="mt-2 h-2 rounded-full" style={{ background: 'var(--border)' }}>
                      <div className="h-full rounded-full" style={{ width: `${(analysis.ml_analysis.safe_probability ?? 0) * 100}%`, background: 'var(--success)' }} />
                    </div>
                  </div>
                </div>
                {analysis.ml_analysis.category && (
                  <div className="mt-3 p-3 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>ML Classification: </span>
                    <span className="font-600 text-sm" style={{ color: 'var(--brand)' }}>{analysis.ml_analysis.category}</span>
                  </div>
                )}
              </div>
            )}
          </div>
        </Section>
      )}

      {/* ── Threat indicators ── */}
      {indicators.length > 0 && (
        <Section title={`Threat Indicators (${indicators.length})`} icon={AlertTriangle} accentColor="var(--danger)">
          <div className="space-y-2">
            {indicators.map((ind, i) => {
              const label = typeof ind === 'string' ? ind
                : ind.label ?? ind.name ?? ind.description ?? JSON.stringify(ind);
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                  style={{ background: 'var(--danger-dim)', border: '1px solid var(--danger)' }}>
                  <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--danger)' }} />
                  <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{label}</span>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* ── Suspicious URLs ── */}
      {links.length > 0 && (
        <Section title={`Links (${links.length})`} icon={Globe} accentColor="var(--threat)">
          <div className="space-y-2">
            {links.map((link, i) => {
              const url = typeof link === 'string' ? link : link.url ?? link.href ?? JSON.stringify(link);
              const displayText = typeof link === 'string' ? null : link.display_text ?? link.displayText ?? null;
              const rawStatus = typeof link === 'string' ? null : link.status ?? link.risk_category ?? null;
              const status = rawStatus || (s >= 70 ? 'suspicious' : s >= 40 ? 'suspicious' : 'safe');
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    status === 'malicious' || status === 'suspicious' ? 'bg-pink-500/15' : 'bg-teal-500/15'
                  }`}>
                    {(status === 'malicious' || status === 'suspicious') ? (
                      <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                    ) : (
                      <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    {displayText && (
                      <div className="text-sm font-medium mb-1" style={{ color: 'var(--text-primary)' }}>
                        <SensitiveText blurSensitive={blurSensitive}>{displayText}</SensitiveText>
                      </div>
                    )}
                    <span className="text-xs font-mono break-all" style={{ color: 'var(--text-secondary)' }}>{url}</span>
                    <div className="flex items-center gap-2 mt-1">
                      <span className={`text-[10px] px-2 py-0.5 rounded ${
                        status === 'malicious' ? 'bg-pink-500/15 text-pink-400' 
                        : status === 'suspicious' ? 'bg-amber-500/15 text-amber-400'
                        : 'bg-teal-500/15 text-teal-400'
                      }`}>
                        {status}
                      </span>
                      {link.category && (
                        <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{link.category}</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* ── Attachments ── */}
      {attachments.length > 0 && (
        <Section title={`Attachments (${attachments.length})`} icon={Paperclip} accentColor="var(--brand)">
          <div className="space-y-2">
            {attachments.map((attachment, i) => {
              const name = attachment.filename ?? attachment.name ?? 'Unknown';
              const size = attachment.size ?? 0;
              const status = attachment.status ?? 'unknown';
              const contentType = attachment.content_type ?? attachment.contentType ?? '';
              return (
                <div key={i} className="flex items-center gap-3 p-3 rounded-xl"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                    status === 'malicious' || status === 'suspicious' ? 'bg-pink-500/15' : 'bg-teal-500/15'
                  }`}>
                    {(status === 'malicious' || status === 'suspicious') ? (
                      <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                    ) : (
                      <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                      <SensitiveText blurSensitive={blurSensitive}>{name}</SensitiveText>
                    </p>
                    <div className="flex items-center gap-2 mt-0.5">
                      <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
                        {contentType ? `${contentType} • ` : ''}{size > 1024 ? `${(size/1024).toFixed(1)} KB` : `${size} B`}
                      </span>
                    </div>
                  </div>
                  <span className={`text-[10px] px-2 py-0.5 rounded ${
                    status === 'malicious' ? 'bg-pink-500/15 text-pink-400' 
                    : status === 'suspicious' ? 'bg-amber-500/15 text-amber-400'
                    : 'bg-teal-500/15 text-teal-400'
                  }`}>
                    {status}
                  </span>
                </div>
              );
            })}
          </div>
        </Section>
      )}

      {/* ── Recommendations ── */}
      {recs.length > 0 && (
        <Section title="Recommendations" icon={CheckCircle} accentColor="var(--success)" open={s >= 40}>
          <div className="space-y-3">
            {recs.map((rec, i) => (
              <div key={i} className="flex items-start gap-3 text-sm" style={{ color: 'var(--text-secondary)' }}>
                <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-700 shrink-0 mt-0.5"
                  style={{ background: 'var(--success-dim)', color: 'var(--success)' }}>
                  {i + 1}
                </span>
                {typeof rec === 'string' ? rec : rec.text ?? JSON.stringify(rec)}
              </div>
            ))}
          </div>
        </Section>
      )}

      {/* ── Category Explanation ── */}
      <Section title="Category Explanation" icon={Shield} accentColor={riskColor(s)}>
        <div className="p-4 rounded-xl" style={{ 
          background: s >= 70 ? 'var(--danger-dim)' : s >= 40 ? 'var(--threat-dim)' : 'var(--success-dim)',
          border: `1px solid ${riskColor(s)}`
        }}>
          <div className="flex items-center gap-3 mb-3">
            {s >= 70 ? (
              <AlertTriangle className="w-6 h-6" style={{ color: 'var(--danger)' }} />
            ) : s >= 40 ? (
              <Shield className="w-6 h-6" style={{ color: 'var(--threat)' }} />
            ) : (
              <CheckCircle className="w-6 h-6" style={{ color: 'var(--success)' }} />
            )}
            <div>
              <h3 className="font-700" style={{ color: riskColor(s) }}>
                {category === 'phishing' ? 'Phishing Email Detected' 
                  : category === 'malware' ? 'Malware Detected'
                  : category === 'suspicious' ? 'Suspicious Email'
                  : 'Safe Email'}
              </h3>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Risk Score: {s}/100 ({riskLabel(s)})
              </p>
            </div>
          </div>
          
          <div className="text-sm space-y-2" style={{ color: 'var(--text-secondary)' }}>
            {s >= 70 && (
              <>
                <p><strong>Why this is classified as high-risk:</strong></p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  {analysis.risk_factors?.sender_reputation >= 70 && <li>Sender domain has poor reputation or is flagged as malicious</li>}
                  {analysis.risk_factors?.link_risk >= 70 && <li>Contains links to known phishing or malicious websites</li>}
                  {analysis.risk_factors?.content_risk >= 70 && <li>Email contains suspicious content patterns (urgency, threats, data requests)</li>}
                  {analysis.risk_factors?.attachment_risk >= 70 && <li>Contains dangerous file attachments</li>}
                  {analysis.risk_factors?.authentication_risk >= 70 && <li>Email failed authentication checks (SPF/DKIM/DMARC)</li>}
                  {analysis.findings?.some(f => f.severity === 'critical') && <li>Critical security findings detected</li>}
                  {analysis.ml_analysis?.phishing_probability > 0.5 && <li>ML model indicates high phishing probability</li>}
                </ul>
                <p className="mt-2"><strong>Recommended actions:</strong></p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Do not click any links in this email</li>
                  <li>Do not download or open any attachments</li>
                  <li>Report this email as phishing to your email provider</li>
                  <li>Delete this email immediately</li>
                </ul>
              </>
            )}
            {s >= 40 && s < 70 && (
              <>
                <p><strong>Why this is classified as suspicious:</strong></p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  {analysis.risk_factors?.sender_reputation >= 40 && analysis.risk_factors?.sender_reputation < 70 && <li>Sender domain has moderate reputation concerns</li>}
                  {analysis.risk_factors?.link_risk >= 40 && analysis.risk_factors?.link_risk < 70 && <li>Contains URLs that require caution</li>}
                  {analysis.risk_factors?.content_risk >= 40 && analysis.risk_factors?.content_risk < 70 && <li>Email content has some suspicious elements</li>}
                  {analysis.findings?.some(f => f.severity === 'medium') && <li>Medium severity findings detected</li>}
                  {analysis.ml_analysis?.phishing_probability > 0.2 && analysis.ml_analysis?.phishing_probability <= 0.5 && <li>ML model indicates moderate phishing probability</li>}
                </ul>
                <p className="mt-2"><strong>Recommended actions:</strong></p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  <li>Verify the sender through official channels</li>
                  <li>Hover over links without clicking to check destination</li>
                  <li>Do not provide any personal information</li>
                  <li>When in doubt, contact your IT security team</li>
                </ul>
              </>
            )}
            {s < 40 && (
              <>
                <p><strong>Why this appears safe:</strong></p>
                <ul className="list-disc list-inside space-y-1 ml-2">
                  {(!analysis.risk_factors || analysis.risk_factors.sender_reputation < 40) && <li>Sender domain has good reputation</li>}
                  {(!analysis.risk_factors || analysis.risk_factors.link_risk < 40) && <li>No suspicious links detected</li>}
                  {(!analysis.risk_factors || analysis.risk_factors.content_risk < 40) && <li>Email content appears legitimate</li>}
                  {(!analysis.findings || analysis.findings.length === 0) && <li>No security findings detected</li>}
                  {analysis.ml_analysis?.safe_probability > 0.7 && <li>ML model indicates high probability of being safe</li>}
                </ul>
                <p className="mt-2"><strong>Note:</strong> Even safe emails should be scrutinized if they request sensitive information.</p>
              </>
            )}
          </div>
        </div>
      </Section>

      {/* ── Raw headers (collapsed by default) ── */}
      {Object.keys(headers).length > 0 && (
        <Section title="Email Headers" icon={User} open={false}>
          <div className="font-mono text-xs leading-relaxed space-y-1 overflow-x-auto max-h-72 overflow-y-auto"
            style={{ color: 'var(--text-secondary)' }}>
            {Object.entries(headers).map(([k, v]) => (
              <div key={k} className="flex gap-2">
                <span className="font-600 shrink-0" style={{ color: 'var(--text-muted)' }}>{k}:</span>
                <span className="break-all">{v}</span>
              </div>
            ))}
          </div>
        </Section>
      )}
    </div>
  );
}