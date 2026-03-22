/**
 * OAuth Service
 * Handles Google OAuth flow with comprehensive error handling and retry logic
 */

import { oauthManager } from './oauthManager';
import { authApi } from './api';

class OAuthService {
  constructor() {
    this.POPUP_CONFIG = {
      width: 500,
      height: 600,
      scrollbars: 'yes',
      resizable: 'yes',
      status: 'no',
      toolbar: 'no',
      menubar: 'no',
      directories: 'no'
    };
    
    this.POPUP_TIMEOUT = 5 * 60 * 1000; // 5 minutes
    this.RETRY_ATTEMPTS = 3;
    this.RETRY_DELAY = 1000; // 1 second
    
    // Track processed authorization codes to prevent duplicate API calls
    this.processedCodes = new Set();
  }

  /**
   * Initiate Google OAuth flow
   */
  async initiateGoogleOAuth() {
    try {
      // Check for existing active flow
      if (oauthManager.hasActiveFlow()) {
        oauthManager.clearState();
      }

      // Get OAuth URL from backend
      const response = await authApi.getGoogleAuthUrl();
      const { auth_url, state } = response;

      if (!auth_url || !state) {
        throw new Error('Invalid OAuth response from server');
      }

      // Store state in localStorage
      oauthManager.setState(state);

      // Open popup
      const popup = this.openPopup(auth_url);

      if (!popup) {
        throw new Error('Failed to open OAuth popup. Please check your popup blocker settings.');
      }

      // Send state to popup via postMessage after it loads
      setTimeout(() => {
        if (popup && !popup.closed) {
          popup.postMessage({ type: 'OAUTH_STATE', state }, window.location.origin);
        }
      }, 1000);

      // Handle OAuth flow
      return await this.handleOAuthFlow(popup, state);

    } catch (error) {
      oauthManager.clearState();
      throw error;
    }
  }

  /**
   * Open OAuth popup
   */
  openPopup(url) {
    const popupConfig = Object.entries(this.POPUP_CONFIG)
      .map(([key, value]) => `${key}=${value}`)
      .join(',');

    const popup = window.open(url, 'google-oauth', popupConfig);
    
    // Check if popup was blocked
    if (!popup || popup.closed || typeof popup.closed === 'undefined') {
      return null;
    }

    return popup;
  }

  /**
   * Handle OAuth flow with popup
   */
  async handleOAuthFlow(popup, expectedState) {
    return new Promise((resolve, reject) => {
      let timeoutId;
      let retryCount = 0;

      const cleanup = () => {
        if (timeoutId) clearTimeout(timeoutId);
        window.removeEventListener('message', messageHandler);
        clearInterval(popupChecker);
      };

      const messageHandler = async (event) => {
        // Verify origin for security
        if (event.origin !== window.location.origin) return;

        // Handle state request from popup
        if (event.data.type === 'REQUEST_OAUTH_STATE') {
          popup.postMessage({ type: 'OAUTH_STATE', state: expectedState }, window.location.origin);
          return;
        }

        try {
          const result = await this.processOAuthMessage(event.data, expectedState);
          
          // If result is null, it means this message should be ignored (e.g., React DevTools)
          if (result === null) {
            return; // Don't resolve or reject, just ignore this message
          }
          
          cleanup();
          resolve(result);
        } catch (error) {
          
          // Retry logic for certain errors
          if (this.shouldRetry(error) && retryCount < this.RETRY_ATTEMPTS) {
            retryCount++;
            setTimeout(() => {
              popup.focus();
            }, this.RETRY_DELAY * retryCount);
            return;
          }

          cleanup();
          reject(error);
        }
      };

      const popupChecker = setInterval(() => {
        if (popup.closed) {
          cleanup();
          reject(new Error('OAuth popup was closed before authentication completed'));
        }
      }, 1000);

      // Set timeout
      timeoutId = setTimeout(() => {
        cleanup();
        popup.close();
        reject(new Error('OAuth flow timed out. Please try again.'));
      }, this.POPUP_TIMEOUT);

      // Add message listener
      window.addEventListener('message', messageHandler);
    });
  }

  /**
   * Process OAuth message from popup
   */
  async processOAuthMessage(message, expectedState) {
    // Filter out non-OAuth messages (like React DevTools messages)
    if (typeof message === 'object' && message !== null) {
      // Ignore React DevTools and other development messages
      if (message.source === 'react-devtools-content-script' || 
          message.source === 'react-devtools-bridge' ||
          message.hello === true) {
        console.log('🔍 Ignoring non-OAuth message:', message);
        return null; // Return null to indicate this message should be ignored
      }
      
      const messageType = message.type || message.message;
      console.log('🔍 Processing OAuth message object:', message);
      
      switch (messageType) {
        case 'google-auth-success':
          return { success: true, message: 'Authentication successful' };
        
        case 'google-auth-mfa-required':
          return { 
            success: false, 
            requiresMFA: true, 
            message: 'Multi-factor authentication required' 
          };
        
        case 'google-auth-activation-required':
          // Get activation info from localStorage
          const activationInfo = localStorage.getItem('pending_activation');
          localStorage.removeItem('pending_activation'); // Clean up
          
          if (activationInfo) {
            const info = JSON.parse(activationInfo);
            return {
              success: false,
              activation_required: true,
              email: info.email,
              full_name: info.full_name,
              message: info.message
            };
          } else {
            return {
              success: false,
              activation_required: true,
              message: 'Please check your email for activation instructions'
            };
          }
        
        case 'google-auth-error':
          throw new Error('Authentication failed');
        
        default:
          console.error('❌ Unknown OAuth message object:', message);
          throw new Error(`Unknown OAuth message: ${JSON.stringify(message)}`);
      }
    }
    
    // Handle case where message is a string (legacy support)
    switch (message) {
      case 'google-auth-success':
        return { success: true, message: 'Authentication successful' };
      
      case 'google-auth-mfa-required':
        return { 
          success: false, 
          requiresMFA: true, 
          message: 'Multi-factor authentication required' 
        };
      
      case 'google-auth-activation-required':
        // Get activation info from localStorage
        const activationInfo = localStorage.getItem('pending_activation');
        localStorage.removeItem('pending_activation'); // Clean up
        
        if (activationInfo) {
          const info = JSON.parse(activationInfo);
          return {
            success: false,
            activation_required: true,
            email: info.email,
            full_name: info.full_name,
            message: info.message
          };
        } else {
          return {
            success: false,
            activation_required: true,
            message: 'Please check your email for activation instructions'
          };
        }
      
      case 'google-auth-error':
        throw new Error('Authentication failed');
      
      default:
        console.error('❌ Unknown OAuth message string:', message);
        throw new Error(`Unknown OAuth message: ${message}`);
    }
  }

  /**
   * Determine if error should trigger retry
   */
  shouldRetry(error) {
    const retryableErrors = [
      'Network error',
      'Timeout',
      'Popup was closed'
    ];
    
    return retryableErrors.some(retryableError => 
      error.message.includes(retryableError)
    );
  }

  /**
   * Handle OAuth callback (called from popup)
   */
  async handleOAuthCallback(code, state) {
    try {
      console.log('🔄 oauthService.handleOAuthCallback started');
      console.log('⏰ Service timestamp:', new Date().toISOString());
      
      // Validate state
      if (!state) {
        throw new Error('No OAuth state provided - please initiate OAuth from the main window');
      }
      
      // Create a unique key for this code to prevent duplicate processing
      const codeKey = code.substring(0, 30); // Longer key for better uniqueness
      const timestamp = Date.now();
      const uniqueKey = `${codeKey}_${timestamp}`;
      
      console.log('🔍 OAuth processing attempt:', {
        codeLength: code.length,
        codeKey: codeKey,
        uniqueKey: uniqueKey,
        existingCodes: this.processedCodes ? Array.from(this.processedCodes) : []
      });
      
      // Check if we've already processed this code
      if (this.processedCodes && this.processedCodes.has(codeKey)) {
        console.error('❌ Duplicate OAuth code detected:', codeKey);
        throw new Error('Authorization code has already been used');
      }
      
      // Mark this code as being processed immediately
      if (!this.processedCodes) {
        this.processedCodes = new Set();
      }
      this.processedCodes.add(codeKey);
      
      console.log('✅ OAuth code marked as processed:', codeKey);

      console.log('🌐 About to call authApi.googleCallback...');
      
      // Exchange code for tokens with retry mechanism
      let response;
      try {
        response = await authApi.googleCallback(code, state);
      } catch (error) {
        // If code expired, try to refresh the OAuth flow
        if (error.message && error.message.includes('Authorization code is invalid or has expired')) {
          console.log('⚠️ OAuth code expired, attempting to restart OAuth flow...');
          
          // Clear the current state and restart OAuth
          oauthManager.clearState();
          
          // Remove this code from processed codes to allow retry
          if (this.processedCodes) {
            this.processedCodes.delete(codeKey);
          }
          
          throw new Error('Authorization code expired. Please try signing in again.');
        }
        throw error;
      }
      
      console.log('✅ authApi.googleCallback response:', response);
      
      // Clear state after successful exchange
      oauthManager.clearState();
      
      // Clean up processed codes after successful completion (keep for 5 minutes)
      setTimeout(() => {
        if (this.processedCodes) {
          this.processedCodes.delete(codeKey);
        }
      }, 5 * 60 * 1000);
      
      return response;

    } catch (error) {
      console.error('❌ oauthService.handleOAuthCallback error:', error);
      oauthManager.clearState();
      throw error;
    }
  }

  /**
   * Send message to parent window (called from popup)
   */
  sendMessageToParent(message) {
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage(message, window.location.origin);
      return true;
    }
    return false;
  }

  /**
   * Close popup and notify parent
   */
  closePopup(message, delay = 1000) {
    this.sendMessageToParent(message);
    setTimeout(() => {
      window.close();
    }, delay);
  }
}

// Export singleton instance
export const oauthService = new OAuthService();
