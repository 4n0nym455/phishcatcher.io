/**
 * App.jsx
 *
 * Root application with full routing configuration.
 * - "/" renders LandingPage (public marketing page)
 * - Auth flow: /login → /verify-otp → /mfa-verification
 * - Authenticated pages wrapped in <PrivateRoute> + <Layout>
 * - Admin pages require requireAdmin={true}
 * - ThemeProvider + Zustand auth store wrap everything
 * - TanStack Query for server state caching
 */

import { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';

import { ThemeProvider }    from '@/context/ThemeContext';
import { FontSizeProvider } from '@/context/FontSizeContext';
import { useAuthStore }     from '@/stores/authStore';
import { useAuth }          from '@/stores/authStore';
import { queryClient }      from '@/lib/queryClient';

// ── Public pages ──────────────────────────────────────────────────────────
import LandingPage           from '@/pages/LandingPage';
import LoginPage             from '@/pages/LoginPage';
import RegisterPage          from '@/pages/RegisterPage';
import OTPPage               from '@/pages/OTPPage';
import MFAVerificationPage   from '@/pages/MFAVerificationPage';
import { ForgotPasswordPage, ResetPasswordPage } from '@/pages/PasswordPage';
import { ActivateAccountPage, ActivationPendingPage } from '@/pages/ActivationPage';
import GoogleCallbackPage    from '@/pages/GoogleCallbackPage';
import { TermsOfService, PrivacyPolicy } from '@/pages/LegalPage';

// ── Authenticated pages ───────────────────────────────────────────────────
import DashboardPage         from '@/pages/DashboardPage';
import EmailUploadPage       from '@/pages/EmailUploadPage';
import AnalysisListPage      from '@/pages/AnalysisListPage';
import AnalysisReportPage    from '@/pages/AnalysisReportPage';
import ReportsPage            from '@/pages/ReportsPage';
import AccountSettingsPage   from '@/pages/AccountSettingsPage';
import MFASettingsPage       from '@/pages/MFASettingsPage';
import GmailSettingsPage    from '@/pages/GmailSettingsPage';
import SessionManagementPage from '@/pages/SessionManagementPage';
import NotificationSettingsPage from '@/pages/NotificationSettingsPage';
import ProviderManagementPage from '@/pages/ProviderManagementPage';

// ── Admin pages ───────────────────────────────────────────────────────────
import AdminDashboardPage    from '@/pages/AdminDashboardPage';
import UserManagement        from '@/pages/UserManagement';
import AuditLogs             from '@/pages/AuditLogs';

// ── Shell components ──────────────────────────────────────────────────────
import Layout                from '@/components/Layout';
import PrivateRoute          from '@/pages/PrivateRoute';
import LoadingOrb            from '@/components/LoadingOrb';
import { FontSizeToggle }    from '@/components/FontSizeToggle';

export default function App() {
  return (
    <ThemeProvider>
      <FontSizeProvider>
        <QueryClientProvider client={queryClient}>
          <Router>
            <AppInner />
            <FontSizeToggle />
            {/* Toast notifications — top-right, themed */}
            <Toaster
              position="top-right"
              toastOptions={{
                style: {
                  borderRadius: '12px',
                  boxShadow: 'var(--shadow-lg)',
                },
                classNames: {
                  success: 'border-l-[4px] !border-l-green-500 [&_[data-icon]]:text-green-500',
                  error: 'border-l-[4px] !border-l-red-500 [&_[data-icon]]:text-red-500',
                  info: 'border-l-[4px] !border-l-blue-500 [&_[data-icon]]:text-blue-500',
                  warning: 'border-l-[4px] !border-l-yellow-500 [&_[data-icon]]:text-yellow-500',
                },
              }}
            />
          </Router>
        </QueryClientProvider>
      </FontSizeProvider>
    </ThemeProvider>
  );
}

function AppInner() {
  const hydrate = useAuthStore((s) => s.hydrate);
  const { loading } = useAuth();

  // Hydrate auth state on mount (replaces old AuthProvider effect)
  useEffect(() => {
    hydrate();
  }, [hydrate]);

  // Show a full-screen loader while auth state is being hydrated
  if (loading) {
    return (
      <div
        className="min-h-screen flex items-center justify-center"
        style={{ background: 'var(--bg-base)' }}
      >
        <LoadingOrb size="large" text="Initializing PhishCatcher…" />
      </div>
    );
  }

  return (
    <Routes>
      {/* ── Home ─────────────────────────────────────────────────────── */}
      <Route path="/" element={<LandingPage />} />

      {/* ── Auth ─────────────────────────────────────────────────────── */}
      <Route path="/login"           element={<LoginPage />} />
      <Route path="/register"        element={<RegisterPage />} />
      <Route path="/verify-otp"      element={<OTPPage />} />
      <Route path="/mfa-verification" element={<MFAVerificationPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password"  element={<ResetPasswordPage />} />

      {/* ── Google OAuth callback (popup window) ─────────────────────── */}
      <Route path="/google/callback"      element={<GoogleCallbackPage />} />
      <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
      <Route path="/gmail/callback"      element={<GoogleCallbackPage />} />

      {/* ── Account activation ───────────────────────────────────────── */}
      <Route path="/activate"            element={<ActivateAccountPage />} />
      <Route path="/activation-pending"  element={<ActivationPendingPage />} />

      {/* ── Legal ────────────────────────────────────────────────────── */}
      <Route path="/terms"   element={<TermsOfService />} />
      <Route path="/privacy" element={<PrivacyPolicy />} />

      {/* ── Authenticated user pages ──────────────────────────────────
          All wrapped in PrivateRoute (redirects to /login if not authed)
          and Layout (sidebar + header shell).
      ──────────────────────────────────────────────────────────────── */}
      <Route element={<PrivateRoute />}>
        <Route element={<Layout><Outlet /></Layout>}>
          <Route path="/dashboard"      element={<DashboardPage />} />
          <Route path="/upload"         element={<EmailUploadPage />} />
          <Route path="/analysis"       element={<AnalysisListPage />} />
          <Route path="/analysis/:id"   element={<AnalysisReportPage />} />
          <Route path="/reports" element={<ReportsPage />} />
          <Route path="/settings"       element={<AccountSettingsPage />} />
          <Route path="/settings/mfa"   element={<MFASettingsPage />} />
          <Route path="/settings/gmail" element={<GmailSettingsPage />} />
          <Route path="/settings/notifications" element={<NotificationSettingsPage />} />
          <Route path="/settings/providers" element={<ProviderManagementPage />} />
        </Route>
      </Route>

      {/* ── Admin pages ───────────────────────────────────────────────
          requireAdmin={true} redirects non-admins to /dashboard.
      ──────────────────────────────────────────────────────────────── */}
      <Route element={<PrivateRoute requireAdmin />}>
        <Route element={<Layout><Outlet /></Layout>}>
          <Route path="/admin"          element={<AdminDashboardPage />} />
          <Route path="/admin/users"    element={<UserManagement />} />
          <Route path="/admin/audit-logs" element={<AuditLogs />} />
          <Route path="/admin/sessions" element={<SessionManagementPage />} />
        </Route>
      </Route>

      {/* ── 404 fallback — redirect to home ──────────────────────────── */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}