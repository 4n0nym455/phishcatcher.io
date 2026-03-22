/**
 * OAuth State Manager
 * Handles secure OAuth state management with expiration and cleanup
 */

class OAuthStateManager {
  constructor() {
    this.STATE_KEY = 'oauth_state';
    this.STATE_EXPIRY_KEY = 'oauth_state_expiry';
    this.STATE_PREFIX = 'oauth_';
    this.STATE_EXPIRY_TIME = 10 * 60 * 1000; // 10 minutes
  }

  /**
   * Generate a secure OAuth state
   */
  generateState() {
    // Clear any existing expired states
    this.cleanupExpiredStates();
    
    // Generate new state with timestamp
    const timestamp = Date.now();
    const randomString = this.generateRandomString(32);
    const state = `${this.STATE_PREFIX}${timestamp}_${randomString}`;
    
    // Store state with expiry
    this.setState(state);
    
    return state;
  }

  /**
   * Store OAuth state with expiry
   */
  setState(state) {
    const expiry = Date.now() + this.STATE_EXPIRY_TIME;
    localStorage.setItem(this.STATE_KEY, state);
    localStorage.setItem(this.STATE_EXPIRY_KEY, expiry.toString());
    // Also store in sessionStorage for popup access
    sessionStorage.setItem(this.STATE_KEY, state);
    sessionStorage.setItem(this.STATE_EXPIRY_KEY, expiry.toString());
  }

  /**
   * Validate OAuth state
   */
  validateState(receivedState) {
    // Check sessionStorage first (for popup windows), then localStorage
    let storedState = sessionStorage.getItem(this.STATE_KEY);
    let storedExpiry = sessionStorage.getItem(this.STATE_EXPIRY_KEY);
    
    if (!storedState) {
      storedState = localStorage.getItem(this.STATE_KEY);
      storedExpiry = localStorage.getItem(this.STATE_EXPIRY_KEY);
    }
    
    if (!storedState) {
      return { valid: false, error: 'No stored state found' };
    }
    
    if (storedState !== receivedState) {
      return { valid: false, error: 'State mismatch' };
    }
    
    // Check if state has expired
    if (storedExpiry && Date.now() > parseInt(storedExpiry)) {
      this.clearState();
      return { valid: false, error: 'State expired' };
    }
    
    return { valid: true };
  }

  /**
   * Get stored state
   */
  getState() {
    // Check sessionStorage first, then localStorage
    let state = sessionStorage.getItem(this.STATE_KEY);
    if (!state) {
      state = localStorage.getItem(this.STATE_KEY);
    }
    return state;
  }

  /**
   * Clear OAuth state
   */
  clearState() {
    localStorage.removeItem(this.STATE_KEY);
    localStorage.removeItem(this.STATE_EXPIRY_KEY);
    sessionStorage.removeItem(this.STATE_KEY);
    sessionStorage.removeItem(this.STATE_EXPIRY_KEY);
  }

  /**
   * Clean up expired states
   */
  cleanupExpiredStates() {
    // Check localStorage expiry
    const localExpiry = localStorage.getItem(this.STATE_EXPIRY_KEY);
    if (localExpiry && Date.now() > parseInt(localExpiry)) {
      this.clearState();
      return;
    }
    
    // Check sessionStorage expiry
    const sessionExpiry = sessionStorage.getItem(this.STATE_EXPIRY_KEY);
    if (sessionExpiry && Date.now() > parseInt(sessionExpiry)) {
      this.clearState();
      return;
    }
  }

  /**
   * Generate cryptographically secure random string
   */
  generateRandomString(length) {
    const array = new Uint8Array(length);
    crypto.getRandomValues(array);
    return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
  }

  /**
   * Check if there's an active OAuth flow
   */
  hasActiveFlow() {
    this.cleanupExpiredStates();
    // Check both localStorage and sessionStorage
    return !!(this.getState());
  }
}

// Export singleton instance
export const oauthManager = new OAuthStateManager();
