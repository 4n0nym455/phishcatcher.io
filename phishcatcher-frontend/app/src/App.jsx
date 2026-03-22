import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { ThemeProvider } from './components/ThemeProvider';
import { NotificationProvider } from './components/NotificationProvider';
import { NotificationContainer } from './components/NotificationToast';
import OceanWaves from './components/OceanWaves';
import LoadingOrb from './components/LoadingOrb';
import LandingPage from './pages/LandingPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import OTPPage from './pages/OTPPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import Dashboard from './pages/Dashboard';
import AnalysisReport from './pages/AnalysisReport';
import AdminDashboard from './pages/AdminDashboard';
import UserManagement from './pages/UserManagement';
import AuditLogs from './pages/AuditLogs';
import ModelManagement from './pages/ModelManagement';
import WeeklyReports from './pages/WeeklyReports';
import AccountSettings from './pages/AccountSettings';
import MFASettings from './pages/MFASettings';
import NotificationSettings from './components/NotificationSettings';
import NotificationTest from './components/NotificationTest';
import TermsOfService from './pages/TermsOfService';
import PrivacyPolicy from './pages/PrivacyPolicy';
import GoogleCallbackPage from './pages/GoogleCallbackPage';
import MFAVerificationPage from './pages/MFAVerificationPage';
import ActivationPendingPage from './pages/ActivationPendingPage';
import ActivateAccountPage from './pages/ActivateAccountPage';
import OAuthSuccessPage from './pages/OAuthSuccessPage';
import EmailUploadPage from './pages/EmailUploadPage';
import AnalysisListPage from './pages/AnalysisListPage';
import Layout from './components/Layout';
import PrivateRoute from './pages/PrivateRoute';
import { getTokens, authApi, clearTokens } from './lib/api'; // Import API utilities

// Admin layout component
function AdminLayout({ children, onLogout, userData }) {
  const navigate = useNavigate();
  const userRole = localStorage.getItem('phishcatcher_role');
  
  useEffect(() => {
    if (userRole !== 'admin') {
      navigate('/dashboard');
    }
  }, [userRole, navigate]);
  
  if (userRole !== 'admin') return null;
  
  return <Layout onLogout={onLogout} userRole="admin" userData={userData}>{children}</Layout>;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isRouteLoading, setIsRouteLoading] = useState(false);
  const [userRole, setUserRole] = useState('user');
  const [userData, setUserData] = useState({});
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    // Check for existing tokens on app load
    const checkAuth = async () => {
      const { accessToken } = getTokens();
      if (accessToken) {
        try {
          // Verify token is valid by fetching current user
          const user = await authApi.getMe();
          setIsAuthenticated(true);
          const role = user.role === 'admin' ? 'admin' : 'user';
          setUserRole(role);
          setUserData(user);
          localStorage.setItem('phishcatcher_role', role);
          localStorage.setItem('phishcatcher_email', user.email);
          localStorage.setItem('phishcatcher_name', user.full_name || '');
        } catch (error) {
          // Token invalid, clear storage
          console.error('Invalid token, clearing storage:', error);
          clearTokens();
          // Set fallback data
          setUserRole('user');
          setUserData({
            email: 'user@example.com',
            full_name: 'User',
            role: 'user'
          });
        }
      } else {
        // No token, set default user data
        setUserRole('user');
        setUserData({
          email: 'user@example.com',
          full_name: 'User',
          role: 'user'
        });
      }
      setIsLoading(false);
    };
    
    checkAuth();
  }, []);

  // Listen for auth success events
  useEffect(() => {
    const handleAuthSuccess = async () => {
      setIsRouteLoading(true);
      
      // Fetch fresh user data
      try {
        const user = await authApi.getMe();
        const role = user.role === 'admin' ? 'admin' : 'user';
        setUserRole(role);
        setUserData(user);
        
        // Update localStorage with fresh data
        localStorage.setItem('phishcatcher_role', role);
        localStorage.setItem('phishcatcher_email', user.email);
        localStorage.setItem('phishcatcher_name', user.full_name || '');
      } catch (error) {
        console.error('Failed to fetch user data in auth success:', error);
        // Fallback to localStorage values
        const role = localStorage.getItem('phishcatcher_role') || 'user';
        setUserRole(role);
        setUserData({
          email: localStorage.getItem('phishcatcher_email') || 'user@example.com',
          full_name: localStorage.getItem('phishcatcher_name') || 'User',
          role: role
        });
      }
      
      setTimeout(() => {
        setIsAuthenticated(true);
        setIsRouteLoading(false);
      }, 300);
    };

    window.addEventListener('auth-success', handleAuthSuccess);
    return () => window.removeEventListener('auth-success', handleAuthSuccess);
  }, []);

  const handleLogin = async () => {
    setIsRouteLoading(true);
    setIsAuthenticated(true);
    
    // Fetch fresh user data
    try {
      const user = await authApi.getMe();
      const role = user.role === 'admin' ? 'admin' : 'user';
      setUserRole(role);
      setUserData(user);
      
      // Update localStorage with fresh data
      localStorage.setItem('phishcatcher_role', role);
      localStorage.setItem('phishcatcher_email', user.email);
      localStorage.setItem('phishcatcher_name', user.full_name || '');
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      // Fallback to localStorage values
      const role = localStorage.getItem('phishcatcher_role') || 'user';
      setUserRole(role);
      setUserData({
        email: localStorage.getItem('phishcatcher_email') || 'user@example.com',
        full_name: localStorage.getItem('phishcatcher_name') || 'User',
        role: role
      });
    }
    
    setTimeout(() => setIsRouteLoading(false), 500); // Brief loading to show orb
  };

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
    clearTokens();
    setIsAuthenticated(false);
    setUserRole('user');
    setUserData({});
  };

  const addNotification = (notification) => {
    const id = Date.now() + Math.random();
    setNotifications(prev => [...prev, { ...notification, id }]);
  };

  const removeNotification = (id) => {
    setNotifications(prev => prev.filter(n => n.id !== id));
  };

  // Handle Google OAuth callback (if redirected back with tokens)
  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const accessToken = urlParams.get('access_token');
    const refreshToken = urlParams.get('refresh_token');
    
    if (accessToken && refreshToken) {
      // Store tokens from Google OAuth callback
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
      
      // Clean up URL
      window.history.replaceState({}, document.title, window.location.pathname);
      
      // Trigger auth state update
      handleLogin();
      window.location.href = '/dashboard';
    }
  }, []);

  if (isLoading || isRouteLoading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center relative overflow-hidden">
        <OceanWaves />
        <LoadingOrb size="large" text={isLoading ? "Initializing PhishCatcher..." : "Loading..."} />
      </div>
    );
  }

  return (
    <ThemeProvider defaultTheme="system" storageKey="phishcatcher-theme">
      <NotificationProvider>
        <Router>
          <OceanWaves />
          <Routes>
            <Route path="/" element={<LandingPage />} />
            <Route path="/login" element={<LoginPage onLogin={handleLogin} />} />
            <Route path="/register" element={<RegisterPage onLogin={handleLogin} />} />
            <Route path="/verify-otp" element={<OTPPage onVerify={handleLogin} />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/google/callback" element={<GoogleCallbackPage />} />
            <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />
            <Route path="/mfa-verification" element={<MFAVerificationPage />} />
            <Route path="/activation-pending" element={<ActivationPendingPage />} />
            <Route path="/activate" element={<ActivateAccountPage />} />
            <Route path="/oauth-success" element={<OAuthSuccessPage />} />
          <Route path="/terms" element={<TermsOfService />} />
          <Route path="/privacy" element={<PrivacyPolicy />} />
          
          {/* User Routes */}
          <Route 
            path="/dashboard" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <Dashboard />
                </Layout>
              </PrivateRoute>
            } 
          />
          <Route 
            path="/analysis/:id" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <AnalysisReport />
                </Layout>
              </PrivateRoute>
            } 
          />
          <Route 
            path="/weekly-reports" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <WeeklyReports />
                </Layout>
              </PrivateRoute>
            } 
          />
          
          <Route 
            path="/settings" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <AccountSettings />
                </Layout>
              </PrivateRoute>
            } 
          />
          
          <Route 
            path="/settings/mfa" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <MFASettings />
                </Layout>
              </PrivateRoute>
            } 
          />
          
          <Route 
            path="/upload" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <EmailUploadPage />
                </Layout>
              </PrivateRoute>
            } 
          />
          
          <Route 
            path="/analysis" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <AnalysisListPage />
                </Layout>
              </PrivateRoute>
            } 
          />
          
          {/* Admin Routes */}
          <Route 
            path="/admin" 
            element={
              isAuthenticated && userRole === 'admin' ? (
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <AdminDashboard />
                </Layout>
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } 
          />
          <Route 
            path="/admin/users" 
            element={
              isAuthenticated && userRole === 'admin' ? (
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <UserManagement />
                </Layout>
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } 
          />
          <Route 
            path="/admin/audit-logs" 
            element={
              isAuthenticated && userRole === 'admin' ? (
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <AuditLogs />
                </Layout>
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } 
          />
          <Route 
            path="/admin/model" 
            element={
              isAuthenticated && userRole === 'admin' ? (
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <ModelManagement />
                </Layout>
              ) : (
                <Navigate to="/dashboard" replace />
              )
            } 
          />
          
          <Route 
            path="/settings/notifications" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <NotificationSettings />
                </Layout>
              </PrivateRoute>
            } 
          />
          <Route 
            path="/test-notifications" 
            element={
              <PrivateRoute>
                <Layout onLogout={handleLogout} userRole={userRole} userData={userData}>
                  <NotificationTest />
                </Layout>
              </PrivateRoute>
            } 
          />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <NotificationContainer 
          notifications={notifications} 
          onRemove={removeNotification} 
        />
      </Router>
    </NotificationProvider>
  </ThemeProvider>
  );
}

export default App;