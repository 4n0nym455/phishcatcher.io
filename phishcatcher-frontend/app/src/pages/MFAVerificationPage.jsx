/**
 * MFAVerificationPage.jsx
 * Step 3 of login: TOTP code or backup code verification.
 * Receives: { mfaSessionToken, user, from } via router state.
 */

import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { ArrowLeft, ShieldCheck, Loader2, Key } from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

export default function MFAVerificationPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { loginWithTokens } = useAuth();

  const {
    mfaSessionToken,
    user,
    from = '/dashboard',
  } = location.state ?? {};

  const [code,       setCode]      = useState('');
  const [backupCode, setBackupCode]= useState('');
  const [useBackup,  setUseBackup] = useState(false);
  const [loading,    setLoading]   = useState(false);
  const [error,      setError]     = useState('');

  // Guard direct navigation
  useEffect(() => {
    if (!mfaSessionToken) navigate('/login', { replace: true });
  }, [mfaSessionToken, navigate]);

  const switchMode = () => {
    setUseBackup(v => !v);
    setError('');
    setCode('');
    setBackupCode('');
  };

  const handleSubmit = async e => {
    e.preventDefault();
    setError('');

    if (useBackup) {
      if (!backupCode.trim()) return setError('Please enter a backup code.');
    } else {
      if (code.length !== 6) return setError('Please enter your 6-digit authenticator code.');
    }

    setLoading(true);
    try {
      let data;
      if (useBackup) {
        data = await authApi.verifyBackupCode(backupCode.trim());
      } else {
        data = await authApi.verifyMFA(mfaSessionToken, code);
      }
      await loginWithTokens(data);
      toast.success('Signed in successfully');
      navigate(from, { replace: true });
    } catch (err) {
      setError(err.message ?? 'Invalid code. Please try again.');
      setCode('');
      setBackupCode('');
    } finally {
      setLoading(false);
    }
  };

  if (!mfaSessionToken) return null;

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
            <ShieldCheck className="w-6 h-6" />
          </div>

          <div className="mb-6">
            <h1 className="font-heading text-2xl font-700 mb-1" style={{ color: 'var(--text-primary)' }}>
              Multi-Factor Auth
            </h1>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              {useBackup
                ? 'Enter one of your saved backup codes'
                : 'Enter the 6-digit code from your authenticator app'
              }
            </p>
          </div>

          {/* User info strip */}
          {user && (
            <div
              className="flex items-center gap-3 p-3 rounded-xl mb-5"
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}
            >
              <div className="w-8 h-8 rounded-full flex items-center justify-center text-sm font-700 shrink-0"
                style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
                {(user.full_name || user.email || 'U')[0].toUpperCase()}
              </div>
              <div>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>Signing in as</p>
                <p className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>{user.email}</p>
              </div>
            </div>
          )}

          {error && <div className="alert-error mb-5">{error}</div>}

          <form onSubmit={handleSubmit} className="space-y-4">
            {useBackup ? (
              <div>
                <label className="form-label">Backup code</label>
                <input
                  type="text"
                  value={backupCode}
                  onChange={e => setBackupCode(e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 8))}
                  placeholder="XXXXXXXX"
                  maxLength={8}
                  autoFocus
                  autoComplete="off"
                  className="input-base font-mono tracking-widest text-center text-lg"
                />
              </div>
            ) : (
              <div>
                <label className="form-label">Authentication code</label>
                <input
                  type="text"
                  inputMode="numeric"
                  value={code}
                  onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="000 000"
                  maxLength={6}
                  autoFocus
                  autoComplete="one-time-code"
                  className="input-base font-mono tracking-[0.4em] text-center text-xl"
                  style={code.length === 6 ? { borderColor: 'var(--brand)' } : {}}
                />
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full h-11 justify-center"
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Verify'}
            </button>
          </form>

          <div className="mt-5 text-center">
            <button
              onClick={switchMode}
              className="text-sm font-500 hover:underline inline-flex items-center gap-1.5"
              style={{ color: 'var(--brand)' }}
            >
              <Key className="w-3.5 h-3.5" />
              {useBackup ? 'Use authenticator app instead' : 'Use a backup code instead'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}