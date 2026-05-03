/**
 * GmailSettingsPage.jsx
 * Full Gmail account management - list, add, remove, set default accounts.
 */

import { useState, useEffect } from 'react';
import {
  Mail, MailPlus, Trash2, Shield, CheckCircle,
  Loader2, AlertTriangle, RefreshCw, Settings,
  RotateCcw, Wifi, WifiOff,
} from 'lucide-react';
import { toast } from 'sonner';
import { authApi } from '@/lib/api';
import { useAuth } from '@/stores/authStore';

export default function GmailSettingsPage() {
  const { refreshUser } = useAuth();

  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [addingAccount, setAddingAccount] = useState(false);
  const [accountToRemove, setAccountToRemove] = useState(null);
  const [removing, setRemoving] = useState(false);
  const [reconnectingId, setReconnectingId] = useState(null);

  useEffect(() => {
    fetchGmailStatus();
  }, []);

  const fetchGmailStatus = () => {
    authApi.gmail.getStatus()
      .then(setStatus)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  /* ── Add new account ── */
  const handleAddAccount = async () => {
    setAddingAccount(true);
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
          setAddingAccount(false);
          fetchGmailStatus();
          toast.success('Gmail account added!');
        }
      }, 500);
    } catch (err) {
      toast.error(err.message ?? 'Failed to add Gmail account');
      setAddingAccount(false);
    }
  };

  /* ── Remove account ── */
  const handleRemoveAccount = async () => {
    if (!accountToRemove) return;
    setRemoving(true);
    try {
      await authApi.gmail.removeAccount(accountToRemove.id);
      toast.success('Gmail account removed');
      setAccountToRemove(null);
      fetchGmailStatus();
    } catch (err) {
      toast.error(err.message ?? 'Failed to remove account');
    } finally {
      setRemoving(false);
    }
  };

  /* ── Reconnect account ── */
  const handleReconnectAccount = async (account) => {
    setReconnectingId(account.id);
    try {
      const data = await authApi.gmail.getReconnectUrl(account.id);
      const popup = window.open(
        data.auth_url,
        'Gmail OAuth',
        'width=500,height=600,scrollbars=yes,resizable=yes'
      );
      
      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          setReconnectingId(null);
          fetchGmailStatus();
          toast.success(`${data.email} reconnected successfully!`);
        }
      }, 500);
    } catch (err) {
      toast.error(err.message ?? 'Failed to reconnect account');
      setReconnectingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--brand)' }} />
      </div>
    );
  }

  const accounts = status?.accounts ?? [];
  const hasAccounts = accounts.length > 0;
  const connected = status?.connected ?? false;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Gmail Integration</h1>
        <p className="page-subtitle">Connect your Gmail, no more second guessing — the email you received is safe</p>
      </div>

      {/* ── Status card ── */}
      <div className="card p-6">
        <div className="flex items-center gap-4 mb-5">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
            style={{ background: connected ? 'var(--success-dim)' : 'var(--bg-elevated)', color: connected ? 'var(--success)' : 'var(--text-muted)' }}>
            {connected ? <CheckCircle className="w-6 h-6" /> : <Mail className="w-6 h-6" />}
          </div>
          <div className="flex-1">
            <p className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
              {hasAccounts ? `${accounts.length} account${accounts.length > 1 ? 's' : ''} connected` : 'No accounts connected'}
            </p>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {connected
                ? 'Connect your Gmail, no more second guessing — the email you received is safe'
                : 'Connect your Gmail, no more second guessing — the email you received is safe'}
            </p>
          </div>
          {connected && <span className="badge badge-success shrink-0">Active</span>}
        </div>

        <button onClick={handleAddAccount} disabled={addingAccount} className="btn-primary h-10">
          {addingAccount ? <Loader2 className="w-4 h-4 animate-spin" /> : <MailPlus className="w-4 h-4" />}
          Add Gmail Account
        </button>
      </div>

      {/* ── Connected accounts list ── */}
      {hasAccounts && (
        <div className="card p-6 space-y-4">
          <h2 className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
            Connected Accounts
          </h2>
          
          <div className="space-y-3">
            {accounts.map((account) => (
              <div key={account.id} 
                className="flex items-center justify-between p-4 rounded-xl"
                style={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
                <div className="flex items-center gap-3 min-w-0">
                  <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0"
                    style={{ background: account.is_connected ? 'var(--success-dim)' : 'var(--danger-dim)', color: account.is_connected ? 'var(--success)' : 'var(--danger)' }}>
                    {account.is_connected ? <CheckCircle className="w-5 h-5" /> : <WifiOff className="w-5 h-5" />}
                  </div>
                  <div className="min-w-0">
                    <p className="font-600 truncate" style={{ color: 'var(--text-primary)' }}>
                      {account.email}
                    </p>
                    <div className="flex items-center gap-2 text-xs" style={{ color: 'var(--text-muted)' }}>
                      {account.is_legacy && <span className="badge badge-warning">Legacy</span>}
                      {!account.is_connected && <span className="badge badge-danger">Needs reconnect</span>}
                      {account.is_connected && <span>Connected</span>}
                      {account.last_sync_at && (
                        <>
                          <span>•</span>
                          <span>Last sync: {new Date(account.last_sync_at).toLocaleDateString()}</span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="flex items-center gap-2 shrink-0">
                  {!account.is_connected && !account.is_legacy && (
                    <button
                      onClick={() => handleReconnectAccount(account)}
                      disabled={reconnectingId === account.id}
                      className="btn-primary h-9 px-3 text-sm flex items-center gap-1.5"
                      title="Reconnect this account">
                      {reconnectingId === account.id ? (
                        <Loader2 className="w-4 h-4 animate-spin" />
                      ) : (
                        <RotateCcw className="w-4 h-4" />
                      )}
                      Reconnect
                    </button>
                  )}
                  <button
                    onClick={() => setAccountToRemove(account)}
                    className="btn-ghost h-9 px-3 text-sm"
                    style={{ color: 'var(--danger)', borderColor: 'var(--danger)' }}>
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Stats ── */}
      {hasAccounts && (
        <div className="grid grid-cols-2 gap-4">
          <div className="card p-4 text-center">
            <p className="text-2xl font-700" style={{ color: 'var(--text-primary)' }}>
              {status?.emails_scanned ?? 0}
            </p>
            <p className="text-xs font-500" style={{ color: 'var(--text-muted)' }}>
              Emails scanned
            </p>
          </div>
          <div className="card p-4 text-center">
            <p className="text-2xl font-700" style={{ color: 'var(--text-primary)' }}>
              {status?.threats_found ?? 0}
            </p>
            <p className="text-xs font-500" style={{ color: 'var(--text-muted)' }}>
              Threats found
            </p>
          </div>
        </div>
      )}

      {/* ── Info card ── */}
      <div className="card p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: 'var(--warning)' }} />
        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
          <p className="font-600 mb-1" style={{ color: 'var(--text-primary)' }}>How it works</p>
          <p>PhishCatcher uses OAuth to securely connect to your Gmail. We never store your password — only secure access tokens.</p>
          <p className="mt-2">You can connect multiple Gmail accounts. Each account can be removed at any time.</p>
        </div>
      </div>

      {/* ── Remove confirmation dialog ── */}
      {accountToRemove && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setAccountToRemove(null)} />
          <div className="relative bg-[var(--bg-surface)] rounded-xl p-6 w-full max-w-sm mx-4 shadow-2xl">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div>
                <h3 className="text-lg font-600" style={{ color: 'var(--text-primary)' }}>
                  Remove {accountToRemove.email}?
                </h3>
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>This action cannot be undone</p>
              </div>
            </div>
            
            <div className="mb-6 p-3 rounded-lg" style={{ background: 'var(--bg-elevated)' }}>
              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                PhishCatcher will stop analyzing this email account. You can reconnect at any time.
              </p>
            </div>

            <div className="flex gap-3">
              <button 
                onClick={() => setAccountToRemove(null)} 
                className="btn-ghost flex-1"
              >
                Cancel
              </button>
              <button 
                onClick={handleRemoveAccount} 
                disabled={removing}
                className="flex-1 h-10 px-4 rounded-lg font-500 text-sm flex items-center justify-center gap-2"
                style={{ background: 'var(--danger)', color: 'white' }}
              >
                {removing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Trash2 className="w-4 h-4" />}
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}