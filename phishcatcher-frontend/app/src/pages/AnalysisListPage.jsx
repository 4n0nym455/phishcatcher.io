/**
 * AnalysisListPage.jsx
 * Searchable, filterable table of all email analyses with delete and load-more.
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Search, Upload, FileText, Clock, RefreshCw, Loader2,
  X, AlertTriangle, CheckCircle, Shield,
} from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi } from '@/lib/api';

/* ─── Helpers ──────────────────────────────────────────────────────────── */
function score(a)     { return a.threat_score ?? a.risk_score ?? 0; }
function riskLabel(s) { return s >= 70 ? 'High' : s >= 40 ? 'Medium' : 'Safe'; }
function riskBadge(s) { return s >= 70 ? 'badge badge-danger' : s >= 40 ? 'badge badge-threat' : 'badge badge-success'; }
function riskColor(s) { return s >= 70 ? 'var(--danger)' : s >= 40 ? 'var(--threat)' : 'var(--success)'; }
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

const FILTER_OPTS = [
  { label: 'All',         value: 'all'    },
  { label: 'High risk',   value: 'high'   },
  { label: 'Medium risk', value: 'medium' },
  { label: 'Safe',        value: 'safe'   },
];

const PAGE_SIZE = 20;

export default function AnalysisListPage() {
  const navigate = useNavigate();

  const [items,    setItems]    = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [search,   setSearch]   = useState('');
  const [filter,   setFilter]   = useState('all');
  const [page,     setPage]     = useState(1);
  const [hasMore,  setHasMore]  = useState(false);
  const [deleting, setDeleting] = useState(null);

  const load = useCallback(async (pg = 1, reset = true) => {
    setLoading(true);
    try {
      const res  = await analysisApi.getHistory({ page: pg, pageSize: PAGE_SIZE });
      const list = res.items ?? res.analyses ?? (Array.isArray(res) ? res : []);
      setItems(prev => reset ? list : [...prev, ...list]);
      setHasMore(list.length === PAGE_SIZE);
      setPage(pg);
    } catch { /* silent */ }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(1, true); }, [load]);

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    if (!window.confirm('Delete this analysis? This cannot be undone.')) return;
    setDeleting(id);
    try {
      await analysisApi.deleteAnalysis(id);
      setItems(prev => prev.filter(a => a.id !== id));
      toast.success('Analysis deleted');
    } catch (err) {
      toast.error(err.message ?? 'Delete failed');
    } finally {
      setDeleting(null);
    }
  };

  // Client-side filter + search
  const filtered = items.filter(a => {
    const s = score(a);
    const matchFilter =
      filter === 'all'    ? true :
      filter === 'high'   ? s >= 70 :
      filter === 'medium' ? s >= 40 && s < 70 :
      filter === 'safe'   ? s < 40 : true;
    const term = search.toLowerCase();
    const matchSearch = !search ||
      (a.subject ?? a.filename ?? a.email_subject ?? '').toLowerCase().includes(term) ||
      (a.threat_category ?? a.category ?? '').toLowerCase().includes(term);
    return matchFilter && matchSearch;
  });

  // Mini stats
  const countHigh   = items.filter(a => score(a) >= 70).length;
  const countMedium = items.filter(a => score(a) >= 40 && score(a) < 70).length;
  const countSafe   = items.filter(a => score(a) < 40).length;

  return (
    <div className="animate-fade-in">

      {/* Header */}
      <div className="page-header flex flex-col sm:flex-row sm:items-end justify-between gap-4">
        <div>
          <h1 className="page-title">Analysis History</h1>
          <p className="page-subtitle">{items.length} total analyses</p>
        </div>
        <Link to="/upload" className="btn-primary h-9 px-4 text-sm self-start sm:self-auto">
          <Upload className="w-4 h-4" /> New analysis
        </Link>
      </div>

      {/* Mini stats */}
      {items.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            { label: 'High risk',   count: countHigh,   icon: Shield,        color: 'var(--danger)',  bg: 'var(--danger-dim)',  filt: 'high'   },
            { label: 'Medium risk', count: countMedium, icon: AlertTriangle, color: 'var(--threat)',  bg: 'var(--threat-dim)',  filt: 'medium' },
            { label: 'Safe',        count: countSafe,   icon: CheckCircle,   color: 'var(--success)', bg: 'var(--success-dim)', filt: 'safe'   },
          ].map(s => (
            <button
              key={s.filt}
              onClick={() => setFilter(prev => prev === s.filt ? 'all' : s.filt)}
              className="stat-card text-left transition-all hover:scale-[1.01] active:scale-[0.99]"
              style={{ outline: filter === s.filt ? `2px solid ${s.color}` : 'none' }}
            >
              <div className="flex items-center gap-2 mb-1">
                <s.icon className="w-3.5 h-3.5" style={{ color: s.color }} />
                <span className="text-xs font-500" style={{ color: 'var(--text-muted)' }}>{s.label}</span>
              </div>
              <div className="font-heading font-700 text-xl" style={{ color: s.color }}>{s.count}</div>
            </button>
          ))}
        </div>
      )}

      {/* Search + filter */}
      <div className="flex flex-col sm:flex-row gap-3 mb-5">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
          <input
            type="text"
            placeholder="Search by subject, filename, or category…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="input-base pl-10 pr-9"
          />
          {search && (
            <button onClick={() => setSearch('')} className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        <div className="flex gap-2 flex-wrap">
          {FILTER_OPTS.map(o => (
            <button
              key={o.value}
              onClick={() => setFilter(o.value)}
              className="px-3 py-1.5 rounded-lg text-xs font-600 transition-all border"
              style={{
                background:  filter === o.value ? 'var(--brand)' : 'var(--bg-surface)',
                color:       filter === o.value ? '#fff' : 'var(--text-secondary)',
                borderColor: filter === o.value ? 'var(--brand)' : 'var(--border)',
              }}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-2xl overflow-hidden"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        {loading && items.length === 0 ? (
          <div className="p-12 text-center">
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Loading analysis history…</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-12 text-center">
            <FileText className="w-10 h-10 mx-auto mb-4 opacity-25" style={{ color: 'var(--text-muted)' }} />
            <p className="font-heading font-700 text-base mb-1" style={{ color: 'var(--text-primary)' }}>
              {search || filter !== 'all' ? 'No results found' : 'No analyses yet'}
            </p>
            <p className="text-sm mb-5" style={{ color: 'var(--text-muted)' }}>
              {search || filter !== 'all' ? 'Try adjusting your search or filter' : 'Upload your first email to get started'}
            </p>
            {!search && filter === 'all' && (
              <Link to="/upload" className="btn-primary inline-flex">
                <Upload className="w-4 h-4" /> Upload email
              </Link>
            )}
          </div>
        ) : (
          <>
            <table className="table-base">
              <thead>
                <tr>
                  <th>Subject / File</th>
                  <th className="hidden sm:table-cell">Category</th>
                  <th>Risk</th>
                  <th className="hidden md:table-cell">Score</th>
                  <th className="hidden lg:table-cell">Analyzed</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map(a => {
                  const s       = score(a);
                  const subject = a.subject ?? a.filename ?? a.email_subject ?? 'Untitled';
                  const cat     = a.threat_category ?? a.category ?? '—';
                  const date    = a.created_at ?? a.analyzed_at;
                  return (
                    <tr key={a.id} className="cursor-pointer" onClick={() => navigate(`/analysis/${a.id}`)}>
                      <td>
                        <p className="font-500 text-sm truncate max-w-[200px]" style={{ color: 'var(--text-primary)' }}>
                          {subject}
                        </p>
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
                      <td>
                        <div className="flex items-center gap-3">
                          <span className="text-xs font-500" style={{ color: 'var(--brand)' }}>View →</span>
                          <button
                            onClick={e => handleDelete(e, a.id)}
                            disabled={deleting === a.id}
                            className="text-xs font-500 hover:underline disabled:opacity-50"
                            style={{ color: 'var(--danger)' }}
                          >
                            {deleting === a.id ? '…' : 'Delete'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
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