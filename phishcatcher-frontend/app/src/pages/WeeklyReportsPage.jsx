/**
 * WeeklyReports.jsx
 * List of weekly threat intelligence reports with expandable detail cards.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  TrendingUp, Calendar, Download, BarChart3,
  AlertTriangle, CheckCircle, Shield, Loader2, ChevronRight,
} from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi } from '@/lib/api';

/* ─── Format helpers ───────────────────────────────────────────────────── */
function formatWeekRange(dateStr) {
  if (!dateStr) return 'Unknown week';
  const start = new Date(dateStr);
  const end   = new Date(start);
  end.setDate(end.getDate() + 6);
  return `${start.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} – ${end.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}`;
}

/* ─── Single report card ───────────────────────────────────────────────── */
function ReportCard({ report, onDownload }) {
  const [expanded, setExpanded] = useState(false);

  const total      = report.total_analyzed ?? report.emails_analyzed ?? 0;
  const threats    = report.threats_detected ?? report.phishing_count ?? 0;
  const suspicious = report.suspicious_count ?? 0;
  const safe       = report.safe_count ?? Math.max(0, total - threats - suspicious);
  const avgScore   = report.avg_risk_score ?? report.average_risk ?? null;
  const topCats    = report.top_categories ?? report.threat_categories ?? [];
  const narrative  = report.summary ?? report.narrative ?? '';

  return (
    <div className="card theme-transition overflow-hidden">
      {/* Card header */}
      <div
        className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-5"
        style={{ borderBottom: expanded ? '1px solid var(--border)' : 'none' }}
      >
        <div className="flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
            <Calendar className="w-5 h-5" />
          </div>
          <div>
            <p className="font-heading font-700 text-sm" style={{ color: 'var(--text-primary)' }}>
              {formatWeekRange(report.week_start ?? report.date)}
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {total} email{total !== 1 ? 's' : ''} analyzed
              {threats > 0 ? ` · ${threats} phishing detected` : ' · No phishing detected'}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          {threats > 0
            ? <span className="badge badge-danger">{threats} threat{threats !== 1 ? 's' : ''}</span>
            : <span className="badge badge-success">All clear</span>
          }
          <button onClick={() => setExpanded(v => !v)} className="btn-ghost h-8 px-3 text-xs">
            {expanded ? 'Collapse' : 'Details'}
            <ChevronRight className={`w-3.5 h-3.5 transition-transform ${expanded ? 'rotate-90' : ''}`} />
          </button>
          <button onClick={() => onDownload(report)} className="btn-ghost h-8 px-3 text-xs">
            <Download className="w-3.5 h-3.5" /> PDF
          </button>
        </div>
      </div>

      {/* Expanded body */}
      {expanded && (
        <div className="p-5 space-y-5 animate-fade-in">
          {/* Stats row */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: 'Analyzed',    value: total,      color: 'var(--brand)',   bg: 'var(--brand-dim)'   },
              { label: 'Phishing',    value: threats,    color: 'var(--danger)',  bg: 'var(--danger-dim)'  },
              { label: 'Suspicious',  value: suspicious, color: 'var(--threat)',  bg: 'var(--threat-dim)'  },
              { label: 'Safe',        value: safe,       color: 'var(--success)', bg: 'var(--success-dim)' },
            ].map(s => (
              <div key={s.label} className="rounded-xl p-3 text-center"
                style={{ background: s.bg }}>
                <div className="font-heading font-700 text-2xl mb-0.5" style={{ color: s.color }}>{s.value}</div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.label}</div>
              </div>
            ))}
          </div>

          {/* Avg risk score bar */}
          {avgScore !== null && (
            <div>
              <p className="text-xs font-600 uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                Average risk score
              </p>
              <div className="flex items-center gap-3">
                <div className="font-heading font-700 text-3xl w-12 shrink-0"
                  style={{ color: avgScore >= 70 ? 'var(--danger)' : avgScore >= 40 ? 'var(--threat)' : 'var(--success)' }}>
                  {Math.round(avgScore)}
                </div>
                <div className="flex-1 h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                  <div className="h-full rounded-full transition-all duration-700"
                    style={{
                      width: `${avgScore}%`,
                      background: avgScore >= 70 ? 'var(--danger)' : avgScore >= 40 ? 'var(--threat)' : 'var(--success)',
                    }} />
                </div>
                <span className="text-xs shrink-0" style={{ color: 'var(--text-muted)' }}>/ 100</span>
              </div>
            </div>
          )}

          {/* Top categories */}
          {topCats.length > 0 && (
            <div>
              <p className="text-xs font-600 uppercase tracking-widest mb-3" style={{ color: 'var(--text-muted)' }}>
                Top threat categories
              </p>
              <div className="space-y-2.5">
                {topCats.slice(0, 5).map((cat, i) => {
                  const name  = typeof cat === 'string' ? cat : cat.name ?? cat.category ?? '—';
                  const count = typeof cat === 'object' ? (cat.count ?? cat.occurrences ?? 1) : 1;
                  const maxCount = typeof topCats[0] === 'object' ? (topCats[0].count ?? topCats[0].occurrences ?? 1) : 1;
                  const pct   = Math.round((count / maxCount) * 100);
                  return (
                    <div key={i} className="flex items-center gap-3">
                      <span className="text-sm w-40 shrink-0 truncate" style={{ color: 'var(--text-secondary)' }}>{name}</span>
                      <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                        <div className="h-full rounded-full" style={{ width: `${pct}%`, background: 'var(--brand)' }} />
                      </div>
                      <span className="text-xs w-5 text-right shrink-0" style={{ color: 'var(--text-muted)' }}>{count}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Narrative */}
          {narrative && (
            <div className="rounded-xl p-4"
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
              <p className="text-xs font-700 uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
                Summary
              </p>
              <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{narrative}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Main ─────────────────────────────────────────────────────────────── */
export default function WeeklyReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  useEffect(() => {
    (async () => {
      setLoading(true);
      try {
        const data = await analysisApi.getWeeklyReport();
        const list = Array.isArray(data)
          ? data
          : data.reports ?? (data.week_start || data.date ? [data] : []);
        setReports(list);
      } catch (err) {
        setError(err.message ?? 'Failed to load reports.');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleDownload = async (report) => {
    if (!report.id) { toast.error('Download not available for this report'); return; }
    try {
      toast.info('Preparing download…');
      const blob = await analysisApi.downloadReport(report.id, 'pdf');
      const url  = URL.createObjectURL(new Blob([blob]));
      const a    = document.createElement('a');
      a.href = url;
      a.download = `phishcatcher-weekly-${report.week_start ?? report.id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Download failed'); }
  };

  return (
    <div className="animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Weekly Reports</h1>
        <p className="page-subtitle">Threat intelligence summaries generated every Monday</p>
      </div>

      {loading ? (
        <div className="text-center py-16">
          <Loader2 className="w-7 h-7 animate-spin mx-auto mb-3" style={{ color: 'var(--brand)' }} />
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading reports…</p>
        </div>
      ) : error ? (
        <div className="alert-error">{error}</div>
      ) : reports.length === 0 ? (
        <div className="card p-12 text-center">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
            <TrendingUp className="w-7 h-7" />
          </div>
          <h3 className="font-heading font-700 text-lg mb-2" style={{ color: 'var(--text-primary)' }}>
            No reports yet
          </h3>
          <p className="text-sm mb-6 max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
            Weekly reports are generated every Monday based on your analysis activity.
            Analyze some emails to generate your first report.
          </p>
          <Link to="/upload" className="btn-primary inline-flex">Analyze your first email</Link>
        </div>
      ) : (
        <div className="space-y-4">
          {reports.map((report, i) => (
            <ReportCard
              key={report.id ?? report.week_start ?? i}
              report={report}
              onDownload={handleDownload}
            />
          ))}
        </div>
      )}
    </div>
  );
}