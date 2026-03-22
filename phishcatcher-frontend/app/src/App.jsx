/**
 * App.jsx — updated to include ThemeProvider
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'sonner';
import { AuthProvider }  from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
import PrivateRoute      from '@/pages/PrivateRoute';
import Layout            from '@/components/Layout';

// Auth pages
import LoginPage              from '@/pages/LoginPage';
import RegisterPage           from '@/pages/RegisterPage';
import OTPPage                from '@/pages/OTPPage';
import MFAVerificationPage    from '@/pages/MFAVerificationPage';
import GoogleCallbackPage     from '@/pages/GoogleCallbackPage';
import { ActivateAccountPage, ActivationPendingPage }  from '@/pages/ActivationPage';
import { ForgotPasswordPage, ResetPasswordPage }     from '@/pages/PasswordPage';

// App pages
import DashboardPage         from '@/pages/DashboardPage';
import EmailUploadPage       from '@/pages/EmailUploadPage';
import AnalysisListPage      from '@/pages/AnalysisListPage';
import AnalysisReportPage    from '@/pages/AnalysisReportPage';
import WeeklyReportsPage     from '@/pages/WeeklyReportsPage';
import AccountSettingsPage   from '@/pages/AccountSettingsPage';
import AdminDashboardPage    from '@/pages/AdminDashboardPage';

export default function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>

        <Toaster
          position="top-right"
          richColors
          closeButton
          toastOptions={{
            style: {
              fontFamily: "'DM Sans', system-ui, sans-serif",
              borderRadius: '12px',
            },
          }}
        />
      </AuthProvider>
    </ThemeProvider>
  );
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public auth routes */}
      <Route path="/login"               element={<LoginPage />} />
      <Route path="/register"            element={<RegisterPage />} />
      <Route path="/verify-otp"          element={<OTPPage />} />
      <Route path="/mfa-verification"    element={<MFAVerificationPage />} />
      <Route path="/activate"            element={<ActivateAccountPage />} />
      <Route path="/activation-pending"  element={<ActivationPendingPage />} />
      <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
      <Route path="/forgot-password"     element={<ForgotPasswordPage />} />
      <Route path="/reset-password"      element={<ResetPasswordPage />} />

      {/* Protected app routes */}
      <Route element={<PrivateRoute />}>
        <Route element={<Layout><Outlet /></Layout>}>
          <Route path="/dashboard"      element={<DashboardPage />} />
          <Route path="/upload"         element={<EmailUploadPage />} />
          <Route path="/analysis"       element={<AnalysisListPage />} />
          <Route path="/analysis/:id"   element={<AnalysisReportPage />} />
          <Route path="/weekly-reports" element={<WeeklyReportsPage />} />
          <Route path="/settings"       element={<AccountSettingsPage />} />
        </Route>
      </Route>

      {/* Admin routes */}
      <Route element={<PrivateRoute requireAdmin />}>
        <Route element={<Layout><Outlet /></Layout>}>
          <Route path="/admin"          element={<AdminDashboardPage />} />
          <Route path="/admin/*"        element={<AdminDashboardPage />} />
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

// Outlet re-export for use inside Layout wrapper
import { Outlet } from 'react-router-dom';