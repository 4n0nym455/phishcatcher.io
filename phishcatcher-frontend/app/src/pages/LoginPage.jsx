/**
 * LoginPage — modernized
 *
 * Clean auth card design using CSS variables for full light/dark support.
 * No hard-coded colors, no slate-* overrides.
 */

import { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Eye, EyeOff, Shield, Chrome, ArrowRight, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';
import { useAuth }  from '@/context/AuthContext';
import { oauthService } from '@/lib/oauthService';

export default function LoginPage() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { loginWithTokens } = useAuth();
  const from = location.state?.from?.pathname ?? '/dashboard';

  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [showPwd,  setShowPwd]  = useState(false);
  const [loading,  setLoading]  = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [error,    setError]    = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = await authApi.login(email, password);
      if (data.activation_required) {
        navigate('/activation-pending', { state: { email } });
        return;
      }
      navigate('/verify-otp', {
        state: {
          email,
          mfaRequired:     data.mfa_required,
          mfaSessionToken: data.mfa_session_token,
          from,
        },
      });
    } catch (err) {
      setError(err.message ?? 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogle = async () => {
    setGoogleLoading(true);
    setError('');
    try {
      const result = await oauthService.initiateGoogleOAuth();
      if (result.activation_required) {
        navigate('/activation-pending', { state: { email: result.email } });
      } else if (result.requiresMFA) {
        navigate('/mfa-verification', {
          state: { mfaSessionToken: result.mfa_session_token, user: result.user, from },
        });
      } else if (result.success) {
        await loginWithTokens(result);
        toast.success('Signed in with Google');
        navigate(from, { replace: true });
      }
    } catch (err) {
      if (err.message !== 'Sign-in cancelled') setError(err.message ?? 'Google sign-in failed');
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <div className="auth-bg flex items-center justify-center p-4">
      <div className="w-full max-w-[420px] animate-slide-up">

        {/* Logo mark */}
        <div className="flex justify-center mb-8">
          <div
            className="w-14 h-14 rounded-2xl flex items-center justify-center"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)', boxShadow: 'var(--shadow-glow)' }}
          >
            <Shield className="w-7 h-7" />
          </div>
        </div>

        <div className="auth-card">
          <div className="mb-6">
            <h1 className="font-heading text-2xl font-700 mb-1" style={{ color: 'var(--text-primary)' }}>
              Welcome back
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              Sign in to your PhishCatcher account
            </p>
          </div>

          {error && <div className="alert-error mb-4">{error}</div>}

          {/* Google */}
          <button
            type="button"
            onClick={handleGoogle}
            disabled={googleLoading || loading}
            className="w-full btn-ghost mb-4 justify-center h-11"
          >
            {googleLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
            )}
            Continue with Google
          </button>

          <div className="divider">or</div>

          {/* Email + password form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="form-label">Email address</label>
              <input
                type="email"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@company.com"
                required
                autoComplete="email"
                className="input-base"
              />
            </div>

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
                  className="input-base pr-10"
                />
                <button
                  type="button"
                  tabIndex={-1}
                  onClick={() => setShowPwd(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || googleLoading}
              className="btn-primary w-full h-11 justify-center"
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>Sign in <ArrowRight className="w-4 h-4" /></>
              )}
            </button>
          </form>

          <p className="text-center text-sm mt-5" style={{ color: 'var(--text-muted)' }}>
            Don't have an account?{' '}
            <Link to="/register" className="font-600 hover:underline" style={{ color: 'var(--brand)' }}>
              Create one
            </Link>
          </p>
        </div>

        <p className="text-center text-xs mt-5" style={{ color: 'var(--text-muted)' }}>
          Protected by enterprise-grade phishing detection
        </p>
      </div>
    </div>
  );
}