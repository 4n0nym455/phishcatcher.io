/**
 * ActivationPages.jsx
 * Exports:
 *   ActivateAccountPage   — /activate?token=TOKEN&email=EMAIL
 *   ActivationPendingPage — /activation-pending (router state: { email })
 */

import { useState, useEffect } from 'react';
import { Link, useNavigate, useSearchParams, useLocation } from 'react-router-dom';
import {
  Mail, CheckCircle, RefreshCw, Loader2,
  ArrowRight, XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

/* ══════════════════════════════════════════════════════
   ActivateAccountPage
   /activate?token=TOKEN&email=EMAIL
   Enter 6-digit code + accept T&C → POST /activate/complete
══════════════════════════════════════════════════════ */
export function ActivateAccountPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const { loginWithTokens, isAuthenticated } = useAuth();

  const email = params.get('email') ?? '';
  const token = params.get('token') ?? '';

  const [code,      setCode]      = useState('');
  const [terms,     setTerms]     = useState(false);
  const [privacy,   setPrivacy]   = useState(false);
  const [loading,   setLoading]   = useState(false);
  const [resending, setResending] = useState(false);
  const [error,     setError]     = useState('');
  const [success,   setSuccess]   = useState('');

  // Already logged in → skip
  useEffect(() => {
    if (isAuthenticated) navigate('/dashboard', { replace: true });
  }, [isAuthenticated, navigate]);

  // Missing params
  if (!token || !email) {
    return (
      <div className="auth-bg flex items-center justify-center p-4">
        <div className="auth-card text-center max-w-[420px] w-full animate-fade-in">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mx-auto mb-4"
            style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
            <XCircle className="w-6 h-6" />
          </div>
          <h2 className="font-heading font-700 text-xl mb-2" style={{ color: 'var(--text-primary)' }}>
            Invalid activation link
          </h2>
          <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
            This activation link is missing required parameters. Please use the link from your email, or request a new one.
          </p>
          <Link to="/login" className="btn-ghost inline-flex h-10 px-6 text-sm">
            Back to sign in
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (!terms || !privacy)
      return setError('You must accept both the Terms of Service and Privacy Policy to activate your account.');
    if (!code.trim() || code.trim().length !== 6)
      return setError('Please enter the 6-digit activation code from your email.');

    setLoading(true);
    try {
      const data = await authApi.completeActivation({
        token,
        email,
        code:             code.trim(),
        terms_accepted:   true,
        privacy_accepted: true,
      });

      if (data.already_activated) {
        navigate('/login?message=already_activated', { replace: true });
        return;
      }

      await loginWithTokens(data);
      toast.success('Account activated! Welcome to PhishCatcher.');
      navigate('/dashboard', { replace: true });
    } catch (err) {
      setError(err.message ?? 'Activation failed. Please check your code and try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    setError('');
    setSuccess('');
    try {
      await authApi.resendActivation(email);
      setSuccess('A new activation email has been sent. Please check your inbox.');
    } catch (err) {
      setError(err.message ?? 'Failed to resend. Please try again.');
    } finally {
      setResending(false);
    }
  };

  // Custom checkbox
  const CheckBox = ({ checked, onToggle, id, children }) => (
    <label htmlFor={id} className="flex items-start gap-3 cursor-pointer">
      <div
        id={id}
        role="checkbox"
        aria-checked={checked}
        tabIndex={0}
        onClick={() => onToggle(!checked)}
        onKeyDown={e => (e.key === ' ' || e.key === 'Enter') && onToggle(!checked)}
        className="w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 mt-0.5 transition-all cursor-pointer"
        style={{ borderColor: checked ? 'var(--brand)' : 'var(--border-strong)', background: checked ? 'var(--brand)' : 'transparent' }}
      >
        {checked && (
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="white" strokeWidth={3}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        )}
      </div>
      <span className="text-sm leading-snug" style={{ color: 'var(--text-secondary)' }}>{children}</span>
    </label>
  );

  return (
    <div className="auth-bg flex items-center justify-center p-4 py-10">
      <div className="w-full max-w-[440px] animate-slide-up">

        {/* Logo */}
        <Link to="/" className="flex items-center justify-center gap-2.5 mb-6">
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-7 h-7 object-contain" />
          <span className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>
            PhishCatcher
          </span>
        </Link>

        <div className="auth-card">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-5"
            style={{ background: 'var(--success-dim)', color: 'var(--success)' }}>
            <CheckCircle className="w-6 h-6" />
          </div>

          <div className="mb-6">
            <h1 className="font-heading text-2xl font-700 mb-1" style={{ color: 'var(--text-primary)' }}>
              Activate your account
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Enter the 6-digit code sent to{' '}
              <span className="font-600" style={{ color: 'var(--text-secondary)' }}>{email}</span>
            </p>
          </div>

          {error   && <div className="alert-error mb-4">{error}</div>}
          {success && <div className="alert-success mb-4">{success}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            {/* Code input */}
            <div>
              <label className="form-label">Activation code</label>
              <input
                type="text"
                inputMode="numeric"
                value={code}
                onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="123456"
                maxLength={6}
                required
                autoFocus
                autoComplete="one-time-code"
                className="input-base font-mono tracking-[0.4em] text-center text-xl"
                style={code.length === 6 ? { borderColor: 'var(--success)' } : {}}
              />
              <p className="text-xs mt-1.5" style={{ color: 'var(--text-muted)' }}>
                The code expires 10 minutes after sending.
              </p>
            </div>

            {/* Legal agreements — REQUIRED */}
            <div className="rounded-xl p-4 space-y-3"
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
              <p className="text-xs font-700 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                Required agreements
              </p>

              <CheckBox id="act-terms" checked={terms} onToggle={setTerms}>
                I agree to the{' '}
                <Link to="/terms" target="_blank" rel="noreferrer"
                  className="font-600 underline decoration-dotted hover:opacity-80"
                  style={{ color: 'var(--brand)' }}
                  onClick={e => e.stopPropagation()}>
                  Terms of Service
                </Link>
              </CheckBox>

              <CheckBox id="act-privacy" checked={privacy} onToggle={setPrivacy}>
                I agree to the{' '}
                <Link to="/privacy" target="_blank" rel="noreferrer"
                  className="font-600 underline decoration-dotted hover:opacity-80"
                  style={{ color: 'var(--brand)' }}
                  onClick={e => e.stopPropagation()}>
                  Privacy Policy
                </Link>
              </CheckBox>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full h-11 justify-center"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Activate account'}
            </button>
          </form>

          <div className="mt-5 text-center">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Didn't receive a code?{' '}
              <button
                onClick={handleResend}
                disabled={resending}
                className="font-600 hover:underline inline-flex items-center gap-1 disabled:opacity-50"
                style={{ color: 'var(--brand)' }}
              >
                {resending && <RefreshCw className="w-3 h-3 animate-spin" />}
                Resend email
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════
   ActivationPendingPage
   /activation-pending — shown after registration or Google OAuth new user
   Router state: { email }
══════════════════════════════════════════════════════ */
export function ActivationPendingPage() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const email     = location.state?.email ?? '';

  const [resending, setResending] = useState(false);
  const [resent,    setResent]    = useState(false);
  const [error,     setError]     = useState('');

  const handleResend = async () => {
    if (!email) return;
    setResending(true);
    setError('');
    try {
      await authApi.resendActivation(email);
      setResent(true);
      toast.success('Activation email resent!');
    } catch (err) {
      setError(err.message ?? 'Failed to resend email.');
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="auth-bg flex items-center justify-center p-4">
      <div className="w-full max-w-[440px] animate-slide-up">

        {/* Logo */}
        <Link to="/" className="flex items-center justify-center gap-2.5 mb-6">
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-7 h-7 object-contain" />
          <span className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>
            PhishCatcher
          </span>
        </Link>

        <div className="auth-card text-center">
          <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
            <Mail className="w-8 h-8" />
          </div>

          <h1 className="font-heading text-2xl font-700 mb-2" style={{ color: 'var(--text-primary)' }}>
            Check your inbox
          </h1>
          <p className="text-sm mb-6" style={{ color: 'var(--text-muted)' }}>
            We sent an activation email{email && (
              <> to{' '}
                <span className="font-600" style={{ color: 'var(--text-secondary)' }}>{email}</span>
              </>
            )}. Click the link and enter your activation code to get started.
          </p>

          {/* Steps */}
          <div className="text-left rounded-xl p-4 mb-6 space-y-3"
            style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
            <p className="text-xs font-700 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              Next steps
            </p>
            {[
              'Check your inbox (and spam folder)',
              'Click the activation link in the email',
              'Enter the 6-digit code on the activation page',
              'Accept the Terms & Privacy Policy',
            ].map((step, i) => (
              <div key={i} className="flex items-start gap-2.5 text-sm" style={{ color: 'var(--text-secondary)' }}>
                <span className="w-5 h-5 rounded-full flex items-center justify-center text-xs font-700 shrink-0 mt-0.5"
                  style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
                  {i + 1}
                </span>
                {step}
              </div>
            ))}
          </div>

          {error && <div className="alert-error mb-4 text-left">{error}</div>}

          <div className="space-y-3">
            {resent ? (
              <p className="text-sm font-600 flex items-center justify-center gap-2"
                style={{ color: 'var(--success)' }}>
                <CheckCircle className="w-4 h-4" /> Email resent successfully
              </p>
            ) : (
              <button
                onClick={handleResend}
                disabled={resending || !email}
                className="btn-ghost w-full h-10 justify-center text-sm"
              >
                {resending ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
                Resend activation email
              </button>
            )}

            <Link to="/login" className="btn-primary w-full h-10 justify-center text-sm inline-flex">
              Back to sign in <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}