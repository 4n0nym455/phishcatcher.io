import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { storeTokens, getTokens } from '../lib/api';

/**
 * ActivateAccountPage
 *
 * Fixed:
 *  - Calls onLogin() after storing tokens so App.jsx updates isAuthenticated
 *    and fetches fresh user data via authApi.getMe() — same path as login/OTP.
 *  - Uses storeTokens() from lib/api (not raw localStorage) to match getTokens()
 *    used in App.jsx's checkAuth().
 *  - account_status is now 'active' from backend so no gate blocks the dashboard.
 */
export default function ActivateAccountPage({ onLogin }) {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const email = searchParams.get('email') || '';
  const token = searchParams.get('token') || '';

  const [code, setCode] = useState('');
  const [termsAccepted, setTermsAccepted] = useState(false);
  const [privacyAccepted, setPrivacyAccepted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [resendLoading, setResendLoading] = useState(false);
  const [resendMessage, setResendMessage] = useState('');

  // Already authenticated — skip to dashboard
  useEffect(() => {
    const { accessToken } = getTokens();
    if (accessToken) {
      navigate('/dashboard', { replace: true });
    }
  }, [navigate]);

  const handleActivation = async (e) => {
    e.preventDefault();
    setError('');

    if (!code.trim()) {
      setError('Please enter the activation code from your email.');
      return;
    }
    if (!termsAccepted || !privacyAccepted) {
      setError('You must accept both the Terms & Conditions and Privacy Policy.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/auth/activate/complete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          token,
          email,
          code: code.trim(),
          terms_accepted: termsAccepted,
          privacy_accepted: privacyAccepted,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        setError(data.detail || 'Activation failed. Please check your code and try again.');
        return;
      }

      if (data.already_activated) {
        navigate('/login?message=already_activated', { replace: true });
        return;
      }

      if (data.access_token) {
        // Store tokens using the same helper getTokens() reads from
        storeTokens(data.access_token, data.refresh_token);

        // Store user data for immediate display
        if (data.user) {
          const role = data.user.role === 'admin' ? 'admin' : 'user';
          localStorage.setItem('phishcatcher_role', role);
          localStorage.setItem('phishcatcher_email', data.user.email);
          localStorage.setItem('phishcatcher_name', data.user.full_name || '');
        }

        // Fire the auth-success event so App.jsx's listener picks it up,
        // then call onLogin() which sets isAuthenticated + fetches fresh user data
        window.dispatchEvent(new Event('auth-success'));
        if (onLogin) await onLogin();

        navigate('/dashboard', { replace: true });
      } else {
        // Unexpected — backend succeeded but no token; send to login
        navigate('/login?message=activation_complete', { replace: true });
      }
    } catch (err) {
      setError('Network error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setResendLoading(true);
    setResendMessage('');
    setError('');
    try {
      const res = await fetch(`${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/auth/activate/resend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Failed to resend activation email.');
      } else {
        setResendMessage('A new activation email has been sent. Please check your inbox.');
      }
    } catch {
      setError('Network error. Please try again.');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-900 px-4">
      <div className="max-w-md w-full bg-slate-800 rounded-2xl shadow-lg p-8 border border-slate-700">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-bold text-white">Activate your account</h1>
          <p className="text-sm text-slate-400 mt-1">
            Enter the 6-digit code sent to <strong className="text-slate-200">{email}</strong>
          </p>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-900/40 border border-red-700 rounded-lg text-red-300 text-sm">
            {error}
          </div>
        )}
        {resendMessage && (
          <div className="mb-4 p-3 bg-green-900/40 border border-green-700 rounded-lg text-green-300 text-sm">
            {resendMessage}
          </div>
        )}

        <form onSubmit={handleActivation} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Activation Code
            </label>
            <input
              type="text"
              value={code}
              onChange={(e) => setCode(e.target.value)}
              placeholder="Enter 6-digit code"
              maxLength={6}
              className="w-full bg-slate-700 border border-slate-600 rounded-lg px-4 py-2 text-sm text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
          </div>

          <div className="space-y-2">
            <label className="flex items-start gap-2 text-sm text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={termsAccepted}
                onChange={(e) => setTermsAccepted(e.target.checked)}
                className="mt-0.5 accent-blue-500"
              />
              <span>
                I agree to the{' '}
                <a href="/terms" className="text-blue-400 underline" target="_blank" rel="noreferrer">
                  Terms &amp; Conditions
                </a>
              </span>
            </label>

            <label className="flex items-start gap-2 text-sm text-slate-400 cursor-pointer">
              <input
                type="checkbox"
                checked={privacyAccepted}
                onChange={(e) => setPrivacyAccepted(e.target.checked)}
                className="mt-0.5 accent-blue-500"
              />
              <span>
                I agree to the{' '}
                <a href="/privacy" className="text-blue-400 underline" target="_blank" rel="noreferrer">
                  Privacy Policy
                </a>
              </span>
            </label>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition"
          >
            {loading ? 'Activating…' : 'Activate Account'}
          </button>
        </form>

        <div className="mt-4 text-center">
          <p className="text-sm text-slate-400">
            Didn't receive a code?{' '}
            <button
              onClick={handleResend}
              disabled={resendLoading}
              className="text-blue-400 hover:underline disabled:opacity-50"
            >
              {resendLoading ? 'Sending…' : 'Resend email'}
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}