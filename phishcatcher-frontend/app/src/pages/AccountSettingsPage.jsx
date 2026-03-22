/**
 * AccountSettings.jsx
 * Profile edit, password change, MFA link, Gmail integration, account deletion.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  User, Lock, Shield, Mail, Trash2,
  Eye, EyeOff, Loader2, ChevronRight, AlertTriangle,
} from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';
import { useAuth } from '@/context/AuthContext';

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

  /* ── Password change state ── */
  const [currentPwd, setCurrentPwd] = useState('');
  const [newPwd,     setNewPwd]     = useState('');
  const [confirmPwd, setConfirmPwd] = useState('');
  const [showCurr,   setShowCurr]   = useState(false);
  const [showNew,    setShowNew]    = useState(false);
  const [showConf,   setShowConf]   = useState(false);
  const [pwdSaving,  setPwdSaving]  = useState(false);

  /* ── Gmail state ── */
  const [gmailStatus,  setGmailStatus]  = useState(null);
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
    Promise.allSettled([authApi.gmail.getStatus(), authApi.getMfaStatus()]).then(([g, m]) => {
      if (g.status === 'fulfilled') setGmailStatus(g.value);
      if (m.status === 'fulfilled') setMfaStatus(m.value);
    });
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
      window.location.href = data.auth_url;
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
      toast.success('Account deleted');
      await logout();
    } catch (err) { toast.error(err.message ?? 'Failed to delete account'); setDeleting(false); }
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
          </div>
          <div>
            <label className="form-label">Confirm new password</label>
            <div className="relative">
              <input type={showConf ? 'text' : 'password'} value={confirmPwd}
                onChange={e => setConfirmPwd(e.target.value)} required
                autoComplete="new-password" className="input-base pr-10"
                style={confirmDirty ? { borderColor: passwordsMatch ? 'var(--success)' : 'var(--danger)' } : {}} />
              <button type="button" tabIndex={-1} onClick={() => setShowConf(v => !v)}
                className="absolute right-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }}>
                {showConf ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            {confirmDirty && !passwordsMatch && (
              <p className="text-xs mt-1 font-500" style={{ color: 'var(--danger)' }}>Passwords do not match</p>
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
          <div className="grid grid-cols-3 gap-3 mt-2">
            {[
              { label: 'Emails scanned', value: gmailStatus?.emails_scanned ?? '—' },
              { label: 'Threats found',  value: gmailStatus?.threats_found  ?? '—' },
              { label: 'Auto-scan',      value: gmailStatus?.auto_scan ? 'On' : 'Off' },
            ].map(s => (
              <div key={s.label} className="rounded-xl p-3 text-center"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                <div className="font-heading font-700 text-lg" style={{ color: 'var(--brand)' }}>{s.value}</div>
                <div className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.label}</div>
              </div>
            ))}
          </div>
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