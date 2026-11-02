import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { auth } from "../api/endpoints.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { Avatar, Field, InfoBox, PageHeader } from "../components/ui.jsx";
import { KeyRound, LogOut, UserCircle } from "lucide-react";
import { errorMessage } from "../utils/errors.js";

const PERMISSION_LABELS = {
  "students.view": "View students", "rooms.view": "View rooms", "fees.view": "View fees and payments",
  "attendance.view": "View attendance", "attendance.record": "Record attendance",
};

export default function Profile() {
  const { user, accept, logout } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const [form, setForm] = useState({ current: "", next: "", confirm: "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    const next = {};
    if (!form.current) next.current = "Enter your current password.";
    if (form.next.length < 10) next.next = "Use at least 10 characters.";
    if (form.next !== form.confirm) next.confirm = "The passwords don’t match.";
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    try {
      const { data } = await auth.changePassword(form.current, form.next);
      accept(data);
      setForm({ current: "", next: "", confirm: "" });
      toast.success("Password changed. Other devices have been signed out.");
    } catch (err) {
      setErrors({ form: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader icon={UserCircle} title="My profile" subtitle="Your account details and sign-in security." />
      <InfoBox title="Keeping your account safe">
        <ul>
          <li>Use a password of at least 10 characters that you don’t use anywhere else.</li>
          <li>Changing your password signs you out on every other device.</li>
          <li>Sign out when you leave a shared computer.</li>
        </ul>
      </InfoBox>
      <div className="grid-2">
        <section className="panel">
          <h2><Avatar name={`${user.first_name} ${user.last_name}`.trim() || user.email} size={30} />Account</h2>
          <dl className="details">
            <dt>Name</dt><dd>{`${user.first_name} ${user.last_name}`.trim() || "–"}</dd>
            <dt>Email</dt><dd>{user.email}</dd>
            <dt>Role</dt><dd>{user.role === "admin" ? "Administrator" : "Employee"}</dd>
            {user.employee_id && (<><dt>Employee ID</dt><dd>{user.employee_id}</dd></>)}
          </dl>
          {user.role === "employee" && (
            <>
              <h3>Your permissions</h3>
              {user.permissions.length ? (
                <ul className="plain">{user.permissions.map((p) => <li key={p}>{PERMISSION_LABELS[p] || p}</li>)}</ul>
              ) : <p className="muted">No permissions assigned yet.</p>}
            </>
          )}
          <button className="btn" onClick={async () => { await logout(); navigate("/login", { replace: true }); }}><LogOut aria-hidden="true" />Sign out</button>
        </section>
        <form className="panel" onSubmit={submit} noValidate>
          <h2><KeyRound size={18} aria-hidden="true" />Change password</h2>
          {errors.form && <div className="notice notice-error" role="alert">{errors.form}</div>}
          <Field label="Current password" name="current" type="password" autoComplete="current-password" value={form.current} onChange={set} error={errors.current} />
          <Field label="New password" name="next" type="password" autoComplete="new-password" value={form.next} onChange={set} error={errors.next} hint="At least 10 characters; avoid common passwords." />
          <Field label="Repeat new password" name="confirm" type="password" autoComplete="new-password" value={form.confirm} onChange={set} error={errors.confirm} />
          <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Change password"}</button>
        </form>
      </div>
    </>
  );
}
