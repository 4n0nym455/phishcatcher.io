import { useState } from 'react';
import { Bell, ShieldAlert, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';

export default function NotificationTest() {
  const [testNotifications, setTestNotifications] = useState([]);

  const addTestNotification = (type, title, message) => {
    const notification = {
      id: Date.now(),
      type,
      title,
      message,
      is_read: false,
      created_at: new Date().toISOString(),
      onClick: () => console.log(`Clicked notification: ${title}`)
    };
    
    setTestNotifications(prev => [notification, ...prev]);
  };

  const clearNotifications = () => {
    setTestNotifications([]);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5" />
            Push Notification Test Center
          </CardTitle>
          <CardDescription>
            Test different types of notifications to see how they appear
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Button
              onClick={() => addTestNotification(
                'security',
                'Security Alert',
                'Suspicious login attempt detected from new device'
              )}
              className="flex items-center gap-2"
            >
              <ShieldAlert className="h-4 w-4" />
              Security Alert
            </Button>

            <Button
              onClick={() => addTestNotification(
                'phishing',
                'Phishing Detected',
                'New phishing email detected in your inbox'
              )}
              variant="outline"
              className="flex items-center gap-2"
            >
              <AlertTriangle className="h-4 w-4" />
              Phishing Alert
            </Button>

            <Button
              onClick={() => addTestNotification(
                'success',
                'Analysis Complete',
                'Email analysis completed successfully'
              )}
              variant="secondary"
              className="flex items-center gap-2"
            >
              <CheckCircle className="h-4 w-4" />
              Success Notification
            </Button>

            <Button
              onClick={() => addTestNotification(
                'info',
                'System Update',
                'New features available in PhishCatcher'
              )}
              variant="ghost"
              className="flex items-center gap-2"
            >
              <Info className="h-4 w-4" />
              Info Notification
            </Button>
          </div>

          <Button
            onClick={clearNotifications}
            variant="destructive"
            className="w-full"
          >
            Clear All Notifications
          </Button>
        </CardContent>
      </Card>

      {/* Recent Test Notifications */}
      {testNotifications.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span>Recent Test Notifications</span>
              <Badge variant="secondary">{testNotifications.length}</Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {testNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className="flex items-start gap-3 p-3 glass-card rounded-lg"
                >
                  <div className="flex-shrink-0">
                    {notification.type === 'security' && <ShieldAlert className="w-4 h-4 text-rose-500" />}
                    {notification.type === 'phishing' && <AlertTriangle className="w-4 h-4 text-amber-500" />}
                    {notification.type === 'success' && <CheckCircle className="w-4 h-4 text-emerald-500" />}
                    {notification.type === 'info' && <Info className="w-4 h-4 text-blue-500" />}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-sm">{notification.title}</p>
                    <p className="text-xs text-muted-foreground">{notification.message}</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {new Date(notification.created_at).toLocaleString()}
                    </p>
                  </div>
                  {!notification.is_read && (
                    <div className="w-2 h-2 bg-violet-500 rounded-full flex-shrink-0 mt-1" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
