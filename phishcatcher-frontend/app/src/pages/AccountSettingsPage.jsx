/**
 * AccountSettings.jsx
 * Profile edit, password change, MFA link, Gmail integration, account deletion.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  User, Lock, Shield, Mail, Trash2,
  Eye, EyeOff, Loader2, ChevronRight, AlertTriangle, CheckCircle2, XCircle, Plus, Settings,
  Bell, Monitor, Phone, Smartphone,
} from 'lucide-react';
import { toast } from 'sonner';
import { authApi, clearTokens } from '@/lib/api';
import { useAuth } from '@/stores/authStore';

const MAX_AVATAR_SIZE = 10 * 1024 * 1024; // 10MB

function getAvatarUrlWithTimestamp(avatarUrl, timestamp) {
  if (!avatarUrl) return null;
  if (!timestamp) return avatarUrl;
  const ts = typeof timestamp === 'string' 
    ? Math.floor(new Date(timestamp).getTime() / 1000)
    : timestamp;
  return `${avatarUrl}?t=${ts}`;
}

function tokenizePhone(phone) {
  if (!phone) return null;
  const clean = phone.replace(/\s+/g, '');
  if (clean.length < 8) return '+***';
  const last4 = clean.slice(-4);
  return `+***-***-${last4}`;
}

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
  const { user, refreshUser, logout, isAdmin } = useAuth();

  /* ── Profile state ── */
  const [name,       setName]      = useState(user?.full_name ?? '');
  const [company,    setCompany]   = useState(user?.company ?? '');
  const [profSaving, setProfSave]  = useState(false);
  const [avatarUrl, setAvatarUrl]  = useState(null);
  const [avatarTimestamp, setAvatarTimestamp] = useState(null);
  const [avatarUploading, setAvatarUploading] = useState(false);

  /* ── Phone state ── */
  const [phone, setPhoneState] = useState(user?.phone ?? '');
  const [phoneVerified, setPhoneVerified] = useState(user?.phone_verified ?? false);
  const [phoneInput, setPhoneInput] = useState('');
  const [phoneOtp, setPhoneOtp] = useState('');
  const [phoneSaving, setPhoneSaving] = useState(false);
  const [phoneError, setPhoneError] = useState('');
  const [phoneStep, setPhoneStep] = useState('none');

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
  const [showGmailDisconnectDialog, setShowGmailDisconnectDialog] = useState(false);
  const [accountToDisconnect, setAccountToDisconnect] = useState(null);
  const [showGmailConnecting, setShowGmailConnecting] = useState(false);

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
        .then((res) => {
          setAvatarUrl(res?.avatar_url ?? null);
          setAvatarTimestamp(user?.avatar_updated_at ?? Date.now());
        })
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
        setShowGmailConnecting(false);
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

    const allowedTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
      toast.error('Please select an image (JPG, PNG, or WEBP)');
      e.target.value = '';
      return;
    }

    if (file.size > MAX_AVATAR_SIZE) {
      toast.error('File too large. Maximum size is 10MB.');
      e.target.value = '';
      return;
    }

    setAvatarUploading(true);
    try {
      const res = await authApi.uploadAvatar(file);
      setAvatarUrl(res.avatar_url ?? null);
      setAvatarTimestamp(Date.now());
      refreshUser();
      toast.success('Profile picture updated');
    } catch (err) {
      toast.error(err.message ?? 'Failed to upload profile picture');
    } finally {
      setAvatarUploading(false);
      e.target.value = '';
    }
  };

  /* ── Phone ── */
  const phoneDigits = phoneInput.replace(/[^+\d]/g, '');
  const phoneInputValid = /^\+\d{7,15}$/.test(phoneDigits);

  const handleUpdatePhone = async e => {
    e.preventDefault();
    setPhoneError('');
    if (!phoneInputValid) return setPhoneError('Enter a valid phone in E.164 format (e.g., +254876543210)');
    setPhoneSaving(true);
    try {
      await authApi.updatePhone(phoneDigits);
      setPhoneStep('otp');
      setPhoneOtp('');
      toast.success('Verification code sent to your phone');
    } catch (err) { setPhoneError(err.message ?? 'Failed to update phone'); }
    finally { setPhoneSaving(false); }
  };

  const handleVerifyPhone = async e => {
    e.preventDefault();
    setPhoneError('');
    if (phoneOtp.length !== 6) return setPhoneError('Enter the 6-digit code');
    setPhoneSaving(true);
    try {
      await authApi.verifyPhone(phoneOtp);
      setPhoneState(phoneDigits);
      setPhoneVerified(true);
      setPhoneStep('none');
      setPhoneInput('');
      setPhoneOtp('');
      await refreshUser();
      toast.success('Phone number verified!');
    } catch (err) { setPhoneError(err.message ?? 'Invalid verification code'); }
    finally { setPhoneSaving(false); }
  };

  const handleRemovePhone = async () => {
    try {
      await authApi.updatePhone('');
      setPhoneState('');
      setPhoneVerified(false);
      await refreshUser();
      toast.success('Phone number removed');
    } catch (err) { toast.error(err.message ?? 'Failed to remove phone'); }
  };

  const cancelPhoneUpdate = () => {
    setPhoneStep('none');
    setPhoneInput('');
    setPhoneOtp('');
    setPhoneError('');
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
    setShowGmailConnecting(true);
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
          setShowGmailConnecting(false);
        }
      }, 500);
    } catch (err) { 
      toast.error(err.message ?? 'Failed to initiate Gmail connection'); 
      setGmailLoading(false);
      setShowGmailConnecting(false);
    }
  };

  const handleGmailDisconnect = async () => {
    setShowGmailDisconnectDialog(false);
    setGmailLoading(true);
    try {
      if (accountToDisconnect?.id) {
        await authApi.gmail.removeAccount(accountToDisconnect.id);
      } else {
        await authApi.gmail.disconnect();
      }
      // Refresh status to get updated accounts list
      const status = await authApi.gmail.getStatus();
      setGmailStatus(status);
      toast.success('Account removed successfully');
    } catch (err) { toast.error(err.message ?? 'Failed to disconnect'); }
    finally { 
      setGmailLoading(false);
      setAccountToDisconnect(null);
    }
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
          <div className="w-16 h-16 rounded-full overflow-hidden border flex items-center justify-center" style={{ borderColor: 'var(--border)', background: 'var(--bg-elevated)' }}>
            {avatarUrl ? (
              <img src={getAvatarUrlWithTimestamp(avatarUrl, avatarTimestamp)} alt="Profile avatar" className="w-full h-full object-cover" />
            ) : (
              <User className="w-8 h-8" style={{ color: 'var(--text-muted)' }} />
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

      {/* ── Phone ── */}
      <Section title="Phone Number" subtitle="SMS OTP for login verification" icon={Phone}>
        {phoneStep === 'none' && phone && phoneVerified ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between gap-4">
              <div>
                <p className="text-sm font-500" style={{ color: 'var(--text-primary)' }}>
                  {tokenizePhone(phone)}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>
                  Verified — you will receive SMS codes during login.
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <span className="badge badge-success">Verified</span>
                <button onClick={handleRemovePhone}
                  className="btn-ghost h-8 px-2 text-xs"
                  style={{ color: 'var(--danger)' }}>
                  Remove
                </button>
              </div>
            </div>
            <button onClick={() => { setPhoneStep('phone'); setPhoneInput(phone); }}
              className="btn-ghost h-9 px-3 text-sm w-full justify-center">
              Change phone number
            </button>
          </div>
        ) : phoneStep === 'none' && phone ? (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-sm" style={{ color: 'var(--text-primary)' }}>{tokenizePhone(phone)}</span>
              <span className="badge badge-warning">Unverified</span>
            </div>
            <button onClick={() => setPhoneStep('phone')}
              className="btn-ghost h-9 px-3 text-sm w-full justify-center">
              Verify phone
            </button>
          </div>
        ) : phoneStep === 'none' ? (
          <div className="space-y-3">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No phone number set.</p>
            <button onClick={() => setPhoneStep('phone')}
              className="btn-ghost h-9 px-3 text-sm w-full justify-center">
              <Plus className="w-3.5 h-3.5" /> Add phone number
            </button>
          </div>
        ) : null}

        {phoneStep !== 'none' && (
          <form className={phoneStep === 'none' ? '' : 'mt-4 space-y-3 animate-fade-in'}>
            {phoneStep === 'phone' && (
              <div>
                <label className="form-label">Phone number</label>
                <input
                  type="tel"
                  value={phoneInput}
                  onChange={e => {
                    const digits = e.target.value.replace(/[^+\d]/g, '');
                    setPhoneInput(digits);
                  }}
                  placeholder="+254876543210"
                  className="input-base"
                  style={!phoneInputValid && phoneInput ? {
                    borderColor: 'var(--danger)',
                    boxShadow: '0 0 0 3px rgba(239,68,68,0.12)',
                  } : {}}
                />
                {phoneInput && !phoneInputValid && (
                  <p className="text-xs mt-1" style={{ color: 'var(--danger)' }}>
                    E.164 format required
                  </p>
                )}
              </div>
            )}

            {phoneStep === 'otp' && (
              <div>
                <label className="form-label">Verification code</label>
                <input
                  type="text"
                  value={phoneOtp}
                  onChange={e => setPhoneOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  placeholder="123456"
                  maxLength={6}
                  className="input-base"
                  style={{ letterSpacing: '0.5em', textAlign: 'center', fontSize: '1.25rem' }}
                />
                <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                  Enter the 6-digit code sent to {tokenizePhone(phoneInput) || phoneInput}.
                </p>
              </div>
            )}

            {phoneError && (
              <div className="alert-error">{phoneError}</div>
            )}

            <div className="flex gap-3">
              <button type="button" onClick={cancelPhoneUpdate}
                className="btn-ghost flex-1 h-10 text-sm">
                Cancel
              </button>
              {phoneStep === 'phone' ? (
                <button type="submit" onClick={handleUpdatePhone}
                  disabled={!phoneInputValid || phoneSaving}
                  className="btn-primary flex-1 h-10 text-sm">
                  {phoneSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Send code'}
                </button>
              ) : (
                <button type="submit" onClick={handleVerifyPhone}
                  disabled={phoneOtp.length !== 6 || phoneSaving}
                  className="btn-primary flex-1 h-10 text-sm">
                  {phoneSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Verify'}
                </button>
              )}
            </div>
          </form>
        )}
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
      <Section title="Multi-Factor Authentication" subtitle="TOTP-based MFA for extra security" icon={Shield}>
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

      {/* ── Quick Settings Links ── */}
      <Section title="More Settings" subtitle="Additional configuration options" icon={Settings}>
        <div className="space-y-2">
          {[
            ...(isAdmin ? [{ to: '/admin/sessions', icon: Shield, label: 'Active Sessions', desc: 'View and manage sessions' }] : []),
            { to: '/settings/notifications', icon: Bell, label: 'Notifications', desc: 'Configure alerts and preferences' },
            { to: '/settings/gmail', icon: Mail, label: 'Gmail Integration', desc: 'Manage connected email accounts' },
          ].map(({ to, icon: Icon, label, desc }) => (
            <Link key={to} to={to}
              className="flex items-center gap-3 p-3 rounded-xl transition-colors"
              style={{ color: 'var(--text-primary)' }}
              onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-elevated)'}
              onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
              <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
                style={{ background: 'var(--bg-elevated)', color: 'var(--brand)' }}>
                <Icon className="w-4 h-4" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-600">{label}</p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{desc}</p>
              </div>
              <ChevronRight className="w-4 h-4 shrink-0" style={{ color: 'var(--text-muted)' }} />
            </Link>
          ))}
        </div>
      </Section>

      {/* ── Gmail ── */}
      <Section title="Gmail Integration" subtitle="Connect your Gmail, no more second guessing — the email you received is safe" icon={Mail}>
        <div className="space-y-3">
          {/* Connected accounts count */}
          <p className="text-sm" style={{ color: 'var(--text-primary)' }}>
            {gmailStatus?.connected 
              ? `${gmailStatus.accounts?.length || 0} account${(gmailStatus.accounts?.length || 0) !== 1 ? 's' : ''} connected`
              : 'No Gmail accounts connected'}
          </p>
          
          {/* Stats - always show if available */}
          {gmailStatus?.connected && (
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: 'Emails scanned', value: gmailStatus?.emails_scanned ?? '—' },
                { label: 'Threats found',  value: gmailStatus?.threats_found  ?? '—' },
              ].map(s => (
                <div key={s.label} className="rounded-xl p-3 text-center"
                  style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                  <p className="text-lg font-600" style={{ color: 'var(--text-primary)' }}>{s.value}</p>
                  <p className="text-xs" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
                </div>
              ))}
            </div>
          )}
          
          {/* Link to full Gmail settings page */}
          <Link to="/settings/gmail" className="btn-primary h-10 px-4 text-sm w-full justify-center flex items-center gap-2 mt-2">
            <Settings className="w-4 h-4" />
            Manage connections
          </Link>
        </div>
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

      {/* Gmail Connecting Dialog */}
      {showGmailConnecting && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" />
          <div
            className="relative w-full max-w-sm mx-4 rounded-2xl p-6 text-center"
            style={{ background: 'var(--bg-surface)', border: '1px solid var(--border)', boxShadow: 'var(--shadow-lg)' }}
          >
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
              style={{ background: 'var(--brand-dim)' }}>
              <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--brand)' }} />
            </div>
            
            <h3 className="font-heading font-700 text-lg mb-2" style={{ color: 'var(--text-primary)' }}>
              Connecting to Gmail...
            </h3>
            
            <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>
              A browser popup has opened. Sign in with your Google account and grant access to PhishCatcher.
            </p>
            
            <p className="text-xs mb-6" style={{ color: 'var(--text-muted)' }}>
              This window will close automatically once connected.
            </p>
            
            <button
              onClick={() => setShowGmailConnecting(false)}
              className="btn-ghost w-full"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Gmail Disconnect Confirmation Dialog */}
      {showGmailDisconnectDialog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setShowGmailDisconnectDialog(false)} />
          <div className="relative bg-white dark:bg-gray-900 rounded-xl p-6 w-full max-w-sm mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'var(--danger-dim, #fee2e2)' }}>
                <AlertTriangle className="w-5 h-5" style={{ color: 'var(--danger)' }} />
              </div>
              <div>
                <h3 className="text-lg font-600" style={{ color: 'var(--text-primary)' }}>
                  {accountToDisconnect ? `Remove ${accountToDisconnect.email}?` : 'Disconnect Gmail?'}
                </h3>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>This action cannot be undone</p>
              </div>
            </div>
            
            <div className="mb-6 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                PhishCatcher will stop analyzing this email account. You can reconnect at any time, but you'll need to re-authorize access.
              </p>
            </div>

            <div className="flex gap-3">
              <button 
                onClick={() => { setShowGmailDisconnectDialog(false); setAccountToDisconnect(null); }} 
                className="btn-ghost flex-1"
              >
                Cancel
              </button>
              <button 
                onClick={handleGmailDisconnect} 
                disabled={gmailLoading}
                className="flex-1 h-10 px-4 rounded-lg font-500 text-sm flex items-center justify-center gap-2"
                style={{ background: 'var(--danger)', color: 'white' }}
              >
                {gmailLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}