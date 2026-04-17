/**
 * AnalysisListPage.jsx
 * Searchable, filterable table of all email analyses with delete and load-more.
 * Also handles queued analyses from Gmail integration.
 * Supports searching by analysis ID and batch report generation.
 */

import { useState, useEffect, useCallback } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Search, Upload, FileText, Clock, RefreshCw, Loader2,
  X, AlertTriangle, CheckCircle, Shield, Play, Layers,
  CheckSquare, Square, Settings, FileJson, File, FileCode, Zap, Trash2,
  ChevronDown, FileBarChart,
} from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi, authApi } from '@/lib/api';

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
  const [idSearch, setIdSearch] = useState('');
  const [filter,   setFilter]   = useState('all');
  const [page,     setPage]     = useState(1);
  const [hasMore,  setHasMore]  = useState(false);
  const [deleting, setDeleting] = useState(null);

  /* ── Batch report state ── */
  const [selectedItems, setSelectedItems] = useState([]);
  const [showBatchReport, setShowBatchReport] = useState(false);
  const [batchReportData, setBatchReportData] = useState(null);
  const [loadingBatchReport, setLoadingBatchReport] = useState(false);

  /* ── Queue state ── */
  const [queueData, setQueueData] = useState({ pending: [], processing: [], completed: [], counts: {} });
  const [selectedIds, setSelectedIds] = useState([]);
  const [expandedQueue, setExpandedQueue] = useState({});
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
      // Validate that it's a proper UUID or 32-char hex ID
      const isValidId = (id) => {
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        const hexRegex = /^[0-9a-f]{32}$/i;
        return uuidRegex.test(id) || hexRegex.test(id);
      };
      
      if (isValidId(pendingId)) {
        localStorage.removeItem('pending_analysis_id');
        navigate(`/analysis/${pendingId}`);
      } else {
        console.warn('Invalid pending_analysis_id found, clearing:', pendingId);
        localStorage.removeItem('pending_analysis_id');
      }
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

  const handleAnalyzeAll = async () => {
    if (selectedIds.length === 0) {
      setSelectedIds(queueData.pending.map(q => q.message_id));
    }
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
      toast.error(err.message ?? 'Failed to start analysis');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleAnalyzeSingle = async (item) => {
    setAnalyzing(true);
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
    } finally {
      setAnalyzing(false);
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

  useEffect(() => { load(1, true); loadQueue(); }, [load]);

  // Handle ID search
  const handleIdSearch = () => {
    const id = idSearch.trim();
    if (!id) return;
    
    const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
    const hexRegex = /^[0-9a-f]{32}$/i;
    
    if (uuidRegex.test(id) || hexRegex.test(id)) {
      navigate(`/analysis/${id}`);
    } else {
      toast.error('Invalid analysis ID format');
    }
  };

  // Handle batch report generation
  const handleGenerateBatchReport = async () => {
    if (selectedItems.length === 0) {
      toast.error('Please select at least one analysis');
      return;
    }
    if (selectedItems.length > 100) {
      toast.error('Maximum 100 analyses can be included in a report');
      return;
    }

    setLoadingBatchReport(true);
    try {
      const ids = selectedItems.map(item => item.id);
      const result = await analysisApi.getBatchReport(ids);
      setBatchReportData(result);
      setShowBatchReport(true);
    } catch (err) {
      toast.error(err.message ?? 'Failed to generate batch report');
    } finally {
      setLoadingBatchReport(false);
    }
  };

  const handleToggleSelectItem = (item) => {
    setSelectedItems(prev => {
      const exists = prev.find(i => i.id === item.id);
      if (exists) {
        return prev.filter(i => i.id !== item.id);
      }
      return [...prev, item];
    });
  };

  const handleSelectAllItems = () => {
    if (selectedItems.length === filtered.length) {
      setSelectedItems([]);
    } else {
      setSelectedItems([...filtered]);
    }
  };

  const handleDelete = async (e, id) => {
    e.stopPropagation();
    
    // Validate inputs
    if (!id || typeof id !== 'string') {
      console.error('Invalid ID provided to delete function:', id);
      toast.error('Invalid analysis ID');
      return;
    }
    
    if (!window.confirm('Delete this analysis? This cannot be undone.')) return;
    
    setDeleting(id);
    try {
      await analysisApi.deleteAnalysis(id);
      setItems(prev => prev.filter(a => a.id !== id));
      toast.success('Analysis deleted');
    } catch (err) {
      console.error('Delete analysis error:', err);
      toast.error(err.message || 'Delete failed');
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
      (a.subject ?? a.file_name ?? a.filename ?? a.email_subject ?? '').toLowerCase().includes(term) ||
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
                        disabled={selectedIds.length === 0 || analyzing}
                        className="btn-primary h-8 px-3 text-xs"
                      >
                        <Play className="w-3 h-3 mr-1" /> {analyzing ? 'Analyzing...' : `Analyze (${selectedIds.length})`}
                      </button>
                    </div>
                  </div>
                  <div className="space-y-2 mb-4">
                    {queueData.pending.map(item => {
                      const isExpanded = expandedQueue[item.message_id];
                      return (
                        <div
                          key={item.message_id}
                          className="rounded-lg"
                          style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                        >
                          <div className="flex items-center gap-3 p-3">
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
                              onClick={() => setExpandedQueue(prev => ({ ...prev, [item.message_id]: !prev[item.message_id] }))}
                              className="p-2 rounded-lg hover:bg-[var(--bg-surface)]"
                              title={isExpanded ? 'Collapse details' : 'Expand details'}
                            >
                              <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} style={{ color: 'var(--text-muted)' }} />
                            </button>
                            <button
                              onClick={() => handleAnalyzeSingle(item)}
                              disabled={analyzing}
                              className="btn-ghost h-8 px-3 text-xs disabled:opacity-50"
                            >
                              {analyzing ? '…' : 'Analyze'}
                            </button>
                            <button
                              onClick={() => { setDeleteItem(item); setShowDeleteDialog(true); }}
                              className="p-2 rounded-lg hover:bg-[var(--bg-surface)]"
                              title="Remove from queue"
                            >
                              <Trash2 className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                            </button>
                          </div>
                          {isExpanded && (
                            <div className="px-3 pb-3 pt-1 space-y-2 text-xs border-t" style={{ borderColor: 'var(--border)' }}>
                              <div className="grid grid-cols-2 gap-2 mt-2">
                                <div>
                                  <span className="text-[var(--text-muted)]">To:</span>
                                  <p className="truncate" style={{ color: 'var(--text-primary)' }}>{item.to || '—'}</p>
                                </div>
                                <div>
                                  <span className="text-[var(--text-muted)]">Date:</span>
                                  <p className="truncate" style={{ color: 'var(--text-primary)' }}>{item.date || '—'}</p>
                                </div>
                              </div>
                              {item.snippet && (
                                <div>
                                  <span className="text-[var(--text-muted)]">Preview:</span>
                                  <p className="line-clamp-2" style={{ color: 'var(--text-secondary)' }}>{item.snippet}</p>
                                </div>
                              )}
                              {item.labels && item.labels.length > 0 && (
                                <div className="flex flex-wrap gap-1">
                                  {item.labels.slice(0, 5).map((label, i) => (
                                    <span key={i} className="px-2 py-0.5 rounded-full text-xs" style={{ background: 'var(--bg-surface)', color: 'var(--text-muted)' }}>
                                      {label}
                                    </span>
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
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
        
        {/* ID Search */}
        <div className="relative flex-shrink-0">
          <input
            type="text"
            placeholder="Search by ID…"
            value={idSearch}
            onChange={e => setIdSearch(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleIdSearch()}
            className="input-base w-40 sm:w-48 pr-8"
          />
          {idSearch && (
            <button onClick={() => setIdSearch('')} className="absolute right-2 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
        
        {/* Generate Batch Report Button */}
        {selectedItems.length > 0 && (
          <button
            onClick={handleGenerateBatchReport}
            disabled={loadingBatchReport}
            className="btn-primary h-9 px-4 text-sm flex items-center gap-2"
          >
            {loadingBatchReport ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <FileBarChart className="w-4 h-4" />
            )}
            Report ({selectedItems.length})
          </button>
        )}
        
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
                  <th className="w-10">
                    <button onClick={handleSelectAllItems} className="p-1">
                      {selectedItems.length === filtered.length && filtered.length > 0 ? (
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
                  <th />
                </tr>
              </thead>
              <tbody>
                {filtered.map(a => {
                  const s       = score(a);
                  const subject = a.subject ?? a.email_metadata?.subject ?? a.file_name ?? a.filename ?? a.email_subject ?? 'Untitled';
                  const cat     = a.threat_category ?? a.category ?? '—';
                  const date    = a.created_at ?? a.analyzed_at;
                  const isSelected = selectedItems.some(i => i.id === a.id);
                  return (
                    <tr key={a.id} className="cursor-pointer" onClick={() => navigate(`/analysis/${a.id}`)}>
                      <td className="w-10" onClick={e => e.stopPropagation()}>
                        <button onClick={() => handleToggleSelectItem(a)}>
                          {isSelected ? (
                            <CheckSquare className="w-4 h-4" style={{ color: 'var(--brand)' }} />
                          ) : (
                            <Square className="w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                          )}
                        </button>
                      </td>
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
      
      {showBatchReport && (
        <BatchReportModal 
          data={batchReportData} 
          onClose={() => setShowBatchReport(false)} 
        />
      )}
    </div>
  );
}

/* ─── Batch Report Modal ────────────────────────────────────────────────── */
function BatchReportModal({ data, onClose }) {
  if (!data) return null;
  
  const stats = [
    { label: 'Total Analyzed', value: data.total_analyses ?? data.total ?? 0 },
    { label: 'Phishing', value: data.phishing_detected ?? 0 },
    { label: 'Malware', value: data.malware_detected ?? 0 },
    { label: 'Suspicious', value: data.suspicious_detected ?? 0 },
    { label: 'Safe', value: data.safe_emails ?? 0 },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative rounded-xl p-6 w-full max-w-2xl mx-4 shadow-2xl max-h-[90vh] overflow-y-auto"
        style={{ background: 'var(--bg-surface)' }}>
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-700" style={{ color: 'var(--text-primary)' }}>
            Batch Report
          </h2>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[var(--bg-elevated)]">
            <X className="w-5 h-5" style={{ color: 'var(--text-muted)' }} />
          </button>
        </div>

        <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
          Report for {data.total_analyses ?? data.analyses?.length ?? 0} selected analyses
        </p>

        {/* Stats */}
        <div className="grid grid-cols-3 sm:grid-cols-5 gap-3 mb-6">
          {stats.map(s => (
            <div key={s.label} className="text-center p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
              <div className="font-heading font-700 text-xl" style={{ color: 'var(--text-primary)' }}>{s.value}</div>
              <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Threat breakdown */}
        {data.threat_breakdown && data.threat_breakdown.length > 0 && (
          <div className="mb-6">
            <h3 className="font-600 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>Threat Breakdown</h3>
            <div className="space-y-2">
              {data.threat_breakdown.map((t, i) => (
                <div key={i} className="flex items-center justify-between p-2 rounded" style={{ background: 'var(--bg-elevated)' }}>
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{t.category}</span>
                  <span className="font-600 text-sm" style={{ color: t.category === 'Safe' ? 'var(--success)' : 'var(--danger)' }}>
                    {t.count}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Daily breakdown */}
        {data.daily_breakdown && data.daily_breakdown.length > 0 && (
          <div>
            <h3 className="font-600 text-sm mb-3" style={{ color: 'var(--text-primary)' }}>Daily Activity</h3>
            <div className="grid grid-cols-7 gap-1">
              {data.daily_breakdown.slice(0, 7).map((d, i) => (
                <div key={i} className="text-center p-2 rounded" style={{ background: 'var(--bg-elevated)' }}>
                  <div className="text-xs font-500" style={{ color: 'var(--text-muted)' }}>{d.day}</div>
                  <div className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>{d.analyzed ?? 0}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="mt-6 pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
          <button onClick={onClose} className="btn-primary w-full">Close</button>
        </div>
      </div>
    </div>
  );
}