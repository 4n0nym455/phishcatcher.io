import { X, Shield, AlertTriangle, Info, CheckCircle } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Button } from './ui/button';

const notificationTypes = {
  security: {
    icon: Shield,
    className: 'border-rose-500 bg-rose-50 dark:bg-rose-950 text-rose-800 dark:text-rose-200',
    iconClassName: 'text-rose-500'
  },
  warning: {
    icon: AlertTriangle,
    className: 'border-amber-500 bg-amber-50 dark:bg-amber-950 text-amber-800 dark:text-amber-200',
    iconClassName: 'text-amber-500'
  },
  info: {
    icon: Info,
    className: 'border-blue-500 bg-blue-50 dark:bg-blue-950 text-blue-800 dark:text-blue-200',
    iconClassName: 'text-blue-500'
  },
  success: {
    icon: CheckCircle,
    className: 'border-emerald-500 bg-emerald-50 dark:bg-emerald-950 text-emerald-800 dark:text-emerald-200',
    iconClassName: 'text-emerald-500'
  }
};

export function NotificationToast({ notification, onClose }) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Animate in
    setIsVisible(true);
    
    // Auto-dismiss after 5 seconds
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onClose, 300);
    }, 5000);

    return () => clearTimeout(timer);
  }, [onClose]);

  const typeConfig = notificationTypes[notification.type] || notificationTypes.info;
  const Icon = typeConfig.icon;

  const handleClick = () => {
    if (notification.onClick) {
      notification.onClick();
    }
    setIsVisible(false);
    setTimeout(onClose, 300);
  };

  return (
    <div
      className={`
        fixed top-4 right-4 z-50 max-w-sm w-full
        transform transition-all duration-300 ease-in-out
        ${isVisible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}
      `}
    >
      <div
        className={`
          glass-card-strong p-4 rounded-lg border cursor-pointer
          hover:shadow-lg transition-shadow duration-200
          ${typeConfig.className}
        `}
        onClick={handleClick}
      >
        <div className="flex items-start gap-3">
          <Icon className={`h-5 w-5 flex-shrink-0 mt-0.5 ${typeConfig.iconClassName}`} />
          
          <div className="flex-1 min-w-0">
            <h4 className="font-semibold text-sm mb-1">
              {notification.title}
            </h4>
            <p className="text-sm opacity-90 line-clamp-2">
              {notification.message}
            </p>
            
            {notification.actions && (
              <div className="flex gap-2 mt-2">
                {notification.actions.map((action, index) => (
                  <Button
                    key={index}
                    size="sm"
                    variant={action.variant || 'outline'}
                    onClick={(e) => {
                      e.stopPropagation();
                      action.onClick();
                    }}
                    className="h-7 text-xs"
                  >
                    {action.label}
                  </Button>
                ))}
              </div>
            )}
          </div>

          <Button
            size="sm"
            variant="ghost"
            className="h-6 w-6 p-0 flex-shrink-0"
            onClick={(e) => {
              e.stopPropagation();
              setIsVisible(false);
              setTimeout(onClose, 300);
            }}
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      </div>
    </div>
  );
}

export function NotificationContainer({ notifications, onRemove }) {
  return (
    <div className="fixed top-0 right-0 z-50 p-4 space-y-2 pointer-events-none">
      {notifications.map((notification) => (
        <div key={notification.id} className="pointer-events-auto">
          <NotificationToast
            notification={notification}
            onClose={() => onRemove(notification.id)}
          />
        </div>
      ))}
    </div>
  );
}
