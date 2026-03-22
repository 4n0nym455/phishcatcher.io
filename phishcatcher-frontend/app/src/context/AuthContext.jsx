/**
 * AuthContext
 *
 * Single source of truth for authentication state.
 * Replaces the scattered localStorage + App.jsx state pattern.
 *
 * Lifecycle:
 *  1. On mount: check access_token → call /auth/me to hydrate user
 *  2. login()  : store tokens → dispatch auth:success → hydrate user
 *  3. logout() : call /auth/logout → clearTokens → reset state
 *  4. Any 401 that can't be refreshed dispatches 'auth:logout' → auto-logout
 */

import { createContext, useContext, useEffect, useReducer, useCallback } from 'react';
import { authApi, getTokens, storeTokens, clearTokens } from '@/lib/api';

// ─── State shape ──────────────────────────────────────────────────────────────

const INITIAL = {
  user:         null,   // UserResponse | null
  loading:      true,   // true while hydrating on mount
  isAuthenticated: false,
};

function reducer(state, action) {
  switch (action.type) {
    case 'HYDRATING':     return { ...state, loading: true };
    case 'AUTHENTICATED': return { ...state, loading: false, isAuthenticated: true,  user: action.user };
    case 'UNAUTHENTICATED': return { ...INITIAL, loading: false };
    case 'UPDATE_USER':   return { ...state, user: { ...state.user, ...action.patch } };
    default:              return state;
  }
}

// ─── Context ──────────────────────────────────────────────────────────────────

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, INITIAL);

  // ── Hydrate on mount ──────────────────────────────────────────────────────

  useEffect(() => {
    const hydrate = async () => {
      const { accessToken } = getTokens();
      if (!accessToken) {
        dispatch({ type: 'UNAUTHENTICATED' });
        return;
      }
      try {
        const user = await authApi.getMe();
        _persistUserMeta(user);
        dispatch({ type: 'AUTHENTICATED', user });
      } catch {
        clearTokens();
        dispatch({ type: 'UNAUTHENTICATED' });
      }
    };
    hydrate();
  }, []);

  // ── Listen for forced logout (401 that couldn't refresh) ─────────────────

  useEffect(() => {
    const handle = () => {
      clearTokens();
      dispatch({ type: 'UNAUTHENTICATED' });
    };
    window.addEventListener('auth:logout', handle);
    return () => window.removeEventListener('auth:logout', handle);
  }, []);

  // ── Public helpers ────────────────────────────────────────────────────────

  /**
   * Called after successful OTP verification or activation.
   * Accepts the full token response and fetches fresh user data.
   */
  const loginWithTokens = useCallback(async (tokenResponse) => {
    storeTokens(tokenResponse);
    const user = tokenResponse.user
      ? tokenResponse.user           // avoid an extra round-trip if already included
      : await authApi.getMe();
    _persistUserMeta(user);
    dispatch({ type: 'AUTHENTICATED', user });
    return user;
  }, []);

  const logout = useCallback(async () => {
    await authApi.logout();
    clearTokens();
    dispatch({ type: 'UNAUTHENTICATED' });
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      const user = await authApi.getMe();
      _persistUserMeta(user);
      dispatch({ type: 'AUTHENTICATED', user });
      return user;
    } catch {
      return null;
    }
  }, []);

  const patchUser = useCallback((patch) => {
    dispatch({ type: 'UPDATE_USER', patch });
  }, []);

  const value = {
    ...state,
    isAdmin:       state.user?.role === 'admin',
    loginWithTokens,
    logout,
    refreshUser,
    patchUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>');
  return ctx;
}

// ─── Internal helpers ─────────────────────────────────────────────────────────

/** Keep a few metadata keys in localStorage for Layout to read before hydration */
function _persistUserMeta(user) {
  if (!user) return;
  localStorage.setItem('phishcatcher_email', user.email ?? '');
  localStorage.setItem('phishcatcher_role',  user.role  ?? 'user');
  localStorage.setItem('phishcatcher_name',  user.full_name ?? '');
}