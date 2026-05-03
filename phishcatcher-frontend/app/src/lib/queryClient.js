/**
 * TanStack Query configuration for PhishCatcher.
 * 
 * Provides:
 * - Automatic request deduplication
 * - Background refetching with stale-while-revalidate
 * - Optimistic updates for mutations
 * - Global cache invalidation helpers
 */

import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,       // 5 min — data considered fresh
      gcTime: 1000 * 60 * 30,          // 30 min — cache retained in memory
      retry: 1,                        // retry once on transient failure
      refetchOnWindowFocus: false,     // avoid noisy refetches
      refetchOnMount: true,
    },
    mutations: {
      retry: 0,
    },
  },
});

/**
 * Pre-built query key factories for type-safe cache management.
 * Usage: queryKeys.auth.me() → ['auth', 'me']
 */
export const queryKeys = {
  auth: {
    all: ['auth'],
    me: ()  => ['auth', 'me'],
  },
  analysis: {
    all:      ['analysis'],
    history:  (filters) => ['analysis', 'history', filters],
    detail:   (id)      => ['analysis', id],
    status:   (id)      => ['analysis', id, 'status'],
    reports:  (params)  => ['analysis', 'reports', params],
  },
  admin: {
    all:      ['admin'],
    stats:    ()        => ['admin', 'stats'],
    users:    (filters) => ['admin', 'users', filters],
    auditLogs:(filters) => ['admin', 'audit-logs', filters],
    modelInfo:()        => ['admin', 'model-info'],
    tasks:    (filters) => ['admin', 'tasks', filters],
  },
  gmail: {
    all:        ['gmail'],
    status:     ()         => ['gmail', 'status'],
    emails:     (params)   => ['gmail', 'emails', params],
    queue:      ()         => ['gmail', 'queue'],
    accounts:   ()         => ['gmail', 'accounts'],
  },
  mfa: {
    all:    ['mfa'],
    status: () => ['mfa', 'status'],
  },
  notifications: {
    all:    ['notifications'],
    list:   (params) => ['notifications', params],
    unread: ()       => ['notifications', 'unread'],
    preferences: ()  => ['notifications', 'preferences'],
  },
  session: {
    all:    ['session'],
    status: () => ['session', 'status'],
  },
  providers: {
    all:  ['providers'],
    list: ()         => ['providers', 'list'],
    detail: (id)     => ['providers', id],
    health: (id)     => ['providers', id, 'health'],
  },
  security: {
    requirements: (action) => ['security', 'requirements', action],
  },
};
