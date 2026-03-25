/**
 * PasswordPages.jsx
 * Exports:
 *   ForgotPasswordPage  — POST /auth/forgot-password
 *   ResetPasswordPage   — POST /auth/reset-password (reads ?token= from URL)
 */

import { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, KeyRound, Loader2, CheckCircle, CheckCircle2, Eye, EyeOff, XCircle } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';

/* ─── Password strength ─────────────────────────────────────────────────── */
const PWD_RULES = [
  { id: 'len',   label: '8+ chars',  test: p => p.length >= 8 },
  { id: 'upper', label: 'Uppercase', test: p => /[A-Z]/.test(p) },
  { id: 'num',   label: 'Number',    test: p => /\d/.test(p) },
  { id: 'sym',   label: 'Symbol',    test: p => /[!@#$%^&*(),.?":{}|<>_\-]/.test(p) },
];
const STRENGTH_COLORS = ['', 'var(--danger)', 'var(--threat)', 'var(--threat)', 'var(--success)'];
const STRENGTH_LABELS = ['', 'Weak', 'Fair', 'Good', 'Strong'];

function PasswordStrength({ password }) {
  if (!password) return null;
  const score = PWD_RULES.filter(r => r.test(password)).length;
  return (
    <div className="mt-2 space-y-2">
      <div className="flex gap-1">
        {[1, 2, 3, 4].map(i => (
          <div
            key={i}
            className="h-1 flex-1 rounded-full transition-all duration-300"
            style={{ background: i <= score ? STRENGTH_COLORS[score] : 'var(--border)' }}
          />
        ))}
      </div>
      <div className="flex items-center justify-between flex-wrap gap-y-1">
        {PWD_RULES.map(r => {
          const ok = r.test(password);
          return (
            <span
              key={r.id}
              className="text-[11px] font-500 flex items-center gap-1"
              style={{ color: ok ? 'var(--success)' : 'var(--text-muted)' }}
            >
              {ok ? <CheckCircle2 className="w-3 h-3" /> : <XCircle className="w-3 h-3" />}
              {r.label}
            </span>
          );
        })}
        {score > 0 && (
          <span className="text-[11px] font-700" style={{ color: STRENGTH_COLORS[score] }}>
            {STRENGTH_LABELS[score]}
          </span>
        )}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════
   ForgotPasswordPage
══════════════════════════════════════════════════════ */
export function ForgotPasswordPage() {
  const [email,   setEmail]   = useState('');
  const [loading, setLoading] = useState(false);
  const [sent,    setSent]    = useState(false);
  const [error,   setError]   = useState('');

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setSent(true);  // Always show success (prevents email enumeration)
    } catch (err) {
      setError(err.message ?? 'Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-bg flex items-center justify-center p-4">
      <div className="w-full max-w-[420px] animate-slide-up">

        <Link
          to="/login"
          className="flex items-center gap-2 text-sm mb-6 transition-opacity hover:opacity-70"
          style={{ color: 'var(--text-muted)' }}
        >
          <ArrowLeft className="w-4 h-4" /> Back to login
        </Link>

        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-7 h-7 object-contain" />
          <span className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>
            PhishCatcher
          </span>
        </div>

        <div className="auth-card">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-5"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
            <KeyRound className="w-6 h-6" />
          </div>

          {sent ? (
            /* ── Sent state ── */
            <div className="text-center py-2">
              <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-4"
                style={{ background: 'var(--success-dim)', color: 'var(--success)' }}>
                <CheckCircle className="w-7 h-7" />
              </div>
              <h2 className="font-heading text-xl font-700 mb-2" style={{ color: 'var(--text-primary)' }}>
                Check your inbox
              </h2>
              <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
                If <span className="font-600" style={{ color: 'var(--text-secondary)' }}>{email}</span> is
                registered with PhishCatcher, a password reset link has been sent. Check your spam folder too.
              </p>
              <div className="space-y-3">
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  The link expires in 1 hour.
                </p>
                <Link to="/login" className="btn-primary inline-flex h-10 px-6 text-sm">
                  Back to sign in
                </Link>
              </div>
            </div>
          ) : (
            /* ── Form ── */
            <>
              <div className="mb-6">
                <h1 className="font-heading text-2xl font-700 mb-1" style={{ color: 'var(--text-primary)' }}>
                  Reset your password
                </h1>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                  Enter your email and we'll send you a reset link.
                </p>
              </div>

              {error && <div className="alert-error mb-5">{error}</div>}

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="form-label">Email address</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="you@company.com"
                    required
                    autoFocus
                    autoComplete="email"
                    className="input-base"
                  />
                </div>
                <button type="submit" disabled={loading} className="btn-primary w-full h-11 justify-center">
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Send reset link'}
                </button>
              </form>

              <p className="text-center text-sm mt-5" style={{ color: 'var(--text-muted)' }}>
                Remember your password?{' '}
                <Link to="/login" className="font-600 hover:underline" style={{ color: 'var(--brand)' }}>
                  Sign in
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════
   ResetPasswordPage
   URL: /reset-password?token=TOKEN
══════════════════════════════════════════════════════ */
export function ResetPasswordPage() {
  const [params]   = useSearchParams();
  const navigate   = useNavigate();
  
  // Extract token from URL parameter - handle nested URL case
  let rawToken = params.get('token') ?? '';
  
  // If token contains a full URL, extract the token from that URL
  if (rawToken.includes('http')) {
    try {
      const url = new URL(rawToken);
      const urlParams = new URLSearchParams(url.search);
      rawToken = urlParams.get('token') ?? '';
    } catch (e) {
      console.error('Failed to parse nested URL:', e);
      // Fallback: extract token after last ?token=
      const tokenMatch = rawToken.match(/token=([^&]+)/);
      rawToken = tokenMatch ? tokenMatch[1] : '';
    }
  }
  
  const token = rawToken;

  const [password,  setPassword]  = useState('');
  const [confirm,   setConfirm]   = useState('');
  const [showPwd,   setShowPwd]   = useState(false);
  const [showConf,  setShowConf]  = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState('');

  const passwordsMatch = password === confirm;
  const confirmDirty   = confirm.length > 0;

  // No token in URL → show error
  if (!token) {
    return (
      <div className="auth-bg flex items-center justify-center p-4">
        <div className="auth-card text-center max-w-[420px] w-full animate-fade-in">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
            <XCircle className="w-6 h-6" />
          </div>
          <h2 className="font-heading font-700 text-xl mb-2" style={{ color: 'var(--text-primary)' }}>
            Invalid reset link
          </h2>
          <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
            This password reset link is missing or invalid. Please request a new one.
          </p>
          <Link to="/forgot-password" className="btn-primary inline-flex h-10 px-6 text-sm">
            Request new link
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    if (!passwordsMatch) return setError('Passwords do not match.');
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      toast.success('Password reset successfully. Please sign in with your new password.');
      navigate('/login', { replace: true });
    } catch (err) {
      setError(err.message ?? 'Reset failed. The link may have expired. Please request a new one.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-bg flex items-center justify-center p-4">
      <div className="w-full max-w-[420px] animate-slide-up">

        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-7 h-7 object-contain" />
          <span className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>
            PhishCatcher
          </span>
        </div>

        <div className="auth-card">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-5"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
            <KeyRound className="w-6 h-6" />
          </div>

          <div className="mb-6">
            <h1 className="font-heading text-2xl font-700 mb-1" style={{ color: 'var(--text-primary)' }}>
              Set new password
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Choose a strong password for your account.
            </p>
          </div>

          {error && <div className="alert-error mb-5">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* New password */}
            <div>
              <label className="form-label">New password</label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoFocus
                  autoComplete="new-password"
                  className="input-base pr-10"
                />
                <button type="button" tabIndex={-1} onClick={() => setShowPwd(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <PasswordStrength password={password} />
            </div>

            {/* Confirm password */}
            <div>
              <label className="form-label">Confirm password</label>
              <div className="relative">
                <input
                  type={showConf ? 'text' : 'password'}
                  value={confirm}
                  onChange={e => setConfirm(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="new-password"
                  className="input-base pr-10"
                  style={confirmDirty ? {
                    borderColor: passwordsMatch ? 'var(--success)' : 'var(--danger)',
                    boxShadow: passwordsMatch
                      ? '0 0 0 3px rgba(16,185,129,0.12)'
                      : '0 0 0 3px rgba(239,68,68,0.12)',
                  } : {}}
                />
                <button type="button" tabIndex={-1} onClick={() => setShowConf(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
                  {showConf ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {confirmDirty && !passwordsMatch && (
                <p className="text-xs mt-1.5 font-500 flex items-center gap-1" style={{ color: 'var(--danger)' }}>
                  <XCircle className="w-3.5 h-3.5" /> Passwords do not match
                </p>
              )}
              {confirmDirty && passwordsMatch && (
                <p className="text-xs mt-1.5 font-500 flex items-center gap-1" style={{ color: 'var(--success)' }}>
                  <CheckCircle2 className="w-3.5 h-3.5" /> Passwords match
                </p>
              )}
            </div>

            <button
              type="submit"
              disabled={loading || (confirmDirty && !passwordsMatch)}
              className="btn-primary w-full h-11 justify-center"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Reset password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}