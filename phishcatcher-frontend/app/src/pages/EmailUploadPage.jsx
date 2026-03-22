/**
 * EmailUploadPage.jsx
 * Drag-and-drop .eml upload with simulated progress, validation, and analysis redirect.
 */

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Upload, CheckCircle, X, Loader2, Zap, Shield, BarChart3, Info } from 'lucide-react';
import { toast } from 'sonner';
import { analysisApi } from '@/lib/api';

export default function EmailUploadPage() {
  const navigate = useNavigate();

  const [file,     setFile]     = useState(null);
  const [dragging, setDragging] = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [progress, setProgress] = useState(0);
  const [error,    setError]    = useState('');

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
        <p className="page-subtitle">Upload an .eml file to detect phishing threats in real time</p>
      </div>

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
        <button
          onClick={handleAnalyze}
          className="btn-primary w-full h-12 justify-center mt-5 text-[15px]"
        >
          <Zap className="w-5 h-5" /> Analyze email now
        </button>
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