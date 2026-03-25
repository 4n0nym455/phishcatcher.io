/**
 * App.jsx
 *
 * Root application with full routing configuration.
 * - "/" renders LandingPage (public marketing page)
 * - Auth flow: /login → /verify-otp → /mfa-verification
 * - Authenticated pages wrapped in <PrivateRoute> + <Layout>
 * - Admin pages require requireAdmin={true}
 * - ThemeProvider + AuthProvider wrap everything
 */

import { BrowserRouter as Router, Routes, Route, Navigate, Outlet } from 'react-router-dom';
import { Toaster } from 'sonner';

import { ThemeProvider }    from '@/context/ThemeContext';
import { AuthProvider }     from '@/context/AuthContext';
import { useAuth }          from '@/context/AuthContext';

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
import WeeklyReportsPage     from '@/pages/WeeklyReportsPage';
import AccountSettingsPage   from '@/pages/AccountSettingsPage';
import MFASettingsPage       from '@/pages/MFASettingsPage';

// ── Admin pages ───────────────────────────────────────────────────────────
import AdminDashboardPage    from '@/pages/AdminDashboardPage';
import UserManagement        from '@/pages/UserManagement';
import AuditLogs             from '@/pages/AuditLogs';
import ModelManagement       from '@/pages/ModelManagement';

// ── Shell components ──────────────────────────────────────────────────────
import Layout                from '@/components/Layout';
import PrivateRoute          from '@/pages/PrivateRoute';
import LoadingOrb            from '@/components/LoadingOrb';

export default function App() {
  return (
    <ThemeProvider>
      <Router>
        <AuthProvider>
          <AppRoutes />

          {/* Toast notifications — top-right, themed */}
          <Toaster
            position="top-right"
            richColors
            toastOptions={{
              style: {
                borderRadius: '12px',
                boxShadow: 'var(--shadow-lg)',
              },
              success: {
                style: {
                  background: '#10b981',
                  color: '#ffffff',
                  border: '1px solid #10b981',
                },
              },
              error: {
                style: {
                  background: '#ef4444',
                  color: '#ffffff',
                  border: '1px solid #ef4444',
                },
              },
              info: {
                style: {
                  background: '#3b82f6',
                  color: '#ffffff',
                  border: '1px solid #3b82f6',
                },
              },
              warning: {
                style: {
                  background: '#f59e0b',
                  color: '#ffffff',
                  border: '1px solid #f59e0b',
                },
              },
            }}
          />
        </AuthProvider>
      </Router>
    </ThemeProvider>
  );
}

function AppRoutes() {
  const { loading } = useAuth();

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
          <Route path="/weekly-reports" element={<WeeklyReportsPage />} />
          <Route path="/settings"       element={<AccountSettingsPage />} />
          <Route path="/settings/mfa"   element={<MFASettingsPage />} />
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
          <Route path="/admin/model"    element={<ModelManagement />} />
        </Route>
      </Route>

      {/* ── 404 fallback — redirect to home ──────────────────────────── */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}