/**
 * AccountSettings.jsx
 * Profile edit, password change, MFA link, Gmail integration, account deletion.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  User, Lock, Shield, Mail, Trash2,
  Eye, EyeOff, Loader2, ChevronRight, AlertTriangle, CheckCircle2, XCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import { authApi, clearTokens } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

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

/* ─── Section wrapper ──────────────────────────────────────────────────── */
function Section({ title, subtitle, icon: Icon, iconColor, iconBg, children }) {
  return (
    <div className="card p-6 space-y-5">
      <div className="flex items-center gap-3 pb-4" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
          style={{ background: iconBg ?? 'var(--brand-dim)', color: iconColor ?? 'var(--brand)' }}>
          <Icon className="w-4 h-4" />
        </div>
        <div>
          <h2 className="font-heading font-700 text-[15px]" style={{ color: 'var(--text-primary)' }}>{title}</h2>
          {subtitle && <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{subtitle}</p>}
        </div>
      </div>
      {children}
    </div>
  );
}

export default function AccountSettingsPage() {
  const { user, refreshUser, logout } = useAuth();

  /* ── Profile state ── */
  const [name,       setName]      = useState(user?.full_name ?? '');
  const [company,    setCompany]   = useState(user?.company ?? '');
  const [profSaving, setProfSave]  = useState(false);
  const [avatarUrl, setAvatarUrl]  = useState(null);
  const [avatarUploading, setAvatarUploading] = useState(false);

  /* ── Password change state ── */
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd,     setNewPwd]     = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [showCurr,   setShowCurr]   = useState(false);
  const [showNew,    setShowNew]    = useState(false);
  const [showConf,   setShowConf]   = useState(false);
  const [pwdSaving,  setPwdSaving]  = useState(false);

  /* ── Gmail state ── */
  const [gmailStatus, setGmailStatus] = useState(null);
  const [gmailLoading, setGmailLoading] = useState(false);

  /* ── MFA status ── */
  const [mfaStatus, setMfaStatus] = useState(null);

  /* ── Delete account ── */
  const [showDelete,    setShowDelete]    = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState('');
  const [deletePwd,     setDeletePwd]     = useState('');
  const [deleting,      setDeleting]      = useState(false);

  /* Load Gmail + MFA status */
  useEffect(() => {
    const fetchData = () => {
      Promise.allSettled([authApi.gmail.getStatus(), authApi.getMfaStatus()]).then(([g, m]) => {
        if (g.status === 'fulfilled') setGmailStatus(g.value);
        if (m.status === 'fulfilled') setMfaStatus(m.value);
      });
      authApi.getAvatarUrl()
        .then((res) => setAvatarUrl(res?.avatar_url ?? null))
        .catch(() => setAvatarUrl(null));
    };

    fetchData();

    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchData();
      }
    };

    const handleFocus = () => {
      fetchData();
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('focus', handleFocus);

    const handleGmailMessage = (event) => {
      if (event.data?.type === 'gmail-connected') {
        setGmailLoading(false);
        setGmailStatus({ connected: true, email: event.data.email });
        toast.success('Gmail connected successfully!');
      } else if (event.data?.type === 'gmail-error') {
        setGmailLoading(false);
        toast.error(event.data.error || 'Failed to connect Gmail');
      }
    };
    window.addEventListener('message', handleGmailMessage);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('focus', handleFocus);
      window.removeEventListener('message', handleGmailMessage);
    };
  }, []);

  /* ── Profile save ── */
  const handleProfileSave = async e => {
    e.preventDefault();
    setProfSave(true);
    try {
      await authApi.updateProfile({ full_name: name, company });
      await refreshUser();
      toast.success('Profile updated');
    } catch (err) { toast.error(err.message ?? 'Failed to update profile'); }
    finally { setProfSave(false); }
  };

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setAvatarUploading(true);
    try {
      const res = await authApi.uploadAvatar(file);
      setAvatarUrl(res.avatar_url ?? null);
      
      // Update user context with new avatar URL
      refreshUser();
      
      toast.success('Profile picture updated');
    } catch (err) {
      toast.error(err.message ?? 'Failed to upload profile picture');
    } finally {
      setAvatarUploading(false);
      e.target.value = '';
    }
  };

  /* ── Password change ── */
  const passwordsMatch = newPwd === confirmPwd;
  const confirmDirty   = confirmPwd.length > 0;

  const handlePasswordChange = async e => {
    e.preventDefault();
    if (!passwordsMatch) return toast.error('Passwords do not match');
    setPwdSaving(true);
    try {
      await authApi.changePassword(currentPwd, newPwd);
      toast.success('Password changed successfully');
      setCurrentPwd(''); setNewPwd(''); setConfirmPwd('');
    } catch (err) { toast.error(err.message ?? 'Failed to change password'); }
    finally { setPwdSaving(false); }
  };

  /* ── Gmail ── */
  const handleGmailConnect = async () => {
    setGmailLoading(true);
    try {
      const data = await authApi.gmail.getAuthUrl();
      const popup = window.open(
        data.auth_url,
        'Gmail OAuth',
        'width=500,height=600,scrollbars=yes,resizable=yes'
      );
      
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          authApi.gmail.getStatus().then(setGmailStatus).catch(() => {});
          setGmailLoading(false);
        }
      }, 500);
    } catch (err) { toast.error(err.message ?? 'Failed to initiate Gmail connection'); setGmailLoading(false); }
  };

  const handleGmailDisconnect = async () => {
    if (!window.confirm('Disconnect Gmail? PhishCatcher will stop monitoring your inbox.')) return;
    setGmailLoading(true);
    try {
      await authApi.gmail.disconnect();
      setGmailStatus(prev => ({ ...prev, connected: false }));
      toast.success('Gmail disconnected');
    } catch (err) { toast.error(err.message ?? 'Failed to disconnect'); }
    finally { setGmailLoading(false); }
  };

  /* ── Delete account ── */
  const handleDeleteAccount = async e => {
    e.preventDefault();
    if (deleteConfirm !== 'DELETE') return toast.error('Type DELETE exactly to confirm');
    setDeleting(true);
    try {
      await authApi.deleteAccount(deletePwd);
      toast.success('Account deleted successfully');
      // Clear auth tokens and redirect immediately
      clearTokens();
      sessionStorage.clear();
      window.location.href = '/login';
    } catch (err) { 
      toast.error(err.message ?? 'Failed to delete account'); 
      setDeleting(false); 
    }
  };

  const gmailConnected = gmailStatus?.connected ?? false;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Account Settings</h1>
        <p className="page-subtitle">Manage your profile, security, and integrations</p>
      </div>

      {/* ── Profile ── */}
      <Section title="Profile" subtitle="Your personal information" icon={User}>
        <div className="flex items-center gap-4 pb-2">
          <div className="w-16 h-16 rounded-full overflow-hidden border" style={{ borderColor: 'var(--border)' }}>
            {avatarUrl ? (
              <img src={avatarUrl} alt="Profile avatar" className="w-full h-full object-cover" />
            ) : (
              <div className="w-full h-full flex items-center justify-center text-lg font-700" style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
                {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
              </div>
            )}
          </div>
          <label className="btn-ghost h-9 px-3 text-sm cursor-pointer">
            {avatarUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Upload picture'}
            <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" onChange={handleAvatarUpload} disabled={avatarUploading} />
          </label>
        </div>
        <form onSubmit={handleProfileSave} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="form-label">Full name</label>
              <input type="text" value={name} onChange={e => setName(e.target.value)} className="input-base" />
            </div>
            <div>
              <label className="form-label">Company</label>
              <input type="text" value={company} onChange={e => setCompany(e.target.value)} placeholder="Optional" className="input-base" />
            </div>
          </div>
          <div>
            <label className="form-label">Email address</label>
            <input type="email" value={user?.email ?? ''} disabled className="input-base opacity-60 cursor-not-allowed" />
            <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>Email address cannot be changed.</p>
          </div>
          <button type="submit" disabled={profSaving} className="btn-primary h-10">
            {profSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save profile'}
          </button>
        </form>
      </Section>

      {/* ── Password ── */}
      <Section title="Change Password" subtitle="Use a strong, unique password" icon={Lock}>
        <form onSubmit={handlePasswordChange} className="space-y-4">
          <div>
            <label className="form-label">Current password</label>
            <div className="relative">
              <input type={showCurr ? 'text' : 'password'} value={currentPwd}
                onChange={e => setCurrentPwd(e.target.value)} required
                autoComplete="current-password" className="input-base pr-10" />
              <button type="button" tabIndex={-1} onClick={() => setShowCurr(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
                {showCurr ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>
          <div>
            <label className="form-label">New password</label>
            <div className="relative">
              <input type={showNew ? 'text' : 'password'} value={newPwd}
                onChange={e => setNewPwd(e.target.value)} required
                autoComplete="new-password" className="input-base pr-10" />
              <button type="button" tabIndex={-1} onClick={() => setShowNew(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
                {showNew ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <PasswordStrength password={newPwd} />
          </div>
          <div>
            <label className="form-label">Confirm password</label>
            <div className="relative">
              <input type={showConf ? 'text' : 'password'} value={confirmPwd}
                onChange={e => setConfirmPwd(e.target.value)} required
                autoComplete="new-password" className="input-base pr-10"
                style={confirmDirty ? {
                  borderColor: passwordsMatch ? 'var(--success)' : 'var(--danger)',
                  boxShadow: passwordsMatch
                    ? '0 0 0 3px rgba(16,185,129,0.12)'
                    : '0 0 0 3px rgba(239,68,68,0.12)',
                } : {}} />
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
          <button type="submit" disabled={pwdSaving || (confirmDirty && !passwordsMatch)} className="btn-primary h-10">
            {pwdSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Update password'}
          </button>
        </form>
      </Section>

      {/* ── MFA ── */}
      <Section title="Two-Factor Authentication" subtitle="TOTP-based 2FA for extra security" icon={Shield}>
        <div className="flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>
              MFA is {mfaStatus?.enabled ? 'enabled' : 'not enabled'}
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {mfaStatus?.enabled
                ? 'Your account is protected by a TOTP authenticator app.'
                : 'Add an authenticator app to protect your account.'}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {mfaStatus?.enabled && <span className="badge badge-success">Active</span>}
            <Link to="/settings/mfa" className="btn-ghost h-9 px-3 text-sm">
              {mfaStatus?.enabled ? 'Manage' : 'Set up'} <ChevronRight className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </Section>

      {/* ── Gmail ── */}
      <Section title="Gmail Integration" subtitle="Monitor your inbox automatically" icon={Mail}>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div>
            <p className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>
              {gmailConnected ? `Connected: ${gmailStatus?.email ?? 'Gmail'}` : 'Not connected'}
            </p>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {gmailConnected
                ? 'PhishCatcher is monitoring your inbox for threats'
                : 'Connect Gmail to enable automatic inbox monitoring'}
            </p>
          </div>
          {gmailConnected ? (
            <button onClick={handleGmailDisconnect} disabled={gmailLoading}
              className="btn-ghost h-9 px-3 text-sm shrink-0"
              style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}>
              {gmailLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
              Disconnect
            </button>
          ) : (
            <button onClick={handleGmailConnect} disabled={gmailLoading}
              className="btn-primary h-9 px-4 text-sm shrink-0">
              {gmailLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Mail className="w-3.5 h-3.5" />}
              Connect Gmail
            </button>
          )}
        </div>

        {gmailConnected && (
          <>
            <div className="grid grid-cols-2 gap-3 mt-2">
              {[
                { label: 'Emails scanned', value: gmailStatus?.emails_scanned ?? '—' },
                { label: 'Threats found',  value: gmailStatus?.threats_found  ?? '—' },
              ].map(s => (
                <div key={s.label} className="rounded-xl p-3 text-center"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <div className="font-heading font-700 text-lg" style={{ color: 'var(--brand)' }}>{s.value}</div>
                  <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.label}</div>
                </div>
              ))}
            </div>
            <div className="mt-3">
              <Link to="/upload" className="text-xs font-500 inline-flex items-center gap-1" style={{ color: 'var(--brand)' }}>
                Load and analyze emails <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </>
        )}
      </Section>

      {/* ── Danger zone ── */}
      <div className="card p-6" style={{ borderColor: 'var(--danger)' }}>
        <div className="flex items-center gap-3 pb-4 mb-5" style={{ borderBottom: '1px solid var(--border)' }}>
          <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
            style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
            <Trash2 className="w-4 h-4" />
          </div>
          <div>
            <h2 className="font-heading font-700 text-[15px]" style={{ color: 'var(--danger)' }}>Danger Zone</h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>Irreversible actions</p>
          </div>
        </div>

        {!showDelete ? (
          <div className="flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>Delete account</p>
              <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                Permanently delete your account and all data. This cannot be undone.
              </p>
            </div>
            <button onClick={() => setShowDelete(true)}
              className="btn-ghost h-9 px-3 text-sm shrink-0"
              style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}>
              Delete account
            </button>
          </div>
        ) : (
          <form onSubmit={handleDeleteAccount} className="space-y-4 animate-fade-in">
            <div className="rounded-xl p-4" style={{ background: 'var(--danger-dim)', border: '1px solid var(--danger)' }}>
              <p className="text-sm font-600 flex items-center gap-2 mb-1" style={{ color: 'var(--danger)' }}>
                <AlertTriangle className="w-4 h-4" /> This action is permanent
              </p>
              <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                All analyses, Gmail integration, MFA settings, and account data will be permanently deleted.
              </p>
            </div>
            <div>
              <label className="form-label">Password</label>
              <input type="password" value={deletePwd} onChange={e => setDeletePwd(e.target.value)}
                required placeholder="Enter your password to confirm" className="input-base" />
            </div>
            <div>
              <label className="form-label">Type "DELETE" to confirm</label>
              <input type="text" value={deleteConfirm} onChange={e => setDeleteConfirm(e.target.value)}
                required placeholder="DELETE" className="input-base"
                style={deleteConfirm ? { borderColor: deleteConfirm === 'DELETE' ? 'var(--danger)' : 'var(--border)' } : {}} />
            </div>
            <div className="flex gap-3">
              <button type="button"
                onClick={() => { setShowDelete(false); setDeleteConfirm(''); setDeletePwd(''); }}
                className="btn-ghost flex-1 h-10 justify-center text-sm">
                Cancel
              </button>
              <button type="submit"
                disabled={deleting || deleteConfirm !== 'DELETE' || !deletePwd}
                className="btn-danger flex-1 h-10 flex items-center justify-center gap-2 text-sm">
                {deleting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Delete permanently
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}