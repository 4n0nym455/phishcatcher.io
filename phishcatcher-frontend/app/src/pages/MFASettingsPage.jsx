/**
 * MFASettings.jsx
 * Full MFA setup (QR + secret + backup codes + verify), disable, and status display.
 */

import { useState, useEffect } from 'react';
import {
  Shield, ShieldCheck, ShieldOff, Key,
  Eye, EyeOff, Loader2, Copy, CheckCircle,
  AlertTriangle, QrCode,
} from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

export default function MFASettingsPage() {
  const { refreshUser } = useAuth();

  const [status,       setStatus]      = useState(null);
  const [loading,      setLoading]     = useState(true);
  const [setupData,    setSetupData]   = useState(null);  // from POST /mfa/setup
  const [setupCode,    setSetupCode]   = useState('');
  const [setupLoading, setSetupLoading]= useState(false);
  const [copiedCodes,  setCopied]      = useState(false);
  const [showDisable,  setShowDisable] = useState(false);
  const [disableCode,  setDisableCode] = useState('');
  const [disablePwd,   setDisablePwd]  = useState('');
  const [showPwd,      setShowPwd]     = useState(false);
  const [disableLoading, setDisableLoading] = useState(false);

  useEffect(() => {
    const fetchMfaStatus = () => {
      authApi.getMfaStatus()
        .then(setStatus)
        .catch(() => {})
        .finally(() => setLoading(false));
    };

    // Initial fetch
    fetchMfaStatus();

    // Refresh when page gains focus (navigation back, tab switch, etc.)
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && !loading) {
        fetchMfaStatus();
      }
    };

    // Also refresh when window gains focus
    const handleFocus = () => {
      if (!loading) {
        fetchMfaStatus();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
    };
  }, [loading]);

  /* ── Initiate setup ── */
  const handleSetup = async () => {
    setSetupLoading(true);
    try {
      const data = await authApi.setupMfa({});
      setSetupData(data);
      setSetupCode('');
    } catch (err) {
      toast.error(err.message ?? 'Failed to start MFA setup');
    } finally {
      setSetupLoading(false);
    }
  };

  /* ── Verify setup (enables MFA) ── */
  const handleVerifySetup = async e => {
    e.preventDefault();
    if (setupCode.length !== 6) return toast.error('Enter the 6-digit code from your authenticator');
    setSetupLoading(true);
    try {
      await authApi.verifyMfaSetup({ mfa_session_token: setupData.mfa_session_token, code: setupCode });
      toast.success('MFA enabled successfully!');
      setSetupData(null);
      setSetupCode('');
      setStatus({ enabled: true, setup_completed: true, has_backup_codes: true });
      await refreshUser();
    } catch (err) {
      console.error('MFA verification error:', err);
      toast.error(err.message ?? 'Invalid code. Try again.');
      setSetupCode('');
    } finally {
      setSetupLoading(false);
    }
  };

  /* ── Disable ── */
  const handleDisable = async e => {
    e.preventDefault();
    if (disableCode.length !== 6) return toast.error('Enter your 6-digit authenticator code');
    setDisableLoading(true);
    try {
      await authApi.disableMfa({ token: disableCode, password: disablePwd });
      toast.success('MFA disabled');
      setShowDisable(false);
      setDisableCode('');
      setDisablePwd('');
      setStatus({ enabled: false, setup_completed: false, has_backup_codes: false });
      await refreshUser();
    } catch (err) {
      toast.error(err.message ?? 'Failed to disable MFA');
    } finally {
      setDisableLoading(false);
    }
  };

  const copyBackupCodes = () => {
    if (!setupData?.backup_codes?.length) return;
    navigator.clipboard.writeText(setupData.backup_codes.join('\n'));
    setCopied(true);
    toast.success('Backup codes copied!');
    setTimeout(() => setCopied(false), 3000);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--brand)' }} />
      </div>
    );
  }

  const enabled = status?.enabled ?? false;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Two-Factor Authentication</h1>
        <p className="page-subtitle">Protect your account with TOTP-based 2FA</p>
      </div>

      {/* ── Status card ── */}
      <div className="card p-6">
        <div className="flex items-center gap-4 mb-5">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
            style={{ background: enabled ? 'var(--success-dim)' : 'var(--bg-elevated)', color: enabled ? 'var(--success)' : 'var(--text-muted)' }}>
            {enabled ? <ShieldCheck className="w-6 h-6" /> : <Shield className="w-6 h-6" />}
          </div>
          <div className="flex-1">
            <p className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
              MFA is {enabled ? 'enabled' : 'not enabled'}
            </p>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {enabled
                ? 'Your account requires both password and authenticator code to sign in.'
                : 'Enable MFA to add a second layer of protection to your account.'}
            </p>
          </div>
          {enabled && <span className="badge badge-success shrink-0">Active</span>}
        </div>

        {!enabled && !setupData && (
          <button onClick={handleSetup} disabled={setupLoading} className="btn-primary h-10">
            {setupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Shield className="w-4 h-4" />}
            Set up MFA
          </button>
        )}
        {enabled && !showDisable && (
          <button onClick={() => setShowDisable(true)} className="btn-ghost h-10"
            style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}>
            <ShieldOff className="w-4 h-4" /> Disable MFA
          </button>
        )}
      </div>

      {/* ── Setup flow ── */}
      {setupData && (
        <div className="card p-6 space-y-6 animate-fade-in">
          <h2 className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
            Step 1 — Scan the QR code
          </h2>
          <p className="text-sm -mt-4" style={{ color: 'var(--text-muted)' }}>
            Open your authenticator app (Google Authenticator, Authy, 1Password, etc.) and scan this QR code.
          </p>

          {/* QR code */}
          {setupData.qr_code ? (
            <div className="flex justify-center">
              <img
                src={`data:image/png;base64,${setupData.qr_code}`}
                alt="MFA QR Code"
                className="w-48 h-48 rounded-2xl"
                style={{ border: '4px solid var(--bg-elevated)' }}
              />
            </div>
          ) : (
            <div className="rounded-xl p-6 text-center"
              style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
              <QrCode className="w-8 h-8 mx-auto mb-2" style={{ color: 'var(--text-muted)' }} />
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>QR code unavailable — use manual entry below</p>
            </div>
          )}

          {/* Manual entry secret */}
          <div>
            <p className="text-xs font-700 uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
              Manual entry key
            </p>
            <div className="flex items-center gap-2">
              <code
                className="flex-1 text-sm font-mono px-3 py-2 rounded-xl break-all"
                style={{ background: 'var(--bg-elevated)', color: 'var(--brand)', border: '1px solid var(--border)' }}
              >
                {setupData.secret}
              </code>
              <button
                onClick={() => { navigator.clipboard.writeText(setupData.secret); toast.success('Key copied!'); }}
                className="btn-ghost h-9 px-3 shrink-0 text-xs"
              >
                <Copy className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {/* Backup codes */}
          {setupData.backup_codes?.length > 0 && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-700 uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                  Backup codes — save these now!
                </p>
                <button onClick={copyBackupCodes}
                  className="text-xs font-600 flex items-center gap-1 hover:underline"
                  style={{ color: 'var(--brand)' }}>
                  {copiedCodes ? <CheckCircle className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                  {copiedCodes ? 'Copied!' : 'Copy all'}
                </button>
              </div>
              <div className="rounded-xl p-4"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                <div className="grid grid-cols-2 gap-2">
                  {setupData.backup_codes.map((code, i) => (
                    <code key={i} className="text-sm font-mono" style={{ color: 'var(--text-primary)' }}>
                      {code}
                    </code>
                  ))}
                </div>
              </div>
              <p className="text-xs mt-2 flex items-start gap-1.5" style={{ color: 'var(--threat)' }}>
                <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                Store these in a safe place. Each code can only be used once.
              </p>
            </div>
          )}

          {/* Verification */}
          <div>
            <h3 className="font-heading font-700 text-sm mb-2" style={{ color: 'var(--text-primary)' }}>
              Step 2 — Verify and enable
            </h3>
            <form onSubmit={handleVerifySetup} className="flex gap-3">
              <input
                type="text"
                inputMode="numeric"
                value={setupCode}
                onChange={e => setSetupCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                autoFocus
                className="input-base flex-1 font-mono tracking-[0.4em] text-center text-lg"
                style={setupCode.length === 6 ? { borderColor: 'var(--brand)' } : {}}
              />
              <button type="submit" disabled={setupLoading || setupCode.length !== 6}
                className="btn-primary h-11 px-5 shrink-0 text-sm">
                {setupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Enable MFA'}
              </button>
            </form>
          </div>

          <button
            onClick={() => { setSetupData(null); setSetupCode(''); }}
            className="text-sm hover:underline"
            style={{ color: 'var(--text-muted)' }}
          >
            Cancel setup
          </button>
        </div>
      )}

      {/* ── Disable form ── */}
      {showDisable && (
        <div className="card p-6 space-y-4 animate-fade-in" style={{ borderColor: 'var(--danger)' }}>
          <div className="rounded-xl p-4" style={{ background: 'var(--danger-dim)', border: '1px solid var(--danger)' }}>
            <p className="text-sm font-600 flex items-center gap-2" style={{ color: 'var(--danger)' }}>
              <AlertTriangle className="w-4 h-4" /> Disabling MFA reduces your account security
            </p>
          </div>

          <form onSubmit={handleDisable} className="space-y-4">
            <div>
              <label className="form-label">Authenticator code</label>
              <input
                type="text"
                inputMode="numeric"
                value={disableCode}
                onChange={e => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="000000"
                maxLength={6}
                autoFocus
                className="input-base font-mono tracking-[0.4em] text-center text-xl"
              />
            </div>
            <div>
              <label className="form-label">Account password</label>
              <div className="relative">
                <input
                  type={showPwd ? 'text' : 'password'}
                  value={disablePwd}
                  onChange={e => setDisablePwd(e.target.value)}
                  required
                  placeholder="Your password"
                  className="input-base pr-10"
                />
                <button type="button" tabIndex={-1} onClick={() => setShowPwd(v => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
                  {showPwd ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="flex gap-3">
              <button type="button"
                onClick={() => { setShowDisable(false); setDisableCode(''); setDisablePwd(''); }}
                className="btn-ghost flex-1 h-10 justify-center text-sm">
                Cancel
              </button>
              <button type="submit"
                disabled={disableLoading || disableCode.length !== 6 || !disablePwd}
                className="flex-1 h-10 rounded-xl font-600 text-sm flex items-center justify-center gap-2 transition-opacity disabled:opacity-50"
                style={{ background: 'var(--danger)', color: '#fff' }}>
                {disableLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldOff className="w-4 h-4" />}
                Disable MFA
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Backup codes status (when enabled) */}
      {enabled && (
        <div className="card p-5 flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
              <Key className="w-4 h-4" />
            </div>
            <div>
              <p className="font-600 text-sm" style={{ color: 'var(--text-primary)' }}>Backup codes</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {status?.has_backup_codes ? 'Backup codes are available for emergency access' : 'No backup codes — re-setup MFA to generate new ones'}
              </p>
            </div>
          </div>
          {status?.has_backup_codes && <span className="badge badge-success shrink-0">Available</span>}
        </div>
      )}
    </div>
  );
}