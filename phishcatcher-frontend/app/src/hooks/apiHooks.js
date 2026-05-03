/**
 * TanStack Query hooks for the PhishCatcher API.
 * 
 * These hooks wrap the existing api.js functions with caching,
 * automatic refetching, and optimistic updates.
 * 
 * Server state → useQuery / useMutation (this file)
 * Client state  → Zustand stores (stores/)
 */

import { useQuery, useMutation, useInfiniteQuery } from '@tanstack/react-query';
import { queryClient, queryKeys } from '@/lib/queryClient';
import { authApi, adminApi, analysisApi, mlApi, sessionApi, notificationApi, taskApi, providerApi, securityApi } from '@/lib/api';

// ─── Auth hooks ────────────────────────────────────────────────────────────────

export function useCurrentUser(enabled = true) {
  return useQuery({
    queryKey: queryKeys.auth.me(),
    queryFn: authApi.getMe,
    enabled,
    staleTime: 1000 * 60 * 5,  // 5 min
  });
}

export function useMfaStatus() {
  return useQuery({
    queryKey: queryKeys.mfa.status(),
    queryFn: authApi.getMfaStatus,
  });
}

// ─── Analysis hooks ────────────────────────────────────────────────────────────

export function useAnalysisHistory(filters = {}) {
  return useQuery({
    queryKey: queryKeys.analysis.history(filters),
    queryFn: () => analysisApi.getHistory(filters),
  });
}

export function useAnalysis(id, enabled = true) {
  return useQuery({
    queryKey: queryKeys.analysis.detail(id),
    queryFn: () => analysisApi.getAnalysis(id),
    enabled: enabled && !!id,
  });
}

export function useAnalysisStatus(id, { refetchInterval = 3000 } = {}) {
  return useQuery({
    queryKey: queryKeys.analysis.status(id),
    queryFn: () => analysisApi.getStatus(id),
    enabled: !!id,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === 'completed' || status === 'failed') return false;
      return refetchInterval;
    },
  });
}

export function useUploadEmail() {
  return useMutation({
    mutationFn: ({ file, queueOnly = false }) =>
      analysisApi.uploadEmail(file, queueOnly),
    onSuccess: () => {
      // Invalidate history so new analysis appears
      // We don't know the filters, so invalidate the whole branch
      // (next render with specific filters will refetch)
    },
  });
}

export function useStartAnalysis() {
  return useMutation({
    mutationFn: (id) => analysisApi.startAnalysis(id),
  });
}

export function useDeleteAnalysis() {
  return useMutation({
    mutationFn: (id) => analysisApi.deleteAnalysis(id),
  });
}

// ─── Admin hooks ───────────────────────────────────────────────────────────────

export function useAdminStats() {
  return useQuery({
    queryKey: queryKeys.admin.stats(),
    queryFn: adminApi.getStats,
  });
}

export function useAdminUsers(filters = {}) {
  return useQuery({
    queryKey: queryKeys.admin.users(filters),
    queryFn: () => adminApi.listUsers(filters),
  });
}

export function useAdminAuditLogs(filters = {}) {
  return useQuery({
    queryKey: queryKeys.admin.auditLogs(filters),
    queryFn: () => adminApi.getAuditLogs(filters),
  });
}

export function useAdminModelInfo() {
  return useQuery({
    queryKey: queryKeys.admin.modelInfo(),
    queryFn: adminApi.getModelInfo,
  });
}

export function useUpdateUser() {
  return useMutation({
    mutationFn: ({ id, ...data }) => adminApi.updateUser(id, data),
  });
}

export function useDeleteUser() {
  return useMutation({
    mutationFn: ({ id, ...payload }) => adminApi.deleteUser(id, payload),
  });
}

// ─── Gmail hooks ───────────────────────────────────────────────────────────────

export function useGmailStatus() {
  return useQuery({
    queryKey: queryKeys.gmail.status(),
    queryFn: authApi.gmail.getStatus,
  });
}

export function useGmailEmails(params = {}) {
  return useQuery({
    queryKey: queryKeys.gmail.emails(params),
    queryFn: () => authApi.gmail.listEmails(
      params.page ?? 1,
      params.maxResults ?? 20,
      params.q ?? null,
      params.providerId ?? null,
    ),
  });
}

export function useGmailQueue() {
  return useQuery({
    queryKey: queryKeys.gmail.queue(),
    queryFn: authApi.gmail.getQueue,
  });
}

export function useGmailAccounts() {
  return useQuery({
    queryKey: queryKeys.gmail.accounts(),
    queryFn: authApi.gmail.getAccounts,
  });
}

// ─── ML hooks ──────────────────────────────────────────────────────────────────

export function useMLPredict() {
  return useMutation({
    mutationFn: ({ subject, body }) => mlApi.predict(subject, body),
  });
}

export function useModelsStatus() {
  return useQuery({
    queryKey: ['ml', 'models'],
    queryFn: mlApi.getModelsStatus,
  });
}

// ─── Reports hooks ─────────────────────────────────────────────────────────────

export function useWeeklyReport(params = {}) {
  return useQuery({
    queryKey: queryKeys.analysis.reports(params),
    queryFn: () => analysisApi.getReport(
      params.startDate,
      params.endDate,
      params.weekStart,
    ),
    enabled: !!(params.startDate || params.weekStart),
  });
}

// ─── Session hooks ──────────────────────────────────────────────────────────────

export function useSessionStatus(refetchInterval = 60000) {
  return useQuery({
    queryKey: queryKeys.session.status(),
    queryFn: sessionApi.getStatus,
    refetchInterval,
  });
}

export function useExtendSession() {
  return useMutation({
    mutationFn: sessionApi.extend,
  });
}

export function useSessionLogout() {
  return useMutation({
    mutationFn: sessionApi.logout,
  });
}

export function useValidateSession() {
  return useQuery({
    queryKey: ['session', 'validate'],
    queryFn: sessionApi.validate,
    enabled: false,
  });
}

export function useSessionCleanup() {
  return useMutation({
    mutationFn: sessionApi.cleanup,
  });
}

// ─── Notification hooks ─────────────────────────────────────────────────────────

export function useNotifications(params = {}) {
  return useQuery({
    queryKey: queryKeys.notifications.list(params),
    queryFn: () => notificationApi.getNotifications(params),
  });
}

export function useNotificationPreferences() {
  return useQuery({
    queryKey: queryKeys.notifications.preferences(),
    queryFn: notificationApi.getPreferences,
  });
}

export function useUpdateNotificationPreferences() {
  return useMutation({
    mutationFn: notificationApi.updatePreferences,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.preferences() });
    },
  });
}

export function useMarkNotificationRead() {
  return useMutation({
    mutationFn: notificationApi.markRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useMarkAllNotificationsRead() {
  return useMutation({
    mutationFn: notificationApi.markAllRead,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.notifications.all });
    },
  });
}

export function useSubscribeNotifications() {
  return useMutation({
    mutationFn: notificationApi.subscribe,
  });
}

export function useUnsubscribeNotifications() {
  return useMutation({
    mutationFn: notificationApi.unsubscribe,
  });
}

// ─── Task hooks ─────────────────────────────────────────────────────────────────

export function useCurrentUserTasks(statusFilter, limit = 50) {
  return useQuery({
    queryKey: queryKeys.admin.tasks({ statusFilter, limit }),
    queryFn: () => taskApi.getCurrentUserTasks(statusFilter, limit),
  });
}

export function useRevokeTask() {
  return useMutation({
    mutationFn: taskApi.revokeTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.admin.tasks.all });
    },
  });
}

// ─── Provider hooks ─────────────────────────────────────────────────────────────

export function useProviders() {
  return useQuery({
    queryKey: queryKeys.providers.list(),
    queryFn: providerApi.listProviders,
  });
}

export function useProvider(id) {
  return useQuery({
    queryKey: queryKeys.providers.detail(id),
    queryFn: () => providerApi.getProvider(id),
    enabled: !!id,
  });
}

export function useProviderHealth(id) {
  return useQuery({
    queryKey: queryKeys.providers.health(id),
    queryFn: () => providerApi.checkProviderHealth(id),
    enabled: !!id,
    refetchInterval: 30000,
  });
}

export function useUpdateProvider() {
  return useMutation({
    mutationFn: ({ id, ...data }) => providerApi.updateProvider(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.providers.all });
    },
  });
}

export function useSyncProvider() {
  return useMutation({
    mutationFn: ({ id, ...options }) => providerApi.syncProvider(id, options),
  });
}

export function useDeleteProvider() {
  return useMutation({
    mutationFn: providerApi.deleteProvider,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.providers.all });
    },
  });
}

export function useConnectGmailProvider() {
  return useMutation({
    mutationFn: ({ code, state }) => providerApi.connectGmail(code, state),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.providers.all });
    },
  });
}

// ─── Security hooks ─────────────────────────────────────────────────────────────

export function useSecurityRequirements(action) {
  return useQuery({
    queryKey: queryKeys.security.requirements(action),
    queryFn: () => securityApi.getSecurityRequirements(action),
    enabled: !!action,
  });
}

export function useSendEmailVerification() {
  return useMutation({
    mutationFn: securityApi.sendEmailVerification,
  });
}

// ─── Gmail mutation hooks ───────────────────────────────────────────────────────

export function useGmailDisconnect() {
  return useMutation({
    mutationFn: authApi.gmail.disconnect,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.gmail.all });
    },
  });
}

export function useQueueEmails() {
  return useMutation({
    mutationFn: ({ messageIds, providerId }) =>
      authApi.gmail.queueEmails(messageIds, providerId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.gmail.queue() });
    },
  });
}

export function useAnalyzeEmails() {
  return useMutation({
    mutationFn: (messageIds) => authApi.gmail.analyzeEmails(messageIds),
  });
}

export function useMarkEmailSafe() {
  return useMutation({
    mutationFn: authApi.gmail.markSafe,
  });
}

export function useReportPhishing() {
  return useMutation({
    mutationFn: authApi.gmail.reportPhishing,
  });
}

export function useProcessQueueItem() {
  return useMutation({
    mutationFn: authApi.gmail.processQueueItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.gmail.queue() });
    },
  });
}

export function useDeleteQueueItem() {
  return useMutation({
    mutationFn: authApi.gmail.deleteQueueItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.gmail.queue() });
    },
  });
}

export function useClearQueue() {
  return useMutation({
    mutationFn: authApi.gmail.clearQueue,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.gmail.queue() });
    },
  });
}

export function useRemoveGmailAccount() {
  return useMutation({
    mutationFn: authApi.gmail.removeAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.gmail.all });
    },
  });
}

export function useSetDefaultAccount() {
  return useMutation({
    mutationFn: authApi.gmail.setDefaultAccount,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.gmail.all });
    },
  });
}
