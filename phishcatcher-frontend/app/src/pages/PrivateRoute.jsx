/**
 * PrivateRoute
 *
 * Guards authenticated routes. Uses AuthContext (not raw localStorage)
 * so it reacts to programmatic logout correctly.
 *
 * While auth is still being determined (loading === true) we render nothing
 * to avoid a flash of the login page for returning users.
 */

import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import LoadingOrb from '@/components/LoadingOrb';

export default function PrivateRoute({ children, requireAdmin = false }) {
  const { isAuthenticated, isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <LoadingOrb size="large" text="Loading…" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requireAdmin && !isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}