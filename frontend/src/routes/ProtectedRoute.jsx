import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext.jsx";
import { Loading } from "../components/ui.jsx";
import Unauthorized from "../pages/Unauthorized.jsx";

/**
 * Wrap routes that need a signed-in user.
 *  - not signed in            -> redirect to /login (remembering where they were going)
 *  - `roles` given and wrong  -> access-denied page
 *  - `permission` / `anyOf`   -> access-denied page when the employee lacks them
 * This is for usability only: the API enforces the same rules on the server.
 */
export default function ProtectedRoute({ roles, permission, anyOf, children }) {
  const { user, loading, can } = useAuth();
  const location = useLocation();

  if (loading) return <Loading label="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (roles && !roles.includes(user.role)) return <Unauthorized />;
  if (permission && !can(permission)) return <Unauthorized />;
  if (anyOf && !anyOf.some(can)) return <Unauthorized />;
  return children || <Outlet />;
}
