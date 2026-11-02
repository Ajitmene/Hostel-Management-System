import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { LogOut, Menu, X } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { Avatar } from "../components/ui.jsx";

/** Shared shell: sidebar + top bar. `nav` is a list of { group, items: [{ to, label, icon, end? }] }. */
export default function DashboardLayout({ nav, home, label }) {
  const { user, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const fullName = `${user.first_name} ${user.last_name}`.trim() || user.email;
  const date = new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" });

  const signOut = async () => {
    try {
      await logout();
    } catch {
      toast.error("Could not reach the server, but you have been signed out on this device.");
    }
    navigate("/login", { replace: true });
  };

  return (
    <div className="shell">
      <aside className={`sidebar ${open ? "sidebar-open" : ""}`} aria-label="Main navigation">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true">H</span>
          <div>
            <strong>Hostel Desk</strong>
            <small>{label}</small>
          </div>
          <button className="icon-btn sidebar-close" onClick={() => setOpen(false)} aria-label="Close menu"><X size={20} /></button>
        </div>
        <nav onClick={() => setOpen(false)}>
          {nav.map((section) => (
            <div key={section.group} className="nav-group">
              <div className="nav-heading">{section.group}</div>
              {section.items.map(({ to, label: text, icon: Icon, end }) => (
                <NavLink key={to} to={to} end={end} className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}>
                  <Icon size={18} aria-hidden="true" />
                  <span>{text}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <div className="main">
        <div className="topbar">
          <button className="icon-btn menu-btn" onClick={() => setOpen((o) => !o)} aria-label="Toggle menu"><Menu size={22} /></button>
          <div className="topbar-date">{date}</div>
          <div className="topbar-user">
            <NavLink to={`${home.replace("/dashboard", "")}/profile`} className="user-chip">
              <Avatar name={fullName} />
              <span className="user-text">
                <span>{fullName}</span>
                <small>{user.role === "admin" ? "Administrator" : "Employee"}</small>
              </span>
            </NavLink>
            <button className="btn btn-small" onClick={signOut}><LogOut size={15} aria-hidden="true" />Sign out</button>
          </div>
        </div>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
