import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { BedDouble, CalendarCheck, ShieldCheck, Wallet } from "lucide-react";
import { useAuth } from "../context/AuthContext.jsx";
import { Field } from "../components/ui.jsx";
import { errorMessage } from "../utils/errors.js";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function Login() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ email: "", password: "" });
  const [errors, setErrors] = useState({});
  const [formError, setFormError] = useState("");
  const [busy, setBusy] = useState(false);

  const homeFor = (u) => (u.role === "admin" ? "/admin/dashboard" : "/employee/dashboard");
  if (user) return <Navigate to={homeFor(user)} replace />;

  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    const next = {};
    if (!EMAIL_RE.test(form.email)) next.email = "Enter a valid email address.";
    if (!form.password) next.password = "Enter your password.";
    setErrors(next);
    setFormError("");
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      const u = await login(form.email.trim(), form.password);
      const from = location.state?.from;
      const allowed = from && from.startsWith(u.role === "admin" ? "/admin" : "/employee");
      navigate(allowed ? from : homeFor(u), { replace: true });
    } catch (err) {
      setFormError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-split">
      <aside className="login-aside">
        <div>
          <h2>Everything a hostel office needs, in one place.</h2>
        </div>
        <p>Rooms, residents, fees and attendance, kept in step so the numbers on screen always match the register.</p>
        <ul className="feature-list">
          <li><span className="tile"><BedDouble size={20} aria-hidden="true" /></span><div><strong>Rooms and allocations</strong><span>Beds can never be over-filled, even when two people allocate at once.</span></div></li>
          <li><span className="tile"><Wallet size={20} aria-hidden="true" /></span><div><strong>Fees and receipts</strong><span>Part payments, balances, overdue tracking and printable receipts.</span></div></li>
          <li><span className="tile"><CalendarCheck size={20} aria-hidden="true" /></span><div><strong>Daily attendance</strong><span>Mark a whole roster in a minute and see percentages per student.</span></div></li>
          <li><span className="tile"><ShieldCheck size={20} aria-hidden="true" /></span><div><strong>Role-based access</strong><span>Employees only see and do what an administrator allows.</span></div></li>
        </ul>
      </aside>
      <div className="login-main">
        <form className="login-card" onSubmit={submit} noValidate>
          <div className="brand brand-dark">
            <span className="brand-mark" aria-hidden="true">H</span>
            <div>
              <strong>Hostel Desk</strong>
              <small>Staff sign in</small>
            </div>
          </div>
          <h1>Sign in</h1>
          <p className="lead">Use the email and password your administrator gave you.</p>
          {formError && <div className="notice notice-error" role="alert">{formError}</div>}
          <Field label="Email" name="email" type="email" autoComplete="username" value={form.email} onChange={set} error={errors.email} autoFocus />
          <Field label="Password" name="password" type="password" autoComplete="current-password" value={form.password} onChange={set} error={errors.password} />
          <button className="btn btn-primary btn-block" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
          <p className="hint">Accounts are created by a hostel administrator. Forgotten your password? Ask an administrator to reset it.</p>
        </form>
      </div>
    </div>
  );
}
