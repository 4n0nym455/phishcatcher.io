/**
 * Auth Zustand Store
 * 
 * Replaces AuthContext with a lighter, more flexible state container.
 * Persists auth tokens in localStorage via the api.js helpers.
 * 
 * Usage:
 *   const { user, loginWithTokens, logout } = useAuthStore();
 */

import { create } from 'zustand';
import { authApi, getTokens, storeTokens, clearTokens } from '@/lib/api';
import { queryClient, queryKeys } from '@/lib/queryClient';

const INITIAL = {
  user: null,
  loading: true,
  isAuthenticated: false,
};

export const useAuthStore = create((set, get) => ({
  ...INITIAL,

  /** Derived helper */
  get isAdmin() {
    return get().user?.role === 'admin';
  },

  /**
   * Hydrate user from stored token on app mount.
   * Call this once in <App> or a top-level effect.
   */
  hydrate: async () => {
    set({ loading: true });
    const { accessToken } = getTokens();
    if (!accessToken) {
      set({ ...INITIAL, loading: false });
      return;
    }
    try {
      const user = await authApi.getMe();
      _persistUserMeta(user);
      set({ user, loading: false, isAuthenticated: true });
    } catch {
      clearTokens();
      localStorage.removeItem('phishcatcher_email');
      localStorage.removeItem('phishcatcher_role');
      localStorage.removeItem('phishcatcher_name');
      localStorage.setItem('phishcatcher_logout_reason', 'session_expired');
      set({ ...INITIAL, loading: false });
    }
  },

  /**
   * Called after successful login (OTP verified or activation complete).
   * @param {Object} tokenResponse — { access_token, refresh_token, user? }
   */
  loginWithTokens: async (tokenResponse) => {
    storeTokens(tokenResponse);
    const user = tokenResponse.user
      ? tokenResponse.user
      : await authApi.getMe();
    _persistUserMeta(user);
    set({ user, loading: false, isAuthenticated: true });
    // Invalidate any stale cached queries
    queryClient.invalidateQueries({ queryKey: queryKeys.auth.all });
    return user;
  },

  /** Full logout: revoke server session + clear local state */
  logout: async () => {
    await authApi.logout().catch(() => {});
    clearTokens();
    set({ ...INITIAL, loading: false });
    // Clear all cached queries
    queryClient.clear();
  },

  /** Refresh user data from API */
  refreshUser: async () => {
    try {
      const user = await authApi.getMe();
      _persistUserMeta(user);
      set({ user, loading: false, isAuthenticated: true });
      return user;
    } catch {
      return null;
    }
  },

  /** Apply a partial patch to the current user (optimistic update) */
  patchUser: (patch) => {
    const { user } = get();
    if (!user) return;
    set({ user: { ...user, ...patch } });
  },

  /** Force logout (e.g. from 401 interceptor) */
  forceLogout: (reason) => {
    clearTokens();
    localStorage.removeItem('phishcatcher_email');
    localStorage.removeItem('phishcatcher_role');
    localStorage.removeItem('phishcatcher_name');
    if (reason) {
      localStorage.setItem('phishcatcher_logout_reason', reason);
    }
    set({ ...INITIAL, loading: false });
    queryClient.clear();
  },
}));

/** Convenience hook that mirrors the old AuthContext API */
export function useAuth() {
  const store = useAuthStore();
  return {
    user: store.user,
    loading: store.loading,
    isAuthenticated: store.isAuthenticated,
    isAdmin: store.user?.role === 'admin',
    hydrate: store.hydrate,
    loginWithTokens: store.loginWithTokens,
    logout: store.logout,
    refreshUser: store.refreshUser,
    patchUser: store.patchUser,
  };
}

/** Keep a few metadata keys in localStorage for Layout to read before hydration */
function _persistUserMeta(user) {
  if (!user) return;
  localStorage.setItem('phishcatcher_email', user.email ?? '');
  localStorage.setItem('phishcatcher_role',  user.role  ?? 'user');
  localStorage.setItem('phishcatcher_name',  user.full_name ?? '');
}
