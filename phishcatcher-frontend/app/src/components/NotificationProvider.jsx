import { createContext, useContext, useEffect, useState } from 'react';
import notificationService from '../services/notificationService';

const NotificationContext = createContext({
  isSupported: false,
  isSubscribed: false,
  permission: 'default',
  isLoading: false,
  subscribe: async () => {},
  unsubscribe: async () => {},
  requestPermission: async () => {},
});

export function NotificationProvider({ children }) {
  const [isSupported, setIsSupported] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [permission, setPermission] = useState('default');
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Check if notifications are supported
    setIsSupported(notificationService.isSupported);
    
    // Check current permission
    if ('Notification' in window) {
      setPermission(Notification.permission);
    }
    
    // Register service worker
    initializeNotifications();
  }, []);

  const initializeNotifications = async () => {
    if (!notificationService.isSupported) return;
    
    // Prevent duplicate service worker registration
    if (navigator.serviceWorker.controller) {
      console.log('Service Worker already registered');
      return;
    }
    
    try {
      const registration = await notificationService.registerServiceWorker();
      if (registration) {
        // Check for existing subscription
        const subscription = await registration.pushManager.getSubscription();
        setIsSubscribed(!!subscription);
      }
    } catch (error) {
      console.error('Failed to initialize notifications:', error);
    }
  };

  const requestPermission = async () => {
    if (!isSupported) return false;
    
    setIsLoading(true);
    try {
      const granted = await notificationService.requestPermission();
      setPermission(granted ? 'granted' : 'denied');
      return granted;
    } catch (error) {
      console.error('Permission request failed:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const subscribe = async () => {
    if (!isSupported || permission !== 'granted') return false;
    
    setIsLoading(true);
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await notificationService.subscribeToPush(registration);
      
      if (subscription) {
        // Send subscription to backend
        const success = await notificationService.sendSubscriptionToBackend(subscription);
        if (success) {
          setIsSubscribed(true);
          return true;
        }
      }
      return false;
    } catch (error) {
      console.error('Subscription failed:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const unsubscribe = async () => {
    if (!isSupported) return false;
    
    setIsLoading(true);
    try {
      await notificationService.unsubscribe();
      setIsSubscribed(false);
      
      // Remove subscription from backend
      await fetch('/api/notifications/unsubscribe', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      return true;
    } catch (error) {
      console.error('Unsubscribe failed:', error);
      return false;
    } finally {
      setIsLoading(false);
    }
  };

  const value = {
    isSupported,
    isSubscribed,
    permission,
    isLoading,
    subscribe,
    unsubscribe,
    requestPermission,
  };

  return (
    <NotificationContext.Provider value={value}>
      {children}
    </NotificationContext.Provider>
  );
}

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};
