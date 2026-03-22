import { Navigate, useLocation } from "react-router-dom";

/**
 * PrivateRoute — guards authenticated routes
 *
 * Checks localStorage for access_token and a valid user object.
 * Does NOT block on account_status — that is enforced by the backend
 * on every API call. The activation flow now sets status='active' before
 * issuing tokens, so by the time the user reaches the dashboard the
 * backend will accept their requests.
 */
export default function PrivateRoute({ children }) {
  const location = useLocation();

  const token = localStorage.getItem("access_token");
  const userRaw = localStorage.getItem("user");

  // No token at all — send to login
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Token exists but user object is malformed — clear and re-login
  let user = null;
  try {
    user = userRaw ? JSON.parse(userRaw) : null;
  } catch {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}