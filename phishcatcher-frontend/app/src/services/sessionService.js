/**
 * Session Management Service
 * 
 * Handles session monitoring, inactivity detection, and automatic logout.
 */

class SessionService {
  constructor() {
    this.sessionInfo = null;
    this.inactivityTimer = null;
    this.sessionCheckInterval = null;
    this.warningShown = false;
    this.listeners = new Set();
    
    // Session limits
    this.INACTIVITY_LIMIT_MINUTES = 20;
    this.SESSION_LIMIT_HOURS = 2;
    this.WARNING_MINUTES = 5; // Show warning 5 minutes before expiration
    
    // Event handlers
    this.handleActivity = this.handleActivity.bind(this);
    this.handleVisibilityChange = this.handleVisibilityChange.bind(this);
    this.handleStorageChange = this.handleStorageChange.bind(this);
  }
  
  /**
   * Initialize session monitoring
   */
  async initialize() {
    try {
      // Get initial session status
      await this.updateSessionStatus();
      
      // Start activity monitoring
      this.startActivityMonitoring();
      
      // Start periodic session checks
      this.startSessionChecks();
      
      // Setup cross-tab communication
      this.setupCrossTabCommunication();
      
      console.log('Session service initialized');
    } catch (error) {
      console.error('Failed to initialize session service:', error);
    }
  }
  
  /**
   * Start monitoring user activity
   */
  startActivityMonitoring() {
    // Track user activity events
    const activityEvents = [
      'mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'
    ];
    
    activityEvents.forEach(event => {
      document.addEventListener(event, this.handleActivity, true);
    });
    
    // Handle page visibility changes
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
    
    // Handle storage changes (cross-tab sync)
    window.addEventListener('storage', this.handleStorageChange);
  }
  
  /**
   * Handle user activity
   */
  async handleActivity() {
    // Reset inactivity timer
    this.resetInactivityTimer();
    
    // Update last activity in storage
    localStorage.setItem('lastActivity', Date.now().toString());
    
    // Trigger activity update to server
    await this.updateActivity();
  }
  
  /**
   * Handle page visibility changes
   */
  handleVisibilityChange() {
    if (document.visibilityState === 'visible') {
      // Page became visible, check session status
      this.checkSessionStatus();
    }
  }
  
  /**
   * Handle storage changes (cross-tab communication)
   */
  handleStorageChange(event) {
    if (event.key === 'sessionActivity') {
      // Another tab updated activity
      this.resetInactivityTimer();
    } else if (event.key === 'sessionLogout') {
      // Another tab logged out
      this.handleLogout('Session expired in another tab');
    }
  }
  
  /**
   * Setup cross-tab communication
   */
  setupCrossTabCommunication() {
    // Notify other tabs of activity
    setInterval(() => {
      localStorage.setItem('sessionActivity', Date.now().toString());
    }, 30000); // Every 30 seconds
  }
  
  /**
   * Start periodic session checks
   */
  startSessionChecks() {
    // Check session every 2 minutes
    this.sessionCheckInterval = setInterval(() => {
      this.checkSessionStatus();
    }, 2 * 60 * 1000);
  }
  
  /**
   * Reset inactivity timer
   */
  resetInactivityTimer() {
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
    }
    
    // Set timer for inactivity warning
    this.inactivityTimer = setTimeout(() => {
      this.showInactivityWarning();
    }, (this.INACTIVITY_LIMIT_MINUTES - this.WARNING_MINUTES) * 60 * 1000);
    
    // Hide warning if it was shown
    this.warningShown = false;
    this.hideInactivityWarning();
  }
  
  /**
   * Show inactivity warning
   */
  showInactivityWarning() {
    if (this.warningShown) return;
    
    this.warningShown = true;
    this.notifyListeners('sessionWarning', {
      type: 'inactivity',
      minutesRemaining: this.WARNING_MINUTES
    });
    
    // Show browser notification if permitted
    if (Notification.permission === 'granted') {
      new Notification('Session Expiring Soon', {
        body: `Your session will expire in ${this.WARNING_MINUTES} minutes due to inactivity.`,
        icon: '/favicon.ico'
      });
    }
    
    // Auto logout after warning period
    setTimeout(() => {
      this.handleLogout('Session expired due to inactivity');
    }, this.WARNING_MINUTES * 60 * 1000);
  }
  
  /**
   * Hide inactivity warning
   */
  hideInactivityWarning() {
    this.notifyListeners('sessionWarning', null);
  }
  
  /**
   * Update session status from server
   */
  async updateSessionStatus() {
    try {
      const response = await fetch('/api/v1/session/status', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (response.ok) {
        this.sessionInfo = await response.json();
        this.notifyListeners('sessionUpdate', this.sessionInfo);
        return this.sessionInfo;
      } else if (response.status === 401) {
        const error = await response.json();
        this.handleLogout(error.detail || 'Session expired');
        return null;
      }
    } catch (error) {
      console.error('Failed to update session status:', error);
    }
    
    return null;
  }
  
  /**
   * Check session validity
   */
  async checkSessionStatus() {
    try {
      const response = await fetch('/api/v1/session/validate', {
        method: 'GET',
        credentials: 'include'
      });
      
      if (response.ok) {
        const result = await response.json();
        
        if (!result.valid) {
          this.handleLogout(result.reason || 'Session invalid');
          return false;
        }
        
        // Check if session is about to expire
        if (result.session && result.session.remaining_inactivity_minutes <= this.WARNING_MINUTES) {
          this.showInactivityWarning();
        }
        
        return true;
      } else if (response.status === 401) {
        this.handleLogout('Session expired');
        return false;
      }
    } catch (error) {
      console.error('Failed to check session status:', error);
    }
    
    return false;
  }
  
  /**
   * Update activity on server
   */
  async updateActivity() {
    try {
      await fetch('/api/v1/session/extend', {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      console.error('Failed to update activity:', error);
    }
  }
  
  /**
   * Extend session
   */
  async extendSession() {
    try {
      const response = await fetch('/api/v1/session/extend', {
        method: 'POST',
        credentials: 'include'
      });
      
      if (response.ok) {
        const result = await response.json();
        this.sessionInfo = result.session;
        this.resetInactivityTimer();
        this.notifyListeners('sessionExtended', result);
        return true;
      }
    } catch (error) {
      console.error('Failed to extend session:', error);
    }
    
    return false;
  }
  
  /**
   * Handle logout
   */
  handleLogout(reason = 'Session expired') {
    // Clear timers
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
    }
    if (this.sessionCheckInterval) {
      clearInterval(this.sessionCheckInterval);
    }
    
    // Remove event listeners
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    window.removeEventListener('storage', this.handleStorageChange);
    
    // Notify other tabs
    localStorage.setItem('sessionLogout', Date.now().toString());
    
    // Clear session data
    this.sessionInfo = null;
    localStorage.removeItem('lastActivity');
    
    // Notify listeners
    this.notifyListeners('sessionExpired', { reason });
    
    // Redirect to login after a short delay
    setTimeout(() => {
      window.location.href = '/login';
    }, 2000);
  }
  
  /**
   * Manual logout
   */
  async logout() {
    try {
      await fetch('/api/v1/session/logout', {
        method: 'POST',
        credentials: 'include'
      });
    } catch (error) {
      console.error('Failed to logout:', error);
    }
    
    this.handleLogout('Manual logout');
  }
  
  /**
   * Add event listener
   */
  addListener(event, callback) {
    this.listeners.add({ event, callback });
  }
  
  /**
   * Remove event listener
   */
  removeListener(event, callback) {
    this.listeners.forEach(listener => {
      if (listener.event === event && listener.callback === callback) {
        this.listeners.delete(listener);
      }
    });
  }
  
  /**
   * Notify all listeners
   */
  notifyListeners(event, data) {
    this.listeners.forEach(listener => {
      if (listener.event === event) {
        try {
          listener.callback(data);
        } catch (error) {
          console.error('Error in session listener:', error);
        }
      }
    });
  }
  
  /**
   * Get current session info
   */
  getSessionInfo() {
    return this.sessionInfo;
  }
  
  /**
   * Check if session is active
   */
  isSessionActive() {
    return this.sessionInfo && this.sessionInfo.session_active;
  }
  
  /**
   * Destroy session service
   */
  destroy() {
    // Clear timers
    if (this.inactivityTimer) {
      clearTimeout(this.inactivityTimer);
    }
    if (this.sessionCheckInterval) {
      clearInterval(this.sessionCheckInterval);
    }
    
    // Remove event listeners
    const activityEvents = [
      'mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart', 'click'
    ];
    
    activityEvents.forEach(event => {
      document.removeEventListener(event, this.handleActivity, true);
    });
    
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
    window.removeEventListener('storage', this.handleStorageChange);
    
    // Clear listeners
    this.listeners.clear();
  }
}

// Create singleton instance
const sessionService = new SessionService();

export default sessionService;
