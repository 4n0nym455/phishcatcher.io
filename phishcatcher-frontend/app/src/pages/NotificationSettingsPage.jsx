/**
 * NotificationSettingsPage.jsx
 * Manage push notification subscriptions and preference toggles.
 */

import { useState, useEffect } from 'react';
import {
  Bell, BellOff, Shield, AlertTriangle, Mail, FileText,
  Loader2, CheckCircle, XCircle, RefreshCw,
} from 'lucide-react';
import { toast } from 'sonner';
import {
  useNotificationPreferences,
  useUpdateNotificationPreferences,
  useNotifications,
  useMarkNotificationRead,
  useMarkAllNotificationsRead,
} from '@/hooks/apiHooks';

function ToggleSwitch({ checked, onChange, label, description }) {
  return (
    <div className="flex items-center justify-between py-3" style={{ borderBottom: '1px solid var(--border)' }}>
      <div className="flex-1 pr-4">
        <p className="text-sm font-600" style={{ color: 'var(--text-primary)' }}>{label}</p>
        {description && <p className="text-xs mt-0.5" style={{ color: 'var(--text-muted)' }}>{description}</p>}
      </div>
      <button
        onClick={() => onChange(!checked)}
        className="relative w-10 h-6 rounded-full transition-colors duration-200 shrink-0"
        style={{ background: checked ? 'var(--brand)' : 'var(--border)' }}
        role="switch"
        aria-checked={checked}
      >
        <div
          className="absolute top-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200"
          style={{ transform: checked ? 'translateX(20px)' : 'translateX(2px)' }}
        />
      </button>
    </div>
  );
}

export default function NotificationSettingsPage() {
  const { data: preferences, isLoading: prefsLoading } = useNotificationPreferences();
  const updateMutation = useUpdateNotificationPreferences();
  const { data: notifData, refetch: refetchNotifs } = useNotifications({ limit: 10, unreadOnly: false });
  const markReadMutation = useMarkNotificationRead();
  const markAllReadMutation = useMarkAllNotificationsRead();

  const [localPrefs, setLocalPrefs] = useState(null);

  useEffect(() => {
    if (preferences) {
      setLocalPrefs(preferences);
    }
  }, [preferences]);

  const handleToggle = async (key) => {
    const updated = { ...localPrefs, [key]: !localPrefs[key] };
    setLocalPrefs(updated);
    try {
      await updateMutation.mutateAsync(updated);
      toast.success('Preferences updated');
    } catch {
      setLocalPrefs(preferences);
      toast.error('Failed to update preferences');
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await markAllReadMutation.mutateAsync();
      toast.success('All notifications marked as read');
      refetchNotifs();
    } catch {
      toast.error('Failed to mark all as read');
    }
  };

  const handleMarkRead = async (id) => {
    try {
      await markReadMutation.mutateAsync(id);
      refetchNotifs();
    } catch {
      toast.error('Failed to mark as read');
    }
  };

  if (prefsLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="w-6 h-6 animate-spin" style={{ color: 'var(--brand)' }} />
      </div>
    );
  }

  const notifications = notifData?.notifications ?? [];
  const unreadCount = notifData?.unread_count ?? 0;

  return (
    <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
      <div className="page-header">
        <h1 className="page-title">Notifications</h1>
        <p className="page-subtitle">Configure how and when you receive alerts</p>
      </div>

      {/* ── Preferences card ── */}
      {localPrefs && (
        <div className="card p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: 'var(--brand-dim)', color: 'var(--brand)' }}>
              <Bell className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
                Notification Preferences
              </h2>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Choose which events trigger a notification
              </p>
            </div>
          </div>

          <div className="divide-y">
            <ToggleSwitch
              checked={localPrefs.security_alerts ?? true}
              onChange={() => handleToggle('security_alerts')}
              label="Security Alerts"
              description="Login attempts, password changes, and suspicious activity"
            />
            <ToggleSwitch
              checked={localPrefs.phishing_detections ?? true}
              onChange={() => handleToggle('phishing_detections')}
              label="Phishing Detections"
              description="When a new threat is detected in your emails"
            />
            <ToggleSwitch
              checked={localPrefs.analysis_complete ?? true}
              onChange={() => handleToggle('analysis_complete')}
              label="Analysis Complete"
              description="When email analysis finishes processing"
            />
            <ToggleSwitch
              checked={localPrefs.weekly_reports ?? false}
              onChange={() => handleToggle('weekly_reports')}
              label="Weekly Reports"
              description="Receive a weekly summary of your email threats"
            />
            <ToggleSwitch
              checked={localPrefs.product_updates ?? false}
              onChange={() => handleToggle('product_updates')}
              label="Product Updates"
              description="New features and improvements"
            />
          </div>
        </div>
      )}

      {/* ── Recent notifications ── */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
              style={{ background: 'var(--bg-elevated)', color: 'var(--text-muted)' }}>
              <Bell className="w-4 h-4" />
            </div>
            <div>
              <h2 className="font-heading font-700 text-base" style={{ color: 'var(--text-primary)' }}>
                Recent Notifications
              </h2>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                {unreadCount > 0 ? `${unreadCount} unread` : 'All caught up'}
              </p>
            </div>
          </div>
          {unreadCount > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="btn-ghost h-8 px-3 text-xs flex items-center gap-1"
            >
              <CheckCircle className="w-3 h-3" />
              Mark all read
            </button>
          )}
        </div>

        {notifications.length === 0 ? (
          <div className="text-center py-8">
            <BellOff className="w-8 h-8 mx-auto mb-2" style={{ color: 'var(--text-muted)' }} />
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No notifications yet</p>
          </div>
        ) : (
          <div className="space-y-2">
            {notifications.map((notif) => {
              const Icon = notif.type === 'security' ? Shield
                : notif.type === 'phishing' ? AlertTriangle
                : notif.type === 'analysis' ? FileText
                : Mail;
              return (
                <div
                  key={notif.id}
                  onClick={() => !notif.is_read && handleMarkRead(notif.id)}
                  className="flex items-start gap-3 p-3 rounded-xl cursor-pointer transition-colors"
                  style={{
                    background: notif.is_read ? 'transparent' : 'var(--bg-elevated)',
                    border: `1px solid ${notif.is_read ? 'transparent' : 'var(--border)'}`,
                  }}
                >
                  <div className="w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5"
                    style={{
                      background: notif.is_read ? 'var(--bg-elevated)' : 'var(--brand-dim)',
                      color: notif.is_read ? 'var(--text-muted)' : 'var(--brand)',
                    }}>
                    <Icon className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-500 truncate" style={{ color: 'var(--text-primary)' }}>
                      {notif.title}
                    </p>
                    <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-muted)' }}>
                      {notif.message}
                    </p>
                    <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                      {new Date(notif.created_at).toLocaleString()}
                    </p>
                  </div>
                  {!notif.is_read && (
                    <div className="w-2 h-2 rounded-full shrink-0 mt-2" style={{ background: 'var(--brand)' }} />
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Push notification setup ── */}
      <div className="card p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: 'var(--warning)' }} />
        <div className="text-sm" style={{ color: 'var(--text-muted)' }}>
          <p className="font-600 mb-1" style={{ color: 'var(--text-primary)' }}>Browser Notifications</p>
          <p>Push notifications require HTTPS and browser permission. Enable them in your browser settings to receive real-time alerts even when PhishCatcher is closed.</p>
        </div>
      </div>
    </div>
  );
}
