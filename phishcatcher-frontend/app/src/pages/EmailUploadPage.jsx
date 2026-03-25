/**
 * EmailUploadPage.jsx
 * Drag-and-drop .eml upload with simulated progress, validation, and analysis redirect.
 */

import { useState, useCallback, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, CheckCircle, X, Loader2, Zap, Shield, BarChart3, Info, Mail, RefreshCw, Layers } from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi, authApi } from '@/lib/api';

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

  useEffect(() => {
    authApi.gmail.getStatus()
      .then(res => setGmailConnected(res.connected))
      .catch(() => setGmailConnected(false));
  }, []);

  const handleLoadGmailEmails = async () => {
    setGmailLoading(true);
    try {
      const data = await authApi.gmail.listEmails(1, 20);
      setGmailEmails(data.emails || []);
    } catch (err) { toast.error(err.message ?? 'Failed to load emails'); }
    finally { setGmailLoading(false); }
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
        await authApi.gmail.analyzeEmails(selectedEmails);
        toast.success(`${selectedEmails.length} emails queued for analysis`);
      }
      if (file) {
        const result = await analysisApi.uploadEmail(file);
        localStorage.setItem('pending_analysis_id', result.id ?? result.analysis_id);
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
      toast.success('Analysis complete!');
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
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>Select emails to analyze</p>
                <button 
                  onClick={handleLoadGmailEmails} 
                  disabled={gmailLoading}
                  className="btn-ghost h-8 px-3 text-xs"
                >
                  {gmailLoading ? <Loader2 className="w-3 h-3 animate-spin mr-1" /> : <RefreshCw className="w-3 h-3 mr-1" />}
                  Load
                </button>
              </div>
              {gmailEmails.length > 0 ? (
                <div className="rounded-lg border overflow-hidden" style={{ borderColor: 'var(--border)', maxHeight: '300px', overflowY: 'auto' }}>
                  <table className="w-full text-xs">
                    <thead className="sticky top-0" style={{ background: 'var(--bg-elevated)' }}>
                      <tr>
                        <th className="p-2 text-left w-8"></th>
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
                <p className="text-xs py-4 text-center" style={{ color: 'var(--text-muted)' }}>Click "Load" to fetch recent emails</p>
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
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Running AI threat detection</p>
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
            onClick={handleAnalyze}
            className="btn-primary flex-1 h-12 justify-center text-[15px]"
          >
            <Zap className="w-5 h-5" /> Analyze now
          </button>
          <button
            onClick={handleSendToQueue}
            disabled={loading}
            className="btn-secondary flex-1 h-12 justify-center text-[15px]"
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