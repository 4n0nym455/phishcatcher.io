import React from 'react';
import { Brain, Target, BarChart3, Info } from 'lucide-react';

function MLAnalysisCard({ analysis }) {
  if (!analysis?.ml_analysis) {
    return null;
  }

  const ml = analysis.ml_analysis;
  
  return (
    <div className="rounded-2xl p-6" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
      <div className="flex items-center gap-3 mb-4">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center"
             style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
          <Brain className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-heading font-600 text-lg" style={{ color: 'var(--text-primary)' }}>
            Machine Learning Analysis
          </h3>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            AI-powered threat detection
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Prediction Result */}
        <div className="rounded-xl p-4" style={{ background: 'var(--background)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4" style={{ color: 'var(--brand)' }} />
            <span className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>
              Prediction Result
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Classification:</span>
              <span className={`text-xs font-600 px-2 py-1 rounded-full ${
                ml.is_phishing 
                  ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400' 
                  : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
              }`}>
                {ml.is_phishing ? 'Phishing' : 'Safe'}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Category:</span>
              <span className="text-xs font-500" style={{ color: 'var(--text-secondary)' }}>
                {ml.category || 'Unknown'}
              </span>
            </div>
          </div>
        </div>

        {/* Confidence Score */}
        <div className="rounded-xl p-4" style={{ background: 'var(--background)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2 mb-2">
            <BarChart3 className="w-4 h-4" style={{ color: 'var(--brand)' }} />
            <span className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>
              Confidence Score
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Model Confidence:</span>
              <span className="text-xs font-600" style={{ color: 'var(--text-secondary)' }}>
                {ml.confidence ? `${(ml.confidence * 100).toFixed(1)}%` : 'N/A'}
              </span>
            </div>
            {ml.phishing_probability !== undefined && (
              <div className="space-y-1">
                <div className="flex justify-between items-center">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Phishing Probability:</span>
                  <span className="text-xs font-600" style={{ color: 'var(--danger)' }}>
                    {(ml.phishing_probability * 100).toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 rounded-full overflow-hidden" style={{ background: 'var(--border)' }}>
                  <div 
                    className="h-full rounded-full transition-all duration-500"
                    style={{ 
                      width: `${ml.phishing_probability * 100}%`, 
                      background: 'var(--danger)' 
                    }} 
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Probabilities */}
        {(ml.phishing_probability !== undefined && ml.safe_probability !== undefined) && (
          <div className="rounded-xl p-4" style={{ background: 'var(--background)', border: '1px solid var(--border)' }}>
            <div className="flex items-center gap-2 mb-2">
              <Info className="w-4 h-4" style={{ color: 'var(--brand)' }} />
              <span className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>
                Probability Breakdown
              </span>
            </div>
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Safe:</span>
                <span className="text-xs font-600" style={{ color: 'var(--success)' }}>
                  {(ml.safe_probability * 100).toFixed(1)}%
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Phishing:</span>
                <span className="text-xs font-600" style={{ color: 'var(--danger)' }}>
                  {(ml.phishing_probability * 100).toFixed(1)}%
                </span>
              </div>
            </div>
          </div>
        )}

        {/* Model Info */}
        <div className="rounded-xl p-4" style={{ background: 'var(--background)', border: '1px solid var(--border)' }}>
          <div className="flex items-center gap-2 mb-2">
            <Brain className="w-4 h-4" style={{ color: 'var(--brand)' }} />
            <span className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>
              Model Information
            </span>
          </div>
          <div className="space-y-2">
            <div className="flex justify-between items-center">
              <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Version:</span>
              <span className="text-xs font-500" style={{ color: 'var(--text-secondary)' }}>
                {ml.model_version || 'Unknown'}
              </span>
            </div>
            {ml.features_used && (
              <div className="flex justify-between items-center">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Features Used:</span>
                <span className="text-xs font-500" style={{ color: 'var(--text-secondary)' }}>
                  {ml.features_used}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MLAnalysisCard;
