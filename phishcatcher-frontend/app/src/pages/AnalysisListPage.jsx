/**
 * AnalysisListPage.jsx
 * Searchable, filterable table of all email analyses with delete and load-more.
 * Also handles queued analyses from Gmail integration.
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Search, Upload, FileText, Clock, RefreshCw, Loader2,
  X, AlertTriangle, CheckCircle, Shield, Play, Layers,
  CheckSquare, Square, Settings, FileJson, File, FileCode, Zap, Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi, authApi } from '@/lib/api';

/* ─── Analysis Format Dialog ─────────────────────────────────────────────── */
function FormatDialog({ open, onClose, onSubmit, selectedCount }) {
  const [format, setFormat] = useState('detailed');
  const [analyzing, setAnalyzing] = useState(false);

  const formats = [
    { value: 'detailed', label: 'Detailed', icon: FileCode, desc: 'Full analysis with all checks' },
    { value: 'quick', label: 'Quick Scan', icon: Zap, desc: 'Fast analysis, basic checks' },
    { value: 'deep', label: 'Deep Analysis', icon: Shield, desc: 'Comprehensive analysis' },
  ];

  const handleSubmit = async () => {
    setAnalyzing(true);
    try {
      await onSubmit(format);
      onClose();
    } catch (err) { toast.error(err.message ?? 'Analysis failed'); }
    finally { setAnalyzing(false); }
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white dark:bg-gray-900 rounded-xl p-6 w-full max-w-md mx-4 shadow-2xl">
        <h3 className="text-lg font-600 mb-1" style={{ color: 'var(--text-primary)' }}>Analysis Options</h3>
        <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
          {selectedCount} item{selectedCount > 1 ? 's' : ''} selected
        </p>

        <div className="space-y-2 mb-6">
          {formats.map(f => (
            <button
              key={f.value}
              onClick={() => setFormat(f.value)}
              className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all ${
                format === f.value ? 'border-brand bg-brand/10' : 'border-transparent'
              }`}
              style={{ background: format === f.value ? 'var(--brand-dim)' : 'var(--bg-surface)' }}
            >
              {format === f.value ? <CheckSquare className="w-5 h-5" style={{ color: 'var(--brand)' }} /> : <Square className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />}
              <div className="text-left">
                <p className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>{f.label}</p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{f.desc}</p>
              </div>
            </button>
          ))}
        </div>

        <div className="flex gap-3">
          <button onClick={onClose} className="btn-ghost flex-1">Cancel</button>
          <button onClick={handleSubmit} disabled={analyzing} className="btn-primary flex-1">
            {analyzing ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Play className="w-4 h-4 mr-2" />}
            Analyze
          </button>
        </div>
      </div>
    </div>
  );
}

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

  /* ── Queue state ── */
  const [queueData, setQueueData] = useState({ pending: [], processing: [], completed: [], counts: {} });
  const [selectedIds, setSelectedIds] = useState([]);
  const [showFormatDialog, setShowFormatDialog] = useState(false);
  const [showClearDialog, setShowClearDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [deleteItem, setDeleteItem] = useState(null);
  const [clearing, setClearing] = useState(false);
  const [queueDeleting, setQueueDeleting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [activeTab, setActiveTab] = useState('results');
  const [queueLoading, setQueueLoading] = useState(false);

  useEffect(() => {
    const pendingId = localStorage.getItem('pending_analysis_id');
    if (pendingId) {
      localStorage.removeItem('pending_analysis_id');
      navigate(`/analysis/${pendingId}`);
    }
    loadQueue();
  }, []);

  const loadQueue = async () => {
    setQueueLoading(true);
    try {
      const data = await authApi.gmail.getQueue();
      setQueueData(data);
    } catch { /* silent */ }
    finally { setQueueLoading(false); }
  };

  const handleSelectAll = () => {
    const allPending = queueData.pending.map(q => q.message_id);
    if (selectedIds.length === allPending.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(allPending);
    }
  };

  const handleToggleSelect = (id) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleAnalyzeAll = () => {
    if (selectedIds.length === 0) {
      setSelectedIds(queueData.pending.map(q => q.message_id));
    }
    setShowFormatDialog(true);
  };

  const handleAnalyzeSingle = async (item) => {
    try {
      const result = await authApi.gmail.processQueueItem(item.message_id);
      const analysisId = result.analysis_id;
      if (analysisId && analysisId !== 'None' && analysisId !== 'null') {
        navigate(`/analysis/${analysisId}`);
      } else {
        toast.success('Analysis completed');
        loadQueue();
      }
    } catch (err) {
      toast.error(err.message ?? 'Failed to start analysis');
    }
  };

  const handleAnalyze = async (format) => {
    setAnalyzing(true);
    try {
      for (const id of selectedIds) {
        await authApi.gmail.processQueueItem(id);
      }
      toast.success(`${selectedIds.length} analyses started`);
      setSelectedIds([]);
      loadQueue();
      setActiveTab('results');
      load(1, true);
    } catch (err) {
      throw err;
    } finally {
      setAnalyzing(false);
    }
  };

  const handleClearCompleted = async () => {
    setShowClearDialog(false);
    setClearing(true);
    try {
      await authApi.gmail.clearQueue();
      toast.success('Queue cleared');
      loadQueue();
    } catch (err) {
      toast.error(err.message ?? 'Failed to clear queue');
    } finally {
      setClearing(false);
    }
  };

  const handleDeleteItem = async () => {
    if (!deleteItem) return;
    setShowDeleteDialog(false);
    setQueueDeleting(true);
    try {
      await authApi.gmail.deleteQueueItem(deleteItem.message_id);
      toast.success('Item removed from queue');
      setSelectedIds(prev => prev.filter(id => id !== deleteItem.message_id));
      loadQueue();
    } catch (err) {
      toast.error(err.message ?? 'Failed to remove item');
    } finally {
      setQueueDeleting(false);
      setDeleteItem(null);
    }
  };

  const handleViewResult = (item) => {
    const analysisId = item.analysis_id;
    if (analysisId && analysisId !== 'None' && analysisId !== 'null' && analysisId !== undefined) {
      navigate(`/analysis/${analysisId}`);
    } else {
      toast.error('Analysis result not available yet');
    }
  };

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
          <h1 className="page-title">Analysis</h1>
          <p className="page-subtitle">{items.length} total analyses</p>
        </div>
        <Link to="/upload" className="btn-primary h-9 px-4 text-sm self-start sm:self-auto">
          <Upload className="w-4 h-4" /> New analysis
        </Link>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('results')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-500 transition-all ${
            activeTab === 'results' ? 'btn-primary' : 'btn-ghost'
          }`}
        >
          <FileText className="w-4 h-4" /> Results
        </button>
        <button
          onClick={() => { setActiveTab('queue'); loadQueue(); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-500 transition-all ${
            activeTab === 'queue' ? 'btn-primary' : 'btn-ghost'
          }`}
        >
          <Layers className="w-4 h-4" /> Queue
          {(queueData.counts.pending > 0 || queueData.counts.processing > 0) && (
            <span className="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-brand text-white">
              {queueData.counts.pending + queueData.counts.processing}
            </span>
          )}
        </button>
      </div>

      {/* Queue Tab */}
      {activeTab === 'queue' && (
        <div className="rounded-2xl p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          {queueLoading ? (
            <div className="text-center py-10">
              <Loader2 className="w-8 h-8 mx-auto animate-spin" style={{ color: 'var(--brand)' }} />
              <p className="text-sm mt-3" style={{ color: 'var(--text-muted)' }}>Loading queue...</p>
            </div>
          ) : queueData.counts.pending === 0 && queueData.counts.processing === 0 && queueData.counts.completed === 0 ? (
            <div className="text-center py-10">
              <Layers className="w-12 h-12 mx-auto mb-3 opacity-30" style={{ color: 'var(--text-muted)' }} />
              <p className="text-sm mb-1" style={{ color: 'var(--text-primary)' }}>Queue is empty</p>
              <p className="text-xs mb-4" style={{ color: 'var(--text-muted)' }}>Select emails from Gmail or upload .eml files</p>
              <Link to="/upload" className="btn-primary text-sm">Go to Upload</Link>
            </div>
          ) : (
            <>
              {/* Queue Stats */}
              <div className="grid grid-cols-3 gap-3 mb-4">
                <div className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <div className="font-heading font-700 text-lg" style={{ color: 'var(--warning)' }}>{queueData.counts.pending}</div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Pending</div>
                </div>
                <div className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <div className="font-heading font-700 text-lg" style={{ color: 'var(--brand)' }}>{queueData.counts.processing}</div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Processing</div>
                </div>
                <div className="rounded-xl p-3 text-center" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <div className="font-heading font-700 text-lg" style={{ color: 'var(--success)' }}>{queueData.counts.completed}</div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>Completed</div>
                </div>
              </div>

              {/* Pending Items */}
              {queueData.pending.length > 0 && (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>Pending Analysis</h3>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={handleSelectAll}
                        className="flex items-center gap-1 text-xs"
                        style={{ color: 'var(--text-muted)' }}
                      >
                        {selectedIds.length === queueData.pending.length ? <CheckSquare className="w-3.5 h-3.5" /> : <Square className="w-3.5 h-3.5" />}
                        Select All
                      </button>
                      <button
                        onClick={handleAnalyzeAll}
                        disabled={selectedIds.length === 0}
                        className="btn-primary h-8 px-3 text-xs"
                      >
                        <Play className="w-3 h-3 mr-1" /> Analyze ({selectedIds.length})
                      </button>
                    </div>
                  </div>
                  <div className="space-y-2 mb-4">
                    {queueData.pending.map(item => (
                      <div
                        key={item.message_id}
                        className="flex items-center gap-3 p-3 rounded-lg"
                        style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                      >
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(item.message_id)}
                          onChange={() => handleToggleSelect(item.message_id)}
                          className="rounded"
                        />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>{item.subject || 'No Subject'}</p>
                          <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>{item.from || 'Unknown sender'}</p>
                        </div>
                        <button
                          onClick={() => handleAnalyzeSingle(item)}
                          className="btn-ghost h-8 px-3 text-xs"
                        >
                          Analyze
                        </button>
                        <button
                          onClick={() => { setDeleteItem(item); setShowDeleteDialog(true); }}
                          className="p-2 rounded-lg hover:bg-[var(--bg-surface)]"
                          title="Remove from queue"
                        >
                          <Trash2 className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                        </button>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Processing Items */}
              {queueData.processing.length > 0 && (
                <>
                  <h3 className="font-600 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>Processing</h3>
                  <div className="space-y-2 mb-4">
                    {queueData.processing.map(item => (
                      <div
                        key={item.message_id}
                        className="flex items-center gap-3 p-3 rounded-lg"
                        style={{ background: 'var(--brand-dim)', border: '1px solid var(--brand)' }}
                      >
                        <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--brand)' }} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>{item.subject || 'No Subject'}</p>
                          <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>Analyzing...</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </>
              )}

              {/* Completed Items */}
              {queueData.completed.length > 0 && (
                <>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>Completed</h3>
                    <button
                      onClick={() => setShowClearDialog(true)}
                      className="text-xs flex items-center gap-1"
                      style={{ color: 'var(--text-muted)' }}
                    >
                      <Trash2 className="w-3 h-3" />
                      Clear completed
                    </button>
                  </div>
                  <div className="space-y-2">
                    {queueData.completed.map(item => (
                      <div
                        key={item.message_id}
                        className="flex items-center gap-3 p-3 rounded-lg cursor-pointer hover:opacity-80"
                        style={{ background: item.status === 'failed' ? 'var(--danger-dim)' : 'var(--success-dim)', border: `1px solid ${item.status === 'failed' ? 'var(--danger)' : 'var(--success)'}` }}
                        onClick={() => handleViewResult(item)}
                      >
                        {item.status === 'failed' ? (
                          <AlertTriangle className="w-4 h-4" style={{ color: 'var(--danger)' }} />
                        ) : (
                          <CheckCircle className="w-4 h-4" style={{ color: 'var(--success)' }} />
                        )}
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate" style={{ color: 'var(--text-primary)' }}>{item.subject || 'No Subject'}</p>
                          <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>
                            {item.status === 'failed' ? (item.error || 'Analysis failed') : 'Analysis complete'}
                          </p>
                        </div>
                        {item.analysis_id && (
                          <span className="text-xs font-500" style={{ color: 'var(--brand)' }}>View Result</span>
                        )}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </>
          )}
        </div>
      )}

      {/* Results Tab */}
      {activeTab === 'results' && (
      <>

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
      </>
      )}

      <FormatDialog
        open={showFormatDialog}
        onClose={() => setShowFormatDialog(false)}
        onSubmit={handleAnalyze}
        selectedCount={selectedIds.length}
      />

      {showClearDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowClearDialog(false)} />
          <div className="relative bg-white dark:bg-gray-900 rounded-xl p-6 w-full max-w-sm mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'var(--danger-dim, #fee2e2)' }}>
                <Trash2 className="w-5 h-5" style={{ color: 'var(--danger)' }} />
              </div>
              <div>
                <h3 className="text-lg font-600" style={{ color: 'var(--text-primary)' }}>Clear Completed?</h3>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>This action cannot be undone</p>
              </div>
            </div>
            
            <div className="mb-6 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                This will remove all completed analysis results from the queue. The analysis results will remain in your history.
              </p>
            </div>

            <div className="flex gap-3">
              <button 
                onClick={() => setShowClearDialog(false)} 
                className="btn-ghost flex-1"
              >
                Cancel
              </button>
              <button 
                onClick={handleClearCompleted} 
                disabled={clearing}
                className="flex-1 h-10 px-4 rounded-lg font-500 text-sm flex items-center justify-center gap-2"
                style={{ background: 'var(--danger)', color: 'white' }}
              >
                {clearing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Clear
              </button>
            </div>
          </div>
        </div>
      )}

      {showDeleteDialog && deleteItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowDeleteDialog(false)} />
          <div className="relative bg-white dark:bg-gray-900 rounded-xl p-6 w-full max-w-sm mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'var(--danger-dim, #fee2e2)' }}>
                <Trash2 className="w-5 h-5" style={{ color: 'var(--danger)' }} />
              </div>
              <div>
                <h3 className="text-lg font-600" style={{ color: 'var(--text-primary)' }}>Remove from Queue?</h3>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>This action cannot be undone</p>
              </div>
            </div>
            
            <div className="mb-6 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                Remove <strong>{deleteItem.subject || 'No Subject'}</strong> from the queue? You can add it again later.
              </p>
            </div>

            <div className="flex gap-3">
              <button 
                onClick={() => setShowDeleteDialog(false)} 
                className="btn-ghost flex-1"
              >
                Cancel
              </button>
              <button 
                onClick={handleDeleteItem} 
                disabled={queueDeleting}
                className="flex-1 h-10 px-4 rounded-lg font-500 text-sm flex items-center justify-center gap-2"
                style={{ background: 'var(--danger)', color: 'white' }}
              >
                {queueDeleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}