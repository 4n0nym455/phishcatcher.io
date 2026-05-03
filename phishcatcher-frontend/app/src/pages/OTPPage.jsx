/**
 * OTPPage.jsx
 * Step 2 of email+password login flow.
 * Receives: { email, mfaRequired, mfaSessionToken, from } via router state.
 * 6-character alphanumeric OTP input with auto-advance, paste, backspace navigation, resend countdown.
 */

import { useState, useRef, useEffect } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { ArrowLeft, Mail, RefreshCw, Loader2, ArrowRight } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';
import { useAuth } from '@/stores/authStore';

const OTP_LEN    = 6;
const RESEND_SEC = 60;

export default function OTPPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { loginWithTokens } = useAuth();

  const {
    email           = '',
    from            = '/dashboard',
  } = location.state ?? {};

  const [digits,    setDigits]    = useState(Array(OTP_LEN).fill(''));
  const [loading,   setLoading]   = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [error,     setError]     = useState('');
  const inputRefs = useRef([]);

  // Guard: no email → redirect to login
  useEffect(() => {
    if (!email) navigate('/login', { replace: true });
  }, [email, navigate]);

  // Countdown timer
  useEffect(() => {
    if (countdown <= 0) return;
    const id = setTimeout(() => setCountdown(c => c - 1), 1000);
    return () => clearTimeout(id);
  }, [countdown]);

  // Auto-focus first box
  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  const otp = digits.join('');

  /* ─── Input handlers ─────────────────────────────────────────────────── */
  const focusAt = idx => inputRefs.current[idx]?.focus();

  const handleChange = (idx, val) => {
    const v = val.replace(/[^a-zA-Z0-9]/g, '');
    if (!v && val) return; // reject non-alphanumeric
    const next = [...digits];
    next[idx] = v.slice(-1);
    setDigits(next);
    if (v && idx < OTP_LEN - 1) focusAt(idx + 1);
  };

  const handleKeyDown = (idx, e) => {
    if (e.key === 'Backspace') {
      if (digits[idx]) {
        const next = [...digits]; next[idx] = ''; setDigits(next);
      } else if (idx > 0) {
        focusAt(idx - 1);
      }
    } else if (e.key === 'ArrowLeft'  && idx > 0)          focusAt(idx - 1);
    else if   (e.key === 'ArrowRight' && idx < OTP_LEN - 1) focusAt(idx + 1);
  };

  const handlePaste = e => {
    e.preventDefault();
    const text = e.clipboardData.getData('text').replace(/[^a-zA-Z0-9]/g, '').slice(0, OTP_LEN);
    if (!text) return;
    const next = Array(OTP_LEN).fill('');
    text.split('').forEach((c, i) => { next[i] = c; });
    setDigits(next);
    focusAt(Math.min(text.length, OTP_LEN - 1));
    // Auto-submit if fully filled
    if (text.length === OTP_LEN) submit(text);
  };

  /* ─── Submit ─────────────────────────────────────────────────────────── */
  const submit = async code => {
    setError('');
    setLoading(true);
    try {
      const data = await authApi.verifyOTP(email, code);
      if (data.mfa_required) {
        navigate('/mfa-verification', {
          state: { mfaSessionToken: data.mfa_session_token, user: data.user, from },
        });
      } else {
        await loginWithTokens(data);
        toast.success('Signed in successfully');
        navigate(from, { replace: true });
      }
    } catch (err) {
      setError(err.message ?? 'Invalid code. Please try again.');
      setDigits(Array(OTP_LEN).fill(''));
      focusAt(0);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = e => {
    e.preventDefault();
    if (otp.length !== OTP_LEN) return setError('Please enter all 6 characters.');
    submit(otp);
  };

  /* ─── Resend ─────────────────────────────────────────────────────────── */
  const handleResend = async () => {
    setResending(true);
    setError('');
    try {
      await authApi.resendOTP(email);
      toast.success('New code sent to your email');
      setCountdown(RESEND_SEC);
      setDigits(Array(OTP_LEN).fill(''));
      focusAt(0);
    } catch (err) {
      if (err.message?.includes('No active login session')) {
        toast.error('Session expired. Please log in again.');
        navigate('/login', { replace: true });
      } else {
        setError(err.message ?? 'Failed to resend code');
      }
    } finally {
      setResending(false);
    }
  };

  if (!email) return null;

  return (
    <div className="auth-bg flex items-center justify-center p-4">
      <div className="w-full max-w-[420px] animate-slide-up">

        {/* Back */}
        <button
          onClick={() => navigate('/login')}
          className="flex items-center gap-2 text-sm mb-6 transition-opacity hover:opacity-70"
          style={{ color: 'var(--text-muted)' }}
        >
          <ArrowLeft className="w-4 h-4" /> Back to login
        </button>

        {/* Logo */}
        <div className="flex items-center justify-center gap-2.5 mb-6">
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-7 h-7 object-contain" />
          <span className="font-heading font-700 text-lg" style={{ color: 'var(--text-primary)' }}>
            PhishCatcher
          </span>
        </div>

        <div className="auth-card">
          {/* Icon */}
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center mb-5"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
            <Mail className="w-6 h-6" />
          </div>

          <div className="mb-6">
            <h1 className="font-heading text-2xl font-700 mb-1" style={{ color: 'var(--text-primary)' }}>
              Check your email
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              We sent a 6-character code to{' '}
              <span className="font-600" style={{ color: 'var(--text-secondary)' }}>{email}</span>
            </p>
          </div>

          {error && <div className="alert-error mb-5">{error}</div>}

          <form onSubmit={handleSubmit}>
            {/* OTP boxes */}
            <div className="flex gap-2 justify-center mb-6" onPaste={handlePaste}>
              {digits.map((d, i) => (
                <input
                  key={i}
                  ref={el => inputRefs.current[i] = el}
                  type="text"
                  inputMode="text"
                  maxLength={1}
                  value={d}
                  onChange={e => handleChange(i, e.target.value)}
                  onKeyDown={e => handleKeyDown(i, e)}
                  disabled={loading}
                  className="otp-digit"
                  style={d ? { borderColor: 'var(--brand)', background: 'var(--brand-dim)' } : {}}
                />
              ))}
            </div>

            <button
              type="submit"
              disabled={loading || otp.length !== OTP_LEN}
              className="btn-primary w-full h-11 justify-center"
            >
              {loading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <>Verify code <ArrowRight className="w-4 h-4" /></>
              }
            </button>
          </form>

          {/* Resend */}
          <div className="mt-5 text-center">
            {countdown > 0 ? (
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Resend available in{' '}
                <span className="font-600" style={{ color: 'var(--text-secondary)' }}>{countdown}s</span>
              </p>
            ) : (
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
                Didn't receive it?{' '}
                <button
                  onClick={handleResend}
                  disabled={resending}
                  className="font-600 hover:underline inline-flex items-center gap-1 disabled:opacity-50"
                  style={{ color: 'var(--brand)' }}
                >
                  {resending && <RefreshCw className="w-3 h-3 animate-spin" />}
                  Resend code
                </button>
              </p>
            )}
          </div>

          <p className="text-center text-xs mt-4" style={{ color: 'var(--text-muted)' }}>
            Code expires in 10 minutes
          </p>
        </div>
      </div>
    </div>
  );
}