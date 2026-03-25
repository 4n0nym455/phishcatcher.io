/**
 * AnalysisReport.jsx
 * Full threat report for a single analysis: score, indicators, links, headers, recommendations.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import {
  ArrowLeft, Download, Trash2, AlertTriangle, CheckCircle,
  Shield, Clock, Mail, Globe, User, Loader2, ExternalLink,
  ChevronDown, ChevronUp,
} from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi } from '@/lib/api';

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

  useEffect(() => {
    // Validate ID before making API call
    if (!id || id === 'None' || id === 'null' || id === 'undefined' || id.length < 10) {
      setError('Invalid analysis ID');
      setLoading(false);
      return;
    }
    
    (async () => {
      setLoading(true);
      try {
        const data = await analysisApi.getAnalysis(id);
        setAnalysis(data);
      } catch (err) {
        setError(err.message ?? 'Failed to load analysis report.');
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

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
      const data = await analysisApi.downloadReport(id, 'pdf');
      const url  = URL.createObjectURL(new Blob([data]));
      const a    = document.createElement('a');
      a.href = url;
      a.download = `phishcatcher-report-${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('Download failed');
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
  const subject    = analysis.subject ?? analysis.email_subject ?? analysis.filename ?? 'Untitled';
  const category   = analysis.threat_category ?? analysis.category ?? '—';
  const summary    = analysis.summary ?? analysis.description ?? '';
  const sender     = analysis.sender ?? analysis.from ?? analysis.email_headers?.['From'] ?? '';
  const replyTo    = analysis.reply_to ?? analysis.email_headers?.['Reply-To'] ?? '';
  const indicators = analysis.indicators ?? analysis.threat_indicators ?? [];
  const links      = analysis.malicious_urls ?? analysis.suspicious_links ?? [];
  const headers    = analysis.email_headers ?? {};
  const recs       = analysis.recommendations ?? [];

  return (
    <div className="max-w-3xl mx-auto space-y-5 animate-fade-in">

      {/* Nav row */}
      <div className="flex items-center justify-between gap-4">
        <Link to="/analysis"
          className="flex items-center gap-2 text-sm font-500 transition-opacity hover:opacity-70"
          style={{ color: 'var(--text-muted)' }}>
          <ArrowLeft className="w-4 h-4" /> Analysis History
        </Link>
        <div className="flex items-center gap-2">
          <button onClick={handleDownload} className="btn-ghost h-8 px-3 text-xs">
            <Download className="w-3.5 h-3.5" /> PDF
          </button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="btn-ghost h-8 px-3 text-xs"
            style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}
          >
            {deleting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Trash2 className="w-3.5 h-3.5" />}
            Delete
          </button>
        </div>
      </div>

      {/* ── Threat score hero ── */}
      <div className="rounded-2xl p-6"
        style={{ background: riskBgColor(s), border: `1px solid ${riskColor(s)}` }}>
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5 mb-2">
              <span className={riskBadge(s)}>{riskLabel(s)}</span>
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{category}</span>
            </div>
            <h1 className="font-heading font-700 text-xl leading-tight mb-1" style={{ color: 'var(--text-primary)' }}>
              {subject}
            </h1>
            <p className="text-xs flex items-center gap-1.5" style={{ color: 'var(--text-muted)' }}>
              <Clock className="w-3 h-3" />
              Analyzed {fmtDate(analysis.created_at ?? analysis.analyzed_at)}
            </p>
          </div>
          <div className="text-center shrink-0">
            <div className="font-heading font-800"
              style={{ fontSize: '4rem', lineHeight: 1, color: riskColor(s) }}>
              {s}
            </div>
            <div className="text-xs font-600 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              / 100
            </div>
          </div>
        </div>
        {/* Score bar */}
        <div className="mt-4 h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
          <div className="h-full rounded-full transition-all duration-700"
            style={{ width: `${s}%`, background: riskColor(s) }} />
        </div>
      </div>

      {/* ── Summary ── */}
      {summary && (
        <Section title="AI Summary" icon={Shield} accentColor="var(--brand)">
          <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{summary}</p>
        </Section>
      )}

      {/* ── Email details ── */}
      <Section title="Email Details" icon={Mail} accentColor="var(--brand)">
        <div style={{ borderTop: '1px solid var(--border)' }}>
          <InfoRow label="Subject" value={subject} />
          <InfoRow label="From"    value={sender}   warn={s >= 70} />
          {replyTo && <InfoRow label="Reply-To" value={replyTo} warn={replyTo !== sender && !!replyTo} />}
          {analysis.received_from && <InfoRow label="Received" value={analysis.received_from} />}
          {analysis.message_id    && <InfoRow label="Msg-ID"   value={analysis.message_id} />}
        </div>
      </Section>

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
        <Section title={`Suspicious URLs (${links.length})`} icon={Globe} accentColor="var(--threat)">
          <div className="space-y-2">
            {links.map((link, i) => {
              const url = typeof link === 'string' ? link : link.url ?? link.href ?? JSON.stringify(link);
              return (
                <div key={i} className="flex items-start gap-3 p-3 rounded-xl"
                  style={{ background: 'var(--threat-dim)', border: '1px solid var(--threat)' }}>
                  <ExternalLink className="w-4 h-4 shrink-0 mt-0.5" style={{ color: 'var(--threat)' }} />
                  <span className="text-xs font-mono break-all" style={{ color: 'var(--text-secondary)' }}>{url}</span>
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