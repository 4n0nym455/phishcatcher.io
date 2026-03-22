/**
 * oauthService
 *
 * Manages the Google OAuth popup flow.
 * Replaces both oauthManager.js and the old oauthService.js.
 *
 * State is stored in sessionStorage (survives the popup redirect, cleared after use).
 * The popup posts typed messages to the opener; the opener acts on them.
 */

import { authApi } from '@/lib/api';

const STATE_KEY   = 'pc_oauth_state';
const EXPIRY_KEY  = 'pc_oauth_expiry';
const TTL_MS      = 10 * 60 * 1000; // 10 minutes

class OAuthService {
  // ── State management ────────────────────────────────────────────────────────

  saveState(state) {
    sessionStorage.setItem(STATE_KEY,  state);
    sessionStorage.setItem(EXPIRY_KEY, (Date.now() + TTL_MS).toString());
  }

  loadState() {
    const state  = sessionStorage.getItem(STATE_KEY);
    const expiry = parseInt(sessionStorage.getItem(EXPIRY_KEY) ?? '0', 10);
    if (!state || Date.now() > expiry) { this.clearState(); return null; }
    return state;
  }

  clearState() {
    sessionStorage.removeItem(STATE_KEY);
    sessionStorage.removeItem(EXPIRY_KEY);
  }

  // ── Popup helpers ────────────────────────────────────────────────────────────

  openPopup(url) {
    return window.open(url, 'google-oauth',
      'width=500,height=620,scrollbars=yes,resizable=yes,toolbar=no,menubar=no');
  }

  /** Called from GoogleCallbackPage to notify opener */
  sendMessageToParent(data) {
    if (window.opener && !window.opener.closed) {
      window.opener.postMessage({ ...data, _pc: true }, window.location.origin);
      return true;
    }
    return false;
  }

  /** Call from GoogleCallbackPage after posting message */
  closePopup(delayMs = 800) {
    setTimeout(() => window.close(), delayMs);
  }

  // ── Main entry point ────────────────────────────────────────────────────────

  /**
   * Opens the Google OAuth popup and waits for the result.
   *
   * Resolves with one of:
   *   { success: true, access_token, refresh_token, user }
   *   { activation_required: true, email, full_name, message }
   *   { requiresMFA: true, mfa_session_token, user }
   *
   * Rejects with an Error on failure or timeout.
   */
  initiateGoogleOAuth() {
    return new Promise(async (resolve, reject) => {
      // Get auth URL + state from backend
      let authData;
      try {
        authData = await authApi.getGoogleAuthUrl();
      } catch (err) {
        return reject(err);
      }

      this.saveState(authData.state);

      const popup = this.openPopup(authData.auth_url);
      if (!popup) {
        this.clearState();
        return reject(new Error('Popup blocked. Please allow pop-ups for this site.'));
      }

      let done = false;

      const cleanup = () => {
        done = true;
        clearInterval(popupWatcher);
        clearTimeout(timer);
        window.removeEventListener('message', onMessage);
        this.clearState();
      };

      const onMessage = (event) => {
        if (event.origin !== window.location.origin) return;
        const msg = event.data;
        if (!msg?._pc) return; // not our message

        cleanup();

        switch (msg.type) {
          case 'GOOGLE_AUTH_SUCCESS':
            return resolve({
              success:       true,
              access_token:  msg.access_token,
              refresh_token: msg.refresh_token,
              user:          msg.user,
            });

          case 'GOOGLE_AUTH_MFA':
            return resolve({
              requiresMFA:      true,
              mfa_session_token: msg.mfa_session_token,
              user:              msg.user,
            });

          case 'GOOGLE_AUTH_ACTIVATION':
            return resolve({
              activation_required: true,
              email:     msg.email,
              full_name: msg.full_name,
              message:   msg.message,
            });

          case 'GOOGLE_AUTH_ERROR':
          default:
            return reject(new Error(msg.error ?? 'Authentication failed'));
        }
      };

      window.addEventListener('message', onMessage);

      // Poll for popup being closed without posting a message
      const popupWatcher = setInterval(() => {
        if (popup.closed && !done) {
          cleanup();
          reject(new Error('Sign-in cancelled'));
        }
      }, 800);

      // Overall timeout (5 minutes)
      const timer = setTimeout(() => {
        if (!done) {
          cleanup();
          popup.close();
          reject(new Error('Sign-in timed out. Please try again.'));
        }
      }, 5 * 60 * 1000);
    });
  }
}

export const oauthService = new OAuthService();