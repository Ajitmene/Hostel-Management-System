import { Link } from "react-router-dom";
import { ShieldAlert } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";

export default function Unauthorized() {
  const { user } = useAuth();
  const home = user?.role === "admin" ? "/admin/dashboard" : user ? "/employee/dashboard" : "/login";
  return (
    <div className="empty empty-page" role="alert">
      <span className="empty-icon" aria-hidden="true"><ShieldAlert size={26} /></span>
      <h1>You don’t have access to this page</h1>
      <p>Your account isn’t permitted to use this area. If you need it, ask a hostel administrator to update your permissions.</p>
      <Link className="btn btn-primary" to={home}>Back to your dashboard</Link>
    </div>
  );
}
