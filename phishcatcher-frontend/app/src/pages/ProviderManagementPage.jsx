/**
 * ProviderManagementPage.jsx
 * Manage connected email providers (Gmail, Outlook, etc.) with sync, health, and settings.
 */

import { useState } from 'react';
import {
  Mail, Plus, Trash2, Settings, RefreshCw, Wifi, WifiOff,
  Loader2, CheckCircle, AlertTriangle, Shield, Edit,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAuth } from '@/stores/authStore';
import {
  useProviders,
  useProviderHealth,
  useUpdateProvider,
  useSyncProvider,
  useDeleteProvider,
  useConnectGmailProvider,
} from '@/hooks/apiHooks';
import { providerApi } from '@/lib/api';

function ProviderIcon({ type }) {
  if (type === 'gmail') {
    return (
      <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
        style={{ background: 'var(--success-dim)', color: 'var(--success)' }}>
        <Mail className="w-5 h-5" />
      </div>
    );
  }
  return (
    <div className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0"
      style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
      <Mail className="w-5 h-5" />
    </div>
  );
}

function ProviderCard({ provider }) {
  const { data: health, isLoading: healthLoading } = useProviderHealth(provider.id);
  const updateMutation = useUpdateProvider();
  const syncMutation = useSyncProvider();
  const deleteMutation = useDeleteProvider();

  const [editing, setEditing] = useState(false);
  const [editSync, setEditSync] = useState(provider.sync_enabled);
  const [editFolder, setEditFolder] = useState(provider.sync_folder ?? '');
  const [syncing, setSyncing] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncMutation.mutateAsync({ id: provider.id });
      toast.success(`Sync started for ${provider.email_address}`);
    } catch (err) {
      toast.error(err.message ?? 'Failed to start sync');
    } finally {
      setSyncing(false);
    }
  };

  const handleSave = async () => {
    try {
      await updateMutation.mutateAsync({
        id: provider.id,
        sync_enabled: editSync,
        sync_folder: editFolder || null,
      });
      setEditing(false);
      toast.success('Provider updated');
    } catch (err) {
      toast.error(err.message ?? 'Failed to update provider');
    }
  };

  const handleDelete = async () => {
    if (!confirm(`Remove ${provider.email_address}? This will revoke access and delete synced data.`)) return;
    try {
      await deleteMutation.mutateAsync(provider.id);
      toast.success('Provider removed');
    } catch (err) {
      toast.error(err.message ?? 'Failed to remove provider');
    }
  };

  const isConnected = provider.is_connected && health?.healthy !== false;
  const lastSync = provider.last_sync_at ? new Date(provider.last_sync_at).toLocaleString() : 'Never';

  return (
    <div className="card p-5 space-y-4">
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <ProviderIcon type={provider.provider_type} />
          <div>
            <p className="font-heading font-600 text-sm" style={{ color: 'var(--text-primary)' }}>
              {provider.email_address}
            </p>
            <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
              {provider.provider_type} • {provider.is_default ? 'Default • ' : ''}Last sync: {lastSync}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          {isConnected ? (
            <span className="badge badge-success">Connected</span>
          ) : (
            <span className="badge badge-danger">Disconnected</span>
          )}
        </div>
      </div>

      {/* ── Edit mode ── */}
      {editing ? (
        <div className="space-y-3 p-3 rounded-xl" style={{ background: 'var(--bg-elevated)' }}>
          <label className="flex items-center gap-3 cursor-pointer">
            <input
              type="checkbox"
              checked={editSync}
              onChange={(e) => setEditSync(e.target.checked)}
              className="rounded"
            />
            <span className="text-sm" style={{ color: 'var(--text-primary)' }}>Enable sync</span>
          </label>
          <div>
            <label className="text-xs" style={{ color: 'var(--text-muted)' }}>Sync folder (leave empty for all)</label>
            <input
              type="text"
              value={editFolder}
              onChange={(e) => setEditFolder(e.target.value)}
              placeholder="e.g., INBOX, [Gmail]/All Mail"
              className="input mt-1 w-full h-9 text-sm"
            />
          </div>
          <div className="flex gap-2">
            <button onClick={handleSave} className="btn-primary h-8 px-3 text-sm">Save</button>
            <button onClick={() => setEditing(false)} className="btn-ghost h-8 px-3 text-sm">Cancel</button>
          </div>
        </div>
      ) : (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setEditing(true)}
            className="btn-ghost h-8 px-3 text-sm flex items-center gap-1"
          >
            <Edit className="w-3 h-3" />
            Edit
          </button>
          <button
            onClick={handleSync}
            disabled={syncing || !isConnected}
            className="btn-ghost h-8 px-3 text-sm flex items-center gap-1"
          >
            {syncing ? <Loader2 className="w-3 h-3 animate-spin" /> : <RefreshCw className="w-3 h-3" />}
            Sync
          </button>
          <button
            onClick={handleDelete}
            className="btn-ghost h-8 px-3 text-sm flex items-center gap-1"
            style={{ color: 'var(--danger)' }}
          >
            <Trash2 className="w-3 h-3" />
            Remove
          </button>
        </div>
      )}
    </div>
  );
}

export default function ProviderManagementPage() {
  const { data: providers, isLoading, refetch } = useProviders();

  const handleConnectGmail = async () => {
    try {
      const data = await providerApi.getGmailAuthUrl();
      const popup = window.open(
        data.auth_url,
        'Connect Email Account',
        'width=500,height=600,scrollbars=yes,resizable=yes'
      );

      const checkClosed = setInterval(() => {
        if (popup.closed) {
          clearInterval(checkClosed);
          refetch();
          toast.success('Account connected!');
        }
      }, 500);
    } catch (err) {
      toast.error(err.message ?? 'Failed to connect account');
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--brand)' }} />
      </div>
    );
  }

  const providerList = providers ?? [];

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Email Providers</h1>
        <p className="page-subtitle">Connect and manage your email accounts</p>
      </div>

      {/* ── Add provider card ── */}
      <div className="card p-6">
        <div className="flex items-center gap-4 mb-4">
          <div className="w-12 h-12 rounded-2xl flex items-center justify-center shrink-0"
            style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
            <Shield className="w-6 h-6" />
          </div>
          <div className="flex-1">
            <p className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
              Connected Providers
            </p>
            <p className="text-sm mt-0.5" style={{ color: 'var(--text-muted)' }}>
              {providerList.length} account{providerList.length !== 1 ? 's' : ''} connected
            </p>
          </div>
        </div>

        <button onClick={handleConnectGmail} className="btn-primary h-10 flex items-center gap-2">
          <Plus className="w-4 h-4" />
          Connect Gmail
        </button>
      </div>

      {/* ── Provider list ── */}
      {providerList.length === 0 ? (
        <div className="card p-8 text-center">
          <Mail className="w-12 h-12 mx-auto mb-3" style={{ color: 'var(--text-muted)' }} />
          <p className="font-600" style={{ color: 'var(--text-primary)' }}>No providers connected</p>
          <p className="text-sm mt-1" style={{ color: 'var(--text-muted)' }}>
            Connect your Gmail account to start analyzing emails
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {providerList.map((provider) => (
            <ProviderCard key={provider.id} provider={provider} />
          ))}
        </div>
      )}

      {/* ── Info card ── */}
      <div className="card p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: 'var(--warning)' }} />
        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
          <p className="font-600 mb-1" style={{ color: 'var(--text-primary)' }}>About email providers</p>
          <p>PhishCatcher connects to your email accounts via OAuth. We never store your password — only secure access tokens. You can remove any provider at any time.</p>
        </div>
      </div>
    </div>
  );
}
