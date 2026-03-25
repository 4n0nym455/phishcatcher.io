import { Navigate } from 'react-router-dom';

const ProtectedRoute = ({ children, isAuthenticated, userRole, userData, onLogout }) => {
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Layout onLogout={onLogout} userRole={userRole} userData={userData}>
      {children}
    </Layout>
  );
};

const AdminRoute = ({ children, isAuthenticated, userRole, userData, onLogout }) => {
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (userRole !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <Layout onLogout={onLogout} userRole="admin" userData={userData}>
      {children}
    </Layout>
  );
};

export { ProtectedRoute, AdminRoute };
