/**
 * Session Status Component
 * 
 * Displays session information and handles session expiration warnings.
 */

import React, { useState, useEffect } from 'react';
import { Clock, AlertTriangle, LogOut, RefreshCw } from 'lucide-react';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import sessionService from '../services/sessionService';

const SessionStatus = () => {
  const [sessionInfo, setSessionInfo] = useState(null);
  const [warning, setWarning] = useState(null);
  const [countdown, setCountdown] = useState(null);
  const [showDetails, setShowDetails] = useState(false);

  useEffect(() => {
    // Initialize session service
    sessionService.initialize();

    // Add event listeners
    const handleSessionUpdate = (info) => {
      setSessionInfo(info);
    };

    const handleSessionWarning = (warningData) => {
      setWarning(warningData);
      if (warningData) {
        startCountdown(warningData.minutesRemaining);
      } else {
        setCountdown(null);
      }
    };

    const handleSessionExpired = (data) => {
      setSessionInfo(null);
      setWarning(null);
      setCountdown(null);
    };

    const handleSessionExtended = (data) => {
      setWarning(null);
      setCountdown(null);
    };

    sessionService.addListener('sessionUpdate', handleSessionUpdate);
    sessionService.addListener('sessionWarning', handleSessionWarning);
    sessionService.addListener('sessionExpired', handleSessionExpired);
    sessionService.addListener('sessionExtended', handleSessionExtended);

    // Get initial session info
    sessionService.updateSessionStatus();

    // Cleanup
    return () => {
      sessionService.removeListener('sessionUpdate', handleSessionUpdate);
      sessionService.removeListener('sessionWarning', handleSessionWarning);
      sessionService.removeListener('sessionExpired', handleSessionExpired);
      sessionService.removeListener('sessionExtended', handleSessionExtended);
    };
  }, []);

  const startCountdown = (minutes) => {
    let remainingSeconds = minutes * 60;
    
    const interval = setInterval(() => {
      remainingSeconds--;
      
      if (remainingSeconds <= 0) {
        clearInterval(interval);
        setCountdown('Expired');
      } else {
        const mins = Math.floor(remainingSeconds / 60);
        const secs = remainingSeconds % 60;
        setCountdown(`${mins}:${secs.toString().padStart(2, '0')}`);
      }
    }, 1000);
  };

  const handleExtendSession = async () => {
    const extended = await sessionService.extendSession();
    if (extended) {
      // Session extended successfully
    }
  };

  const handleLogout = async () => {
    await sessionService.logout();
  };

  const formatTimeRemaining = (minutes) => {
    if (minutes <= 0) return 'Expired';
    if (minutes < 60) return `${minutes}m`;
    
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    return `${hours}h ${remainingMinutes}m`;
  };

  if (!sessionInfo) {
    return null;
  }

  const { session, user } = sessionInfo;

  return (
    <div className="relative">
      {/* Session Status Indicator */}
      <div className="flex items-center gap-2 p-2 bg-violet-500/10 rounded-lg border border-violet-500/20">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-violet-400" />
          <span className="text-sm text-violet-300">
            {user?.email}
          </span>
        </div>
        
        {/* Session Time Remaining */}
        <div className="flex items-center gap-2">
          {session && (
            <Badge 
              variant={session.remaining_inactivity_minutes <= 5 ? "destructive" : "secondary"}
              className="text-xs"
            >
              {formatTimeRemaining(session.remaining_inactivity_minutes)}
            </Badge>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowDetails(!showDetails)}
            className="text-violet-400 hover:text-violet-300"
          >
            <Clock className="w-4 h-4" />
          </Button>
          
          <Button
            variant="ghost"
            size="sm"
            onClick={handleLogout}
            className="text-red-400 hover:text-red-300"
          >
            <LogOut className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Session Warning */}
      {warning && (
        <div className="absolute top-full right-0 mt-2 w-80 bg-red-500/10 border border-red-500/20 rounded-lg p-4 z-50">
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-medium text-red-400">
                Session Expiring Soon
              </h4>
              <p className="text-xs text-red-300 mt-1">
                Your session will expire in {warning.minutesRemaining} minutes due to inactivity.
              </p>
              {countdown && (
                <div className="mt-2">
                  <Badge variant="destructive" className="text-xs">
                    {countdown}
                  </Badge>
                </div>
              )}
              <div className="flex gap-2 mt-3">
                <Button
                  size="sm"
                  onClick={handleExtendSession}
                  className="bg-red-500 hover:bg-red-600"
                >
                  <RefreshCw className="w-3 h-3 mr-1" />
                  Extend Session
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleLogout}
                  className="border-red-500/20 text-red-400 hover:bg-red-500/10"
                >
                  Logout Now
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Session Details */}
      {showDetails && (
        <div className="absolute top-full right-0 mt-2 w-96 bg-violet-500/10 border border-violet-500/20 rounded-lg p-4 z-40">
          <div className="space-y-3">
            <div>
              <h4 className="text-sm font-medium text-violet-300">Session Information</h4>
              <div className="mt-2 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-violet-400">User:</span>
                  <span className="text-white">{user?.email}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-violet-400">Session Started:</span>
                  <span className="text-white">
                    {new Date(session?.created_at).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-violet-400">Last Activity:</span>
                  <span className="text-white">
                    {new Date(session?.last_activity).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-violet-400">Session Expires:</span>
                  <span className="text-white">
                    {new Date(session?.expires_at).toLocaleString()}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-violet-400">Inactivity Timeout:</span>
                  <span className="text-white">
                    {new Date(session?.inactivity_expires_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-violet-500/20">
              <h4 className="text-sm font-medium text-violet-300 mb-2">Time Remaining</h4>
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-xs text-violet-400">Session Duration:</span>
                  <Badge 
                    variant={session.remaining_session_minutes <= 30 ? "destructive" : "secondary"}
                    className="text-xs"
                  >
                    {formatTimeRemaining(session.remaining_session_minutes)}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-violet-400">Inactivity Timeout:</span>
                  <Badge 
                    variant={session.remaining_inactivity_minutes <= 5 ? "destructive" : "secondary"}
                    className="text-xs"
                  >
                    {formatTimeRemaining(session.remaining_inactivity_minutes)}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-xs text-violet-400">Last Activity:</span>
                  <span className="text-xs text-white">
                    {session.last_activity_minutes_ago} minutes ago
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-3 border-t border-violet-500/20">
              <div className="flex gap-2">
                <Button
                  size="sm"
                  onClick={handleExtendSession}
                  className="bg-violet-500 hover:bg-violet-600"
                >
                  <RefreshCw className="w-3 h-3 mr-1" />
                  Extend Session
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={handleLogout}
                  className="border-violet-500/20 text-violet-400 hover:bg-violet-500/10"
                >
                  <LogOut className="w-3 h-3 mr-1" />
                  Logout
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionStatus;
