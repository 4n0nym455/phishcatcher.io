import { useState } from 'react';
import { Bell, BellOff, Shield, ShieldOff } from 'lucide-react';
import { useNotifications } from './NotificationProvider';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Switch } from './ui/switch';
import { Badge } from './ui/badge';

export default function NotificationSettings() {
  const { isSupported, isSubscribed, permission, isLoading, requestPermission, subscribe, unsubscribe } = useNotifications();
  const [notificationTypes, setNotificationTypes] = useState({
    securityAlerts: true,
    phishingDetections: true,
    systemUpdates: false,
    marketingEmails: false,
  });

  const handlePermissionRequest = async () => {
    const granted = await requestPermission();
    if (granted) {
      await subscribe();
    }
  };

  const handleSubscribe = async () => {
    if (isSubscribed) {
      await unsubscribe();
    } else {
      await subscribe();
    }
  };

  const handleNotificationTypeChange = (type, enabled) => {
    setNotificationTypes(prev => ({
      ...prev,
      [type]: enabled
    }));
  };

  const saveNotificationPreferences = async () => {
    try {
      await fetch('/api/notifications/preferences', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        },
        body: JSON.stringify(notificationTypes)
      });
    } catch (error) {
      console.error('Failed to save notification preferences:', error);
    }
  };

  if (!isSupported) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <BellOff className="h-5 w-5" />
            Notifications Not Supported
          </CardTitle>
          <CardDescription>
            Your browser doesn't support push notifications. Please use a modern browser like Chrome, Firefox, or Safari.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Push Notification Status */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Push Notifications
            <Badge variant={permission === 'granted' ? 'default' : 'secondary'}>
              {permission === 'granted' ? 'Enabled' : permission === 'denied' ? 'Blocked' : 'Not Requested'}
            </Badge>
          </CardTitle>
          <CardDescription>
            Receive real-time notifications about security alerts and phishing detections
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {permission === 'default' && (
            <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
              <div>
                <p className="font-medium">Enable Push Notifications</p>
                <p className="text-sm text-muted-foreground">
                  Get instant alerts about security threats
                </p>
              </div>
              <Button onClick={handlePermissionRequest} disabled={isLoading}>
                {isLoading ? 'Requesting...' : 'Enable Notifications'}
              </Button>
            </div>
          )}

          {permission === 'denied' && (
            <div className="flex items-center gap-2 p-4 bg-destructive/10 rounded-lg">
              <ShieldOff className="h-5 w-5 text-destructive" />
              <div>
                <p className="font-medium text-destructive">Notifications Blocked</p>
                <p className="text-sm text-muted-foreground">
                  You've blocked notifications in your browser settings. Please enable them in your browser preferences.
                </p>
              </div>
            </div>
          )}

          {permission === 'granted' && (
            <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
              <div>
                <p className="font-medium flex items-center gap-2">
                  Push Notifications
                  {isSubscribed ? (
                    <Badge variant="default">Active</Badge>
                  ) : (
                    <Badge variant="secondary">Inactive</Badge>
                  )}
                </p>
                <p className="text-sm text-muted-foreground">
                  {isSubscribed 
                    ? 'You\'re subscribed to receive notifications' 
                    : 'Subscribe to receive notifications'
                  }
                </p>
              </div>
              <Button 
                onClick={handleSubscribe} 
                disabled={isLoading}
                variant={isSubscribed ? 'destructive' : 'default'}
              >
                {isLoading ? 'Processing...' : isSubscribed ? 'Unsubscribe' : 'Subscribe'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Notification Types */}
      {isSubscribed && (
        <Card>
          <CardHeader>
            <CardTitle>Notification Types</CardTitle>
            <CardDescription>
              Choose what types of notifications you want to receive
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <label className="text-sm font-medium">Security Alerts</label>
                <p className="text-sm text-muted-foreground">
                  Critical security threats and vulnerabilities
                </p>
              </div>
              <Switch
                checked={notificationTypes.securityAlerts}
                onCheckedChange={(checked) => handleNotificationTypeChange('securityAlerts', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <label className="text-sm font-medium">Phishing Detections</label>
                <p className="text-sm text-muted-foreground">
                  New phishing attempts detected in your emails
                </p>
              </div>
              <Switch
                checked={notificationTypes.phishingDetections}
                onCheckedChange={(checked) => handleNotificationTypeChange('phishingDetections', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <label className="text-sm font-medium">System Updates</label>
                <p className="text-sm text-muted-foreground">
                  Updates and maintenance notifications
                </p>
              </div>
              <Switch
                checked={notificationTypes.systemUpdates}
                onCheckedChange={(checked) => handleNotificationTypeChange('systemUpdates', checked)}
              />
            </div>

            <div className="flex items-center justify-between">
              <div className="space-y-1">
                <label className="text-sm font-medium">Marketing Emails</label>
                <p className="text-sm text-muted-foreground">
                  Product updates and promotional content
                </p>
              </div>
              <Switch
                checked={notificationTypes.marketingEmails}
                onCheckedChange={(checked) => handleNotificationTypeChange('marketingEmails', checked)}
              />
            </div>

            <Button onClick={saveNotificationPreferences} className="w-full">
              Save Preferences
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
