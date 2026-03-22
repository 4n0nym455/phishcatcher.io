/**
 * ModelManagement.jsx
 * Admin page: AI model metrics, version info, and retrain trigger.
 */

import { useState, useEffect } from 'react';
import { Database, RefreshCw, Loader2, Activity, TrendingUp } from 'lucide-react';
import { toast } from 'sonner';
import { adminApi } from '@/lib/api';

export default function ModelManagement() {
  const [model,      setModel]      = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [retraining, setRetraining] = useState(false);
  const [error,      setError]      = useState('');

  const fetchModel = async () => {
    try {
      const data = await adminApi.getModelInfo();
      setModel(data);
    } catch (err) {
      setError(err.message ?? 'Failed to load model info');
    }
  };

  useEffect(() => {
    fetchModel().finally(() => setLoading(false));
  }, []);

  const handleRetrain = async () => {
    if (!window.confirm(
      'Start model retraining? This will use all current analysis data and may take 5–20 minutes.\n\nThe model will remain operational during retraining.'
    )) return;

    setRetraining(true);
    try {
      await adminApi.retrainModel();
      toast.success('Retraining job started!');
      // Poll for updates
      setTimeout(async () => {
        await fetchModel();
      }, 3000);
    } catch (err) {
      toast.error(err.message ?? 'Failed to start retraining');
    } finally {
      setRetraining(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--brand)' }} />
      </div>
    );
  }

  return (
    <div className="max-w-2xl animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">AI Model Management</h1>
        <p className="page-subtitle">Monitor and retrain the phishing detection model</p>
      </div>

      {error && <div className="alert-error mb-6">{error}</div>}

      {model && (
        <div className="space-y-5">

          {/* Status banner */}
          <div
            className="rounded-2xl p-5 flex items-center gap-4"
            style={{
              background: model.status === 'active' ? 'var(--success-dim)' : 'var(--threat-dim)',
              border: `1px solid ${model.status === 'active' ? 'var(--success)' : 'var(--threat)'}`,
            }}
          >
            <div
              className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
              style={{
                background: model.status === 'active' ? 'var(--success)' : 'var(--threat)',
                color: '#fff',
              }}
            >
              <Database className="w-6 h-6" />
            </div>
            <div>
              <p className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
                Model v{model.version ?? '—'} — {model.status ?? 'unknown'}
              </p>
              <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {model.algorithm ?? 'Unknown algorithm'} ·
                Last trained: {model.last_trained ? new Date(model.last_trained).toLocaleDateString() : '—'}
              </p>
            </div>
          </div>

          {/* Performance metrics */}
          <div className="card p-6">
            <h2 className="font-heading font-700 text-base mb-4" style={{ color: 'var(--text-primary)' }}>
              Performance Metrics
            </h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Accuracy',  value: model.accuracy  ? `${(model.accuracy  * 100).toFixed(2)}%` : '—', color: 'var(--success)' },
                { label: 'Precision', value: model.precision ? `${(model.precision * 100).toFixed(2)}%` : '—', color: 'var(--brand)'   },
                { label: 'Recall',    value: model.recall    ? `${(model.recall    * 100).toFixed(2)}%` : '—', color: 'var(--brand)'   },
                { label: 'F1 Score',  value: model.f1_score  ? model.f1_score.toFixed(4)               : '—', color: 'var(--success)' },
              ].map(s => (
                <div key={s.label} className="rounded-xl p-4"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <p className="text-xs font-700 uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>
                    {s.label}
                  </p>
                  <p className="font-heading font-700 text-2xl" style={{ color: s.color }}>{s.value}</p>
                </div>
              ))}
            </div>

            {/* Accuracy bar */}
            {model.accuracy && (
              <div className="mt-5">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-600 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                    Overall accuracy
                  </span>
                  <span className="font-heading font-700 text-sm" style={{ color: 'var(--success)' }}>
                    {(model.accuracy * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-3 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${model.accuracy * 100}%`, background: 'var(--success)' }}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Model info */}
          <div className="card p-6">
            <h2 className="font-heading font-700 text-base mb-4" style={{ color: 'var(--text-primary)' }}>
              Model Information
            </h2>
            <div className="space-y-0"
              style={{ borderTop: '1px solid var(--border)' }}>
              {[
                { label: 'Version',            value: model.version        ?? '—' },
                { label: 'Algorithm',          value: model.algorithm      ?? '—' },
                { label: 'Training samples',   value: model.training_samples ? model.training_samples.toLocaleString() : '—' },
                { label: 'Model size',         value: model.model_size     ?? '—' },
                { label: 'Feature count',      value: model.feature_count  ?? '—' },
                { label: 'Last trained',       value: model.last_trained   ? new Date(model.last_trained).toLocaleString() : '—' },
                { label: 'Status',             value: model.status         ?? '—' },
              ].map(row => (
                <div key={row.label} className="flex gap-4 py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
                  <span className="text-xs font-600 uppercase tracking-wide w-36 shrink-0 pt-0.5"
                    style={{ color: 'var(--text-muted)' }}>
                    {row.label}
                  </span>
                  <span className="text-sm" style={{ color: 'var(--text-secondary)' }}>{row.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Retrain */}
          <div className="card p-6">
            <h2 className="font-heading font-700 text-base mb-1" style={{ color: 'var(--text-primary)' }}>
              Retrain Model
            </h2>
            <p className="text-sm mb-5" style={{ color: 'var(--text-muted)' }}>
              Trigger a full retraining using all current analysis data. The model stays operational during training.
              Retraining typically takes 5–20 minutes depending on dataset size.
            </p>
            <button
              onClick={handleRetrain}
              disabled={retraining}
              className="btn-primary h-10"
            >
              {retraining
                ? <><Loader2 className="w-4 h-4 animate-spin" />Retraining in progress…</>
                : <><RefreshCw className="w-4 h-4" />Start retraining</>
              }
            </button>
          </div>
        </div>
      )}
    </div>
  );
}