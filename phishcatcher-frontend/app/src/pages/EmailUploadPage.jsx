/**
 * EmailUploadPage.jsx
 * Drag-and-drop .eml upload with simulated progress, validation, and analysis redirect.
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, CheckCircle, X, Loader2, Shield, BarChart3, Info, Mail, RefreshCw, Layers, Search, ChevronDown, HelpCircle, XCircle, Zap } from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi, authApi } from '@/lib/api';

const FILTER_CHIPS = [
  { id: 'unread', label: 'Unread', query: 'is:unread' },
  { id: 'attachments', label: 'Has Attachments', query: 'has:attachment' },
  { id: '7days', label: 'Last 7 days', query: 'newer_than:7d' },
  { id: '30days', label: 'Last 30 days', query: 'newer_than:30d' },
];

export default function EmailUploadPage() {
  const navigate = useNavigate();

  const [file,     setFile]     = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [progress, setProgress] = useState(0);
  const [error,    setError]    = useState('');

  /* ── Gmail state ── */
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailLoading, setGmailLoading] = useState(false);
  const [gmailEmails, setGmailEmails] = useState([]);
  const [selectedEmails, setSelectedEmails] = useState([]);
  const [activeTab, setActiveTab] = useState('upload');
  const [searchQuery, setSearchQuery] = useState('');
  const [activeFilters, setActiveFilters] = useState([]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showHelp, setShowHelp] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [queryHelp, setQueryHelp] = useState(null);
  
  const [filters, setFilters] = useState({
    filterType: '',
    hasAttachments: null,
    dateFrom: '',
    dateTo: '',
    fromAddress: '',
    subject: ''
  });
  const [page, setPage] = useState(1);
  const [totalResults, setTotalResults] = useState(0);
  const [emailCount, setEmailCount] = useState(0);
  
  /* ── Gmail Accounts ── */
  const [gmailAccounts, setGmailAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);

  useEffect(() => {
    authApi.gmail.getStatus()
      .then(res => {
        setGmailConnected(res.connected);
        setGmailAccounts(res.accounts || []);
      })
      .catch(() => setGmailConnected(false));
    
    authApi.gmail.getQueryHelp()
      .then(setQueryHelp)
      .catch(() => {});
  }, []);

  const buildQuery = useCallback(() => {
    const parts = [];
    if (searchQuery.trim()) {
      parts.push(searchQuery.trim());
    }
    activeFilters.forEach(f => {
      const chip = FILTER_CHIPS.find(c => c.id === f);
      if (chip) parts.push(chip.query);
    });
    return parts.join(' ');
  }, [searchQuery, activeFilters]);

  const handleLoadGmailEmails = async (pageNum = 1) => {
    setGmailLoading(true);
    setPage(pageNum);
    try {
      const hasStructuredFilters = filters.filterType || filters.hasAttachments !== null || 
        filters.dateFrom || filters.dateTo || filters.fromAddress || filters.subject;
      const hasSearchQuery = searchQuery.trim().length > 0;
      const providerId = selectedAccount || undefined;
      
      let data;
      if (hasStructuredFilters) {
        data = await authApi.gmail.filterEmails({
          filterType: filters.filterType || undefined,
          hasAttachments: filters.hasAttachments ?? undefined,
          dateFrom: filters.dateFrom || undefined,
          dateTo: filters.dateTo || undefined,
          fromAddress: filters.fromAddress || undefined,
          subject: filters.subject || undefined,
          page: pageNum,
          maxResults: 20,
          providerId
        });
      } else if (hasSearchQuery || activeFilters.length > 0) {
        const query = buildQuery();
        data = await authApi.gmail.listEmails(pageNum, 20, query || null, providerId);
      } else {
        data = await authApi.gmail.listEmails(pageNum, 20, null, providerId);
      }
      setGmailEmails(data.emails || []);
      setTotalResults(data.total_results || data.emails?.length || 0);
      setEmailCount(data.emails?.length || 0);
      if (data.error) {
        toast.error(data.error);
      } else if (data.emails?.length === 0) {
        toast.info('No emails match your filters');
      }
    } catch (err) { toast.error(err.message ?? 'Failed to load emails'); }
    finally { setGmailLoading(false); }
  };

  const handleToggleFilter = (filterId) => {
    setActiveFilters(prev =>
      prev.includes(filterId)
        ? prev.filter(f => f !== filterId)
        : [...prev, filterId]
    );
  };

  const handleClearFilters = () => {
    setSearchQuery('');
    setActiveFilters([]);
    setFilters({
      filterType: '',
      hasAttachments: null,
      dateFrom: '',
      dateTo: '',
      fromAddress: '',
      subject: ''
    });
  };

  const handleToggleEmail = (msgId) => {
    setSelectedEmails(prev => 
      prev.includes(msgId) 
        ? prev.filter(id => id !== msgId)
        : [...prev, msgId]
    );
  };

  const handleSendToQueue = async () => {
    if (selectedEmails.length === 0 && !file) return;
    setLoading(true);
    try {
      if (selectedEmails.length > 0) {
        await authApi.gmail.queueEmails(selectedEmails, selectedAccount);
        toast.success(`${selectedEmails.length} emails added to queue`);
      }
      if (file) {
        const result = await analysisApi.uploadEmail(file, true);
        toast.success('File added to queue');
      }
      setSelectedEmails([]);
      setGmailEmails([]);
      setFile(null);
      navigate('/analysis');
    } catch (err) { toast.error(err.message ?? 'Failed to queue'); }
    finally { setLoading(false); }
  };

  const MAX_SIZE_MB = 10;

  const validate = f => {
    if (!f) return 'No file selected.';
    if (!f.name.toLowerCase().endsWith('.eml')) return 'Only .eml files are supported.';
    if (f.size > MAX_SIZE_MB * 1024 * 1024) return `File size must be under ${MAX_SIZE_MB} MB.`;
    return null;
  };

  const pickFile = f => {
    const err = validate(f);
    if (err) { setError(err); return; }
    setError('');
    setFile(f);
  };

  const onDrop = useCallback(e => {
    e.preventDefault();
    setDragging(false);
    pickFile(e.dataTransfer.files[0]);
  }, []);

  const handleAnalyze = async () => {
    if (!file) return;
    setError('');
    setLoading(true);
    setProgress(0);

    // Simulated progress for UX feedback
    const iv = setInterval(() => setProgress(p => Math.min(p + 10, 85)), 280);

    try {
      const result = await analysisApi.uploadEmail(file);
      clearInterval(iv);
      setProgress(100);
      toast.success('Analysis started! Redirecting…');
      setTimeout(() => navigate(`/analysis/${result.id ?? result.analysis_id}`), 300);
    } catch (err) {
      clearInterval(iv);
      setProgress(0);
      setError(err.message ?? 'Upload failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const removeFile = e => {
    e.stopPropagation();
    setFile(null);
    setError('');
    setProgress(0);
    const inp = document.getElementById('eml-file-input');
    if (inp) inp.value = '';
  };

  const fileSizeLabel = file
    ? file.size < 1024 * 1024
      ? `${(file.size / 1024).toFixed(1)} KB`
      : `${(file.size / (1024 * 1024)).toFixed(2)} MB`
    : '';

  return (
    <div className="max-w-2xl mx-auto animate-fade-in">

      <div className="page-header">
        <h1 className="page-title">Analyze Email</h1>
        <p className="page-subtitle">Upload an .eml file or select from Gmail to detect phishing threats</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 mb-4">
        <button
          onClick={() => setActiveTab('upload')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-500 transition-all ${
            activeTab === 'upload' ? 'btn-primary' : 'btn-ghost'
          }`}
        >
          <Upload className="w-4 h-4" /> Upload .eml
        </button>
        <button
          onClick={() => { setActiveTab('gmail'); if (!gmailConnected) toast.error('Connect Gmail in Settings first'); }}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-500 transition-all ${
            activeTab === 'gmail' ? 'btn-primary' : 'btn-ghost'
          }`}
        >
          <Mail className="w-4 h-4" /> Gmail
        </button>
      </div>

      {activeTab === 'gmail' && (
        <div className="rounded-2xl p-5" style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
          {!gmailConnected ? (
            <div className="text-center py-6">
              <Mail className="w-10 h-10 mx-auto mb-3 opacity-30" style={{ color: 'var(--text-muted)' }} />
              <p className="text-sm mb-3" style={{ color: 'var(--text-muted)' }}>Connect Gmail in Settings to load emails</p>
              <button onClick={() => navigate('/settings')} className="btn-secondary text-sm">Go to Settings</button>
            </div>
          ) : (
            <>
              {/* Account Selector */}
              {gmailAccounts.length > 0 && (
                <div className="flex items-center gap-2 mb-3">
                  <label className="text-xs shrink-0" style={{ color: 'var(--text-muted)' }}>Source:</label>
                  <select
                    value={selectedAccount || ''}
                    onChange={(e) => {
                      setSelectedAccount(e.target.value);
                      setGmailEmails([]);
                      setSelectedEmails([]);
                    }}
                    className="h-8 px-2 rounded text-xs flex-1"
                    style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                  >
                    {gmailAccounts.map(acc => (
                      <option key={acc.id} value={acc.id}>
                        {acc.email}
                        {acc.is_default ? ' (Default)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              
              {/* Search Bar */}
              <div className="flex items-center gap-2 mb-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: 'var(--text-muted)' }} />
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleLoadGmailEmails()}
                    placeholder="Search emails... (e.g., from:bank subject:urgent)"
                    className="w-full h-9 pl-9 pr-20 rounded-lg text-sm"
                    style={{
                      background: 'var(--bg-elevated)',
                      border: '1px solid var(--border)',
                      color: 'var(--text-primary)'
                    }}
                  />
                  <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center gap-1">
                    {searchQuery && (
                      <button
                        onClick={() => setSearchQuery('')}
                        className="p-1 rounded hover:bg-[var(--bg-surface)]"
                      >
                        <XCircle className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                      </button>
                    )}
                    <button
                      onClick={() => setShowHelp(!showHelp)}
                      className="p-1 rounded hover:bg-[var(--bg-surface)]"
                      title="Search help"
                    >
                      <HelpCircle className="w-3.5 h-3.5" style={{ color: 'var(--text-muted)' }} />
                    </button>
                    <button
                      onClick={() => setShowAdvanced(!showAdvanced)}
                      className="text-xs px-2 py-0.5 rounded"
                      style={{ 
                        background: showAdvanced ? 'var(--brand-dim)' : 'transparent',
                        color: showAdvanced ? 'var(--brand)' : 'var(--text-muted)'
                      }}
                    >
                      Advanced
                    </button>
                  </div>
                </div>
              </div>

              {/* Search Help Dropdown */}
              {showHelp && queryHelp && (
                <div className="mb-3 p-3 rounded-lg text-xs" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <p className="font-600 mb-2" style={{ color: 'var(--text-primary)' }}>Quick Examples:</p>
                  <div className="space-y-1">
                    {queryHelp.examples.map((ex, i) => (
                      <button
                        key={i}
                        onClick={() => { setSearchQuery(ex.query); setShowHelp(false); }}
                        className="block w-full text-left px-2 py-1 rounded hover:bg-[var(--bg-surface)]"
                        style={{ color: 'var(--text-secondary)' }}
                      >
                        <span className="font-mono" style={{ color: 'var(--brand)' }}>{ex.query}</span>
                        <span className="ml-2">{ex.label}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Advanced Mode */}
              {showAdvanced && (
                <div className="mb-3 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <p className="text-xs font-600 mb-2" style={{ color: 'var(--text-muted)' }}>Gmail Search Operators</p>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                    <div><code className="text-[var(--brand)]">from:</code> Sender email</div>
                    <div><code className="text-[var(--brand)]">to:</code> Recipient</div>
                    <div><code className="text-[var(--brand)]">subject:</code> In subject</div>
                    <div><code className="text-[var(--brand)]">has:attachment</code> Has files</div>
                    <div><code className="text-[var(--brand)]">newer_than:7d</code> Age filter</div>
                    <div><code className="text-[var(--brand)]">is:unread</code> Status</div>
                    <div><code className="text-[var(--brand)]">after:</code> Date from</div>
                    <div><code className="text-[var(--brand)]">before:</code> Date to</div>
                  </div>
                </div>
              )}

              {/* Filter Panel Toggle */}
              <div className="flex items-center justify-between mb-3">
                <button
                  onClick={() => setShowFilters(!showFilters)}
                  className="flex items-center gap-2 text-xs px-3 py-1.5 rounded-lg"
                  style={{ 
                    background: showFilters ? 'var(--brand-dim)' : 'var(--bg-elevated)',
                    color: showFilters ? 'var(--brand)' : 'var(--text-secondary)',
                    border: `1px solid ${showFilters ? 'var(--brand)' : 'var(--border)'}`
                  }}
                >
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showFilters ? 'rotate-180' : ''}`} />
                  Filters
                </button>
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  {gmailEmails.length > 0 && `${totalResults > 0 ? totalResults : gmailEmails.length} emails found`}
                </span>
              </div>

              {/* Filter Panel */}
              {showFilters && (
                <div className="mb-4 p-4 rounded-lg" style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                    <div>
                      <label className="text-xs block mb-1" style={{ color: 'var(--text-muted)' }}>Filter Type</label>
                      <select
                        value={filters.filterType}
                        onChange={(e) => setFilters(f => ({ ...f, filterType: e.target.value }))}
                        className="w-full h-8 px-2 rounded text-xs"
                        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                      >
                        <option value="">All</option>
                        <option value="unread">Unread</option>
                        <option value="starred">Starred</option>
                        <option value="important">Important</option>
                        <option value="promotions">Promotions</option>
                        <option value="social">Social</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs block mb-1" style={{ color: 'var(--text-muted)' }}>Has Attachments</label>
                      <select
                        value={filters.hasAttachments === null ? '' : filters.hasAttachments.toString()}
                        onChange={(e) => setFilters(f => ({ ...f, hasAttachments: e.target.value === '' ? null : e.target.value === 'true' }))}
                        className="w-full h-8 px-2 rounded text-xs"
                        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                      >
                        <option value="">Any</option>
                        <option value="true">Yes</option>
                        <option value="false">No</option>
                      </select>
                    </div>
                    <div>
                      <label className="text-xs block mb-1" style={{ color: 'var(--text-muted)' }}>From Address</label>
                      <input
                        type="text"
                        value={filters.fromAddress}
                        onChange={(e) => setFilters(f => ({ ...f, fromAddress: e.target.value }))}
                        placeholder="e.g., bank.com"
                        className="w-full h-8 px-2 rounded text-xs"
                        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                      />
                    </div>
                    <div>
                      <label className="text-xs block mb-1" style={{ color: 'var(--text-muted)' }}>Email Contains</label>
                      <input
                        type="text"
                        value={filters.subject}
                        onChange={(e) => setFilters(f => ({ ...f, subject: e.target.value }))}
                        placeholder="Keyword in email body"
                        className="w-full h-8 px-2 rounded text-xs"
                        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                      />
                    </div>
                    <div>
                      <label className="text-xs block mb-1" style={{ color: 'var(--text-muted)' }}>Date From</label>
                      <input
                        type="date"
                        value={filters.dateFrom}
                        onChange={(e) => setFilters(f => ({ ...f, dateFrom: e.target.value }))}
                        className="w-full h-8 px-2 rounded text-xs"
                        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                      />
                    </div>
                    <div>
                      <label className="text-xs block mb-1" style={{ color: 'var(--text-muted)' }}>Date To</label>
                      <input
                        type="date"
                        value={filters.dateTo}
                        onChange={(e) => setFilters(f => ({ ...f, dateTo: e.target.value }))}
                        className="w-full h-8 px-2 rounded text-xs"
                        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                      />
                    </div>
                  </div>
                  <div className="flex gap-2 mt-3">
                    <button
                      onClick={handleClearFilters}
                      className="text-xs px-3 py-1.5 rounded"
                      style={{ background: 'var(--bg-surface)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}
                    >
                      Clear All
                    </button>
                    <button
                      onClick={() => handleLoadGmailEmails(1)}
                      className="text-xs px-3 py-1.5 rounded"
                      style={{ background: 'var(--brand)', color: 'white' }}
                    >
                      Apply Filters
                    </button>
                  </div>
                </div>
              )}

              {/* Filter Chips */}
              <div className="flex flex-wrap items-center gap-2 mb-3">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Quick filters:</span>
                {FILTER_CHIPS.map(chip => (
                  <button
                    key={chip.id}
                    onClick={() => handleToggleFilter(chip.id)}
                    className="text-xs px-3 py-1 rounded-full transition-all"
                    style={{
                      background: activeFilters.includes(chip.id) ? 'var(--brand-dim)' : 'var(--bg-elevated)',
                      color: activeFilters.includes(chip.id) ? 'var(--brand)' : 'var(--text-secondary)',
                      border: `1px solid ${activeFilters.includes(chip.id) ? 'var(--brand)' : 'var(--border)'}`
                    }}
                  >
                    {chip.label}
                  </button>
                ))}
                {(searchQuery || activeFilters.length > 0) && (
                  <button
                    onClick={handleClearFilters}
                    className="text-xs px-2 py-1 rounded flex items-center gap-1"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    <XCircle className="w-3 h-3" /> Clear
                  </button>
                )}
              </div>

              {/* Current Query Display */}
              {buildQuery() && (
                <div className="mb-3 text-xs px-3 py-2 rounded-lg flex items-center justify-between" style={{ background: 'var(--bg-elevated)' }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)' }}>Active query: </span>
                    <code className="font-mono" style={{ color: 'var(--brand)' }}>{buildQuery()}</code>
                  </div>
                  <span className="text-[var(--text-muted)]">{gmailEmails.length} results</span>
                </div>
              )}

              {/* Action Bar */}
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>
                  {selectedEmails.length > 0 ? `${selectedEmails.length} selected` : 'Select emails to analyze'}
                </p>
                <button 
                  onClick={() => handleLoadGmailEmails()} 
                  disabled={gmailLoading}
                  className="btn-ghost h-8 px-3 text-xs"
                >
                  {gmailLoading ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <RefreshCw className="w-3 h-3 mr-1" />}
                  Search
                </button>
              </div>

              {/* Email List */}
              {gmailEmails.length > 0 ? (
                <div className="rounded-lg border overflow-hidden" style={{ borderColor: 'var(--border)', maxHeight: '320px', overflowY: 'auto' }}>
                  <table className="w-full text-xs">
                    <thead className="sticky top-0" style={{ background: 'var(--bg-elevated)' }}>
                      <tr>
                        <th className="p-2 text-left w-8">
                          <input 
                            type="checkbox"
                            checked={selectedEmails.length === gmailEmails.length && gmailEmails.length > 0}
                            onChange={() => {
                              if (selectedEmails.length === gmailEmails.length) {
                                setSelectedEmails([]);
                              } else {
                                setSelectedEmails(gmailEmails.map(e => e.id));
                              }
                            }}
                            className="rounded"
                          />
                        </th>
                        <th className="p-2 text-left">From</th>
                        <th className="p-2 text-left">Subject</th>
                        <th className="p-2 text-left">Date</th>
                      </tr>
                    </thead>
                    <tbody>
                      {gmailEmails.map(email => (
                        <tr 
                          key={email.id}
                          style={{ 
                            background: selectedEmails.includes(email.id) ? 'var(--brand-dim)' : 'transparent',
                            borderBottom: '1px solid var(--border)'
                          }}
                        >
                          <td className="p-2">
                            <input 
                              type="checkbox" 
                              checked={selectedEmails.includes(email.id)}
                              onChange={() => handleToggleEmail(email.id)}
                              className="rounded"
                            />
                          </td>
                          <td className="p-2 truncate max-w-[120px]" style={{ color: 'var(--text-primary)' }}>{email.from || '—'}</td>
                          <td className="p-2 truncate max-w-[180px]" style={{ color: 'var(--text-primary)' }}>{email.subject || 'No Subject'}</td>
                          <td className="p-2" style={{ color: 'var(--text-muted)' }}>{email.date || '—'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8">
                  <Search className="w-8 h-8 mx-auto mb-2 opacity-30" style={{ color: 'var(--text-muted)' }} />
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                    {searchQuery || activeFilters.length > 0 ? 'No emails match your search' : 'Enter a search or select filters, then click Search'}
                  </p>
                </div>
              )}

              {selectedEmails.length > 0 && (
                <button
                  onClick={handleSendToQueue}
                  disabled={loading}
                  className="btn-primary w-full h-10 justify-center mt-4 text-sm"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Layers className="w-4 h-4 mr-2" />}
                  Send to Queue ({selectedEmails.length})
                </button>
              )}

              {totalResults > 20 && (
                <div className="flex items-center justify-between mt-4 text-xs" style={{ color: 'var(--text-muted)' }}>
                  <span>Showing {gmailEmails.length} of {totalResults}</span>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => handleLoadGmailEmails(page - 1)}
                      disabled={page === 1 || gmailLoading}
                      className="px-2 py-1 rounded"
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                    >
                      Previous
                    </button>
                    <span>Page {page}</span>
                    <button
                      onClick={() => handleLoadGmailEmails(page + 1)}
                      disabled={gmailEmails.length < 20 || gmailLoading}
                      className="px-2 py-1 rounded"
                      style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {activeTab === 'upload' && (
      <>
      {/* Drop zone */}
      <div
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => !file && !loading && document.getElementById('eml-file-input').click()}
        className="rounded-2xl transition-all duration-200 flex items-center justify-center"
        style={{
          minHeight: 200,
          padding: '3rem 2rem',
          textAlign: 'center',
          cursor: file || loading ? 'default' : 'pointer',
          background: dragging ? 'var(--brand-dim)' : file ? 'var(--success-dim)' : 'var(--bg-surface)',
          border: `2px dashed ${dragging ? 'var(--brand)' : file ? 'var(--success)' : 'var(--border-strong)'}`,
        }}
      >
        <input
          id="eml-file-input"
          type="file"
          accept=".eml"
          className="hidden"
          onChange={e => pickFile(e.target.files[0])}
        />

        {loading ? (
          <div className="w-full space-y-4">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto"
              style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
              <Loader2 className="w-6 h-6 animate-spin" />
            </div>
            <div>
              <p className="font-600 mb-1" style={{ color: 'var(--text-primary)' }}>Analyzing email…</p>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Running ML threat detection</p>
            </div>
            <div className="max-w-xs mx-auto">
              <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                <div
                  className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${progress}%`, background: 'var(--brand)' }}
                />
              </div>
              <p className="text-xs mt-1 text-right" style={{ color: 'var(--text-muted)' }}>{progress}%</p>
            </div>
          </div>
        ) : file ? (
          <div className="space-y-3">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto"
              style={{ background: 'var(--success-dim)', color: 'var(--success)' }}>
              <CheckCircle className="w-7 h-7" />
            </div>
            <div>
              <p className="font-600 text-base mb-0.5" style={{ color: 'var(--text-primary)' }}>{file.name}</p>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{fileSizeLabel}</p>
            </div>
            <button
              onClick={removeFile}
              className="text-xs font-500 hover:underline inline-flex items-center gap-1"
              style={{ color: 'var(--danger)' }}
            >
              <X className="w-3.5 h-3.5" /> Remove file
            </button>
          </div>
        ) : (
          <div className="space-y-3">
            <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto"
              style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
              <Upload className="w-7 h-7" />
            </div>
            <div>
              <p className="font-600 text-base mb-1" style={{ color: 'var(--text-primary)' }}>
                {dragging ? 'Drop your file here' : 'Drop your .eml file here'}
              </p>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                or{' '}
                <span className="font-600 underline" style={{ color: 'var(--brand)' }}>browse files</span>
                {' '}— max {MAX_SIZE_MB} MB
              </p>
            </div>
            <div
              className="inline-flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-full"
              style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}
            >
              <Info className="w-3 h-3" /> Only .eml files are supported
            </div>
          </div>
        )}
      </div>

      {error && <div className="alert-error mt-4">{error}</div>}

      {file && !loading && (
        <div className="flex gap-2 mt-5">
          <button
            onClick={handleSendToQueue}
            disabled={loading}
            className="btn-primary flex-1 h-12 justify-center text-[15px]"
          >
            <Layers className="w-5 h-5" /> Send to Queue
          </button>
        </div>
      )}
      </>
      )}

      {/* Stats strip */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mt-8">
        {[
          { icon: Shield,    value: '97.4%', label: 'Detection accuracy', color: 'var(--brand)',   bg: 'var(--brand-dim)'   },
          { icon: Zap,       value: '< 3s',  label: 'Analysis time',      color: 'var(--success)', bg: 'var(--success-dim)' },
          { icon: BarChart3, value: '12+',   label: 'Threat categories',  color: 'var(--threat)',  bg: 'var(--threat-dim)'  },
        ].map(s => (
          <div key={s.label} className="stat-card text-center">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center mx-auto mb-2"
              style={{ background: s.bg, color: s.color }}>
              <s.icon className="w-4 h-4" />
            </div>
            <div className="stat-value text-2xl" style={{ color: s.color }}>{s.value}</div>
            <div className="stat-label">{s.label}</div>
          </div>
        ))}
      </div>

      {/* What we analyze */}
      <div className="mt-8 rounded-2xl p-5"
        style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)' }}>
        <p className="text-xs font-700 uppercase tracking-widest mb-4" style={{ color: 'var(--text-muted)' }}>
          What we analyze
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            'Sender domain spoofing', 'Malicious URL detection',
            'Header anomalies',       'Urgency manipulation',
            'Reply-to mismatch',      'Lookalike domains',
            'Attachment risk',        'Social engineering',
          ].map(item => (
            <div key={item} className="flex items-start gap-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
              <CheckCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" style={{ color: 'var(--success)' }} />
              {item}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}