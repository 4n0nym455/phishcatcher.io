/**
 * LoginPage.jsx
 * Step 1 of the auth flow:
 *   email + password → POST /auth/login → backend sends OTP email
 *   redirect to /verify-otp with router state
 * Google OAuth via popup → oauthService.initiateGoogleOAuth()
 */

import { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, ArrowRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';
import { oauthService } from '@/lib/oauthService';

function GoogleIcon() {
  return (
    <svg className="w-4 h-4 shrink-0" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
      <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
      <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
      <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
    </svg>
  );
}

export default function LoginPage() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { loginWithTokens } = useAuth();

  // Where to redirect after successful login (supports PrivateRoute redirect)
  const from = location.state?.from?.pathname ?? '/dashboard';

  const [email,         setEmail]         = useState('');
  const [password,      setPassword]      = useState('');
  const [showPwd,       setShowPwd]       = useState(false);
  const [loading,       setLoading]       = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error,         setError]         = useState('');

  /* ── Email + password submit ── */
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await authApi.login(email, password);

      // Backend sends OTP to email. Navigate to verify-otp with context.
      navigate('/verify-otp', {
        state: {
          email,
          mfaRequired:     data.mfa_required      ?? false,
          mfaSessionToken: data.mfa_session_token ?? null,
          from,
        },
      });
    } catch (err) {
      setError(err.message ?? 'Invalid email or password.');
    } finally {
      setLoading(false);
    }
  };

  /* ── Google OAuth (popup flow) ── */
  const handleGoogle = async () => {
    setGoogleLoading(true);
    setError('');
    try {
      const result = await oauthService.initiateGoogleOAuth();

      if (result.activation_required) {
        // New Google user — needs account activation
        navigate('/activation-pending', {
          state: { email: result.email, full_name: result.full_name },
        });
        return;
      }

      if (result.requiresMFA) {
        navigate('/mfa-verification', {
          state: { mfaSessionToken: result.mfa_session_token, user: result.user, from },
        });
        return;
      }

      if (result.success && result.access_token) {
        await loginWithTokens(result);
        toast.success('Signed in with Google');
        navigate(from, { replace: true });
        return;
      }

      throw new Error(result.message ?? 'Google authentication failed');
    } catch (err) {
      // Don't show error if user just cancelled the popup
      if (err.message !== 'Sign-in cancelled') {
        setError(err.message ?? 'Google sign-in failed');
      }
    } finally {
      setGoogleLoading(false);
    }
  };

  const busy = loading || googleLoading;

  return (
    <div className="auth-bg flex items-center justify-center p-4 min-h-screen">
      <div className="w-full max-w-[420px] animate-slide-up">

        {/* Logo */}
        <Link to="/" className="flex items-center justify-center gap-2.5 mb-8">
          <img
            src="/phishcatcher.png"
            alt="PhishCatcher"
            className="w-9 h-9 object-contain"
          />
          <span className="font-heading font-700 text-xl" style={{ color: 'var(--text-primary)' }}>
            PhishCatcher
          </span>
        </Link>

        <div className="auth-card">
          {/* Heading */}
          <div className="mb-6">
            <h1 className="font-heading text-2xl font-700 mb-1" style={{ color: 'var(--text-primary)' }}>
              Welcome back
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Sign in to your PhishCatcher account
            </p>
          </div>

          {/* Error banner */}
          {error && <div className="alert-error mb-5">{error}</div>}

          {/* Google OAuth button */}
          <button
            type="button"
            onClick={handleGoogle}
            disabled={busy}
            className="w-full btn-ghost mb-5 h-11 justify-center gap-2.5 text-sm"
          >
            {googleLoading
              ? <Loader2 className="w-4 h-4 animate-spin" />
              : <GoogleIcon />
            }
            Continue with Google
          </button>

          {/* OR divider */}
          <div className="divider mb-5">or</div>

          {/* Email + password form */}
          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Email */}
            <div>
              <label className="form-label">Email address</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                autoComplete="email"
                autoFocus
                disabled={busy}
                className="input-base"
              />
            </div>

            {/* Password */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="form-label mb-0">Password</label>
                <Link
                  to="/forgot-password"
                  className="text-xs font-500 hover:underline"
                  style={{ color: 'var(--brand)' }}
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  autoComplete="current-password"
                  disabled={busy}
                  className="input-base pr-10"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPwd(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 transition-opacity hover:opacity-70"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {/* Submit */}
            <button
              type="submit"
              disabled={busy}
              className="btn-primary w-full h-11 justify-center"
            >
              {loading
                ? <Loader2 className="w-4 h-4 animate-spin" />
                : <>Sign in <ArrowRight className="w-4 h-4" /></>
              }
            </button>
          </form>

          {/* Register link */}
          <p className="text-center text-sm mt-5" style={{ color: 'var(--text-muted)' }}>
            Don't have an account?{' '}
            <Link to="/register" className="font-600 hover:underline" style={{ color: 'var(--brand)' }}>
              Create one
            </Link>
          </p>
        </div>

        {/* Security footnote */}
        <p
          className="flex items-center justify-center gap-2 mt-6 text-xs"
          style={{ color: 'var(--text-muted)' }}
        >
          <img
            src="/phishcatcher-logo.png"
            alt="PhishCatcher"
            className="w-4 h-4"
            style={{ color: 'var(--brand)' }}
          />
          Protected by enterprise-grade phishing detection
        </p>
      </div>
    </div>
  );
}