/**
 * GoogleCallbackPage.jsx
 * Runs inside the OAuth popup window ONLY.
 * Exchanges code+state with the backend, then posts a typed message to the opener.
 * The opener (LoginPage) calls loginWithTokens() after receiving GOOGLE_AUTH_SUCCESS.
 *
 * Messages posted to opener:
 *   GOOGLE_AUTH_SUCCESS    → { access_token, refresh_token, user }
 *   GOOGLE_AUTH_MFA        → { mfa_session_token, user }
 *   GOOGLE_AUTH_ACTIVATION → { email, full_name, message }
 *   GOOGLE_AUTH_ERROR      → { error: string }
 */

import { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Loader2, AlertTriangle } from 'lucide-react';
import { authApi } from '@/lib/api';
import { oauthService } from '@/lib/oauthService';

export default function GoogleCallbackPage() {
  const [params]  = useSearchParams();
  const processed = useRef(false);

  const code  = params.get('code');
  const state = params.get('state');
  const error = params.get('error');   // e.g. "access_denied"

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;

    (async () => {
      // User cancelled or Google returned an error
      if (error) {
        oauthService.sendMessageToParent({ type: 'GOOGLE_AUTH_ERROR', error });
        oauthService.closePopup(1200);
        return;
      }

      if (!code || !state) {
        oauthService.sendMessageToParent({ type: 'GOOGLE_AUTH_ERROR', error: 'missing_params' });
        oauthService.closePopup(1200);
        return;
      }

      try {
        const data = await authApi.googleCallback(code, state);

        if (data.activation_required) {
          oauthService.sendMessageToParent({
            type:      'GOOGLE_AUTH_ACTIVATION',
            email:     data.email,
            full_name: data.full_name,
            message:   data.message,
          });
        } else if (data.mfa_required) {
          oauthService.sendMessageToParent({
            type:              'GOOGLE_AUTH_MFA',
            mfa_session_token: data.mfa_session_token,
            user:              data.user,
          });
        } else if (data.access_token) {
          oauthService.sendMessageToParent({
            type:          'GOOGLE_AUTH_SUCCESS',
            access_token:  data.access_token,
            refresh_token: data.refresh_token,
            user:          data.user,
          });
        } else {
          throw new Error('Unexpected response from server');
        }
      } catch (err) {
        oauthService.sendMessageToParent({
          type:  'GOOGLE_AUTH_ERROR',
          error: err.message ?? 'Authentication failed',
        });
      } finally {
        oauthService.closePopup(600);
      }
    })();
  }, []); // run once

  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ background: 'var(--bg-base)' }}
    >
      <div className="max-w-sm w-full text-center animate-fade-in">
        <div className="w-14 h-14 rounded-2xl overflow-hidden flex items-center justify-center mx-auto mb-5"
          style={{ background: 'var(--brand-dim)' }}>
          <img src="/phishcatcher.png" alt="PhishCatcher" className="w-12 h-12 object-contain" />
        </div>

        {error ? (
          <>
            <div className="w-10 h-10 rounded-xl flex items-center justify-center mx-auto mb-4"
              style={{ background: 'var(--danger-dim)', color: 'var(--danger)' }}>
              <AlertTriangle className="w-5 h-5" />
            </div>
            <p className="font-600 mb-1" style={{ color: 'var(--text-primary)' }}>Sign-in cancelled</p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Closing window…</p>
          </>
        ) : (
          <>
            <Loader2 className="w-6 h-6 animate-spin mx-auto mb-4" style={{ color: 'var(--brand)' }} />
            <p className="font-600 mb-1" style={{ color: 'var(--text-primary)' }}>Completing sign-in…</p>
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
              This window will close automatically.
            </p>
          </>
        )}
      </div>
    </div>
  );
}
