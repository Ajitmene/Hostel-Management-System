import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { employees } from "../api/endpoints.js";
import { useToast } from "../context/ToastContext.jsx";
import { ConfirmDialog } from "../components/Modal.jsx";
import { ErrorNotice, Field, InfoBox, Loading, PageHeader } from "../components/ui.jsx";
import { ArrowLeft, UserCog } from "lucide-react";
import { errorMessage, fieldErrors } from "../utils/errors.js";
import { today } from "../utils/format.js";

export const PERMISSIONS = [
  ["students.view", "View students"],
  ["rooms.view", "View rooms and availability"],
  ["fees.view", "View fees and payment status"],
  ["attendance.view", "View attendance history"],
  ["attendance.record", "Record attendance"],
];
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?[0-9]{7,15}$/;

export default function EmployeeForm() {
  const { id } = useParams();
  const editing = !!id;
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState({
    first_name: "", last_name: "", email: "", employee_id: "", phone: "", designation: "", department: "",
    joining_date: today(), permissions: PERMISSIONS.map(([c]) => c), password: "",
  });
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(editing);
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);
  const [resetting, setResetting] = useState(false);
  const [newPassword, setNewPassword] = useState("");

  useEffect(() => {
    if (!editing) return;
    employees.get(id).then(({ data }) => setForm({ ...data, password: "" })).catch((e) => setLoadError(errorMessage(e))).finally(() => setLoading(false));
  }, [id, editing]);

  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  const togglePerm = (code) => setForm((f) => ({ ...f, permissions: f.permissions.includes(code) ? f.permissions.filter((c) => c !== code) : [...f.permissions, code] }));

  const submit = async (e) => {
    e.preventDefault();
    const found = {};
    if (!form.first_name.trim()) found.first_name = "Enter the first name.";
    if (!form.last_name.trim()) found.last_name = "Enter the last name.";
    if (!EMAIL_RE.test(form.email)) found.email = "Enter a valid email address.";
    if (!form.employee_id.trim()) found.employee_id = "Enter the employee ID.";
    if (!PHONE_RE.test(form.phone)) found.phone = "Use 7–15 digits, with an optional leading +.";
    if (!form.designation.trim()) found.designation = "Enter the designation.";
    if (!form.department.trim()) found.department = "Enter the department.";
    if (!editing && form.password.length < 10) found.password = "Use at least 10 characters.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      const { password, id: _i, user_id, is_active, role, ...body } = form;
      if (editing) await employees.update(id, body); else await employees.create({ ...body, password });
      toast.success(editing ? "Employee updated." : "Employee account created.");
      navigate("/admin/employees");
    } catch (err) {
      setErrors({ ...fieldErrors(err), form: errorMessage(err) });
    } finally { setBusy(false); }
  };

  const reset = async () => {
    setBusy(true);
    try {
      await employees.resetPassword(id, newPassword);
      toast.success("Password updated. The employee was signed out everywhere.");
      setResetting(false);
      setNewPassword("");
    } catch (err) { toast.error(errorMessage(err)); } finally { setBusy(false); }
  };

  if (loading) return <Loading />;
  if (loadError) return <ErrorNotice message={loadError} />;

  return (
    <>
      <PageHeader icon={UserCog} title={editing ? "Edit employee" : "Add employee"} subtitle="The role is always Employee. What they can do is set by the permissions below."
        actions={<Link className="btn" to="/admin/employees"><ArrowLeft aria-hidden="true" />Back to employees</Link>} />
      <InfoBox title="Permissions explained">
        <ul>
          <li><strong>View students / rooms / fees</strong> gives read-only access to those lists.</li>
          <li><strong>Record attendance</strong> lets them save daily attendance; <strong>View attendance</strong> lets them read the history.</li>
          <li>Whatever is ticked here, employees can never manage employees, change roles, record payments, or edit students and rooms.</li>
          {!editing && <li>The temporary password is shown only to you. Share it securely; the employee can change it from their profile.</li>}
        </ul>
      </InfoBox>
      <form className="panel form-grid" onSubmit={submit} noValidate>
        {errors.form && !Object.keys(errors).some((k) => k !== "form") && <div className="notice notice-error span-2" role="alert">{errors.form}</div>}
        <Field label="First name" name="first_name" value={form.first_name} onChange={set} error={errors.first_name} />
        <Field label="Last name" name="last_name" value={form.last_name} onChange={set} error={errors.last_name} />
        <Field label="Email (used to sign in)" name="email" type="email" value={form.email} onChange={set} error={errors.email} />
        <Field label="Employee ID" name="employee_id" value={form.employee_id} onChange={set} error={errors.employee_id} />
        <Field label="Phone" name="phone" inputMode="tel" value={form.phone} onChange={set} error={errors.phone} />
        <Field label="Joining date" name="joining_date" type="date" value={form.joining_date} onChange={set} />
        <Field label="Designation" name="designation" value={form.designation} onChange={set} error={errors.designation} />
        <Field label="Department" name="department" value={form.department} onChange={set} error={errors.department} />
        {!editing && <div className="span-2"><Field label="Temporary password" name="password" type="password" autoComplete="new-password" value={form.password} onChange={set} error={errors.password} hint="At least 10 characters. Share it securely; the employee can change it from their profile." /></div>}
        <fieldset className="span-2 perms">
          <legend>Permissions</legend>
          {PERMISSIONS.map(([code, label]) => (
            <label key={code} className="check"><input type="checkbox" checked={form.permissions.includes(code)} onChange={() => togglePerm(code)} /> {label}</label>
          ))}
          <small className="hint">Employees can never manage employees, change roles, record payments, or edit students and rooms.</small>
        </fieldset>
        <div className="form-actions span-2">
          {editing && <button type="button" className="btn btn-danger-ghost push-left" onClick={() => setResetting(true)}>Reset password…</button>}
          <button type="button" className="btn" onClick={() => navigate("/admin/employees")}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Create account"}</button>
        </div>
      </form>
      {resetting && (
        <ConfirmDialog title="Reset password" confirmLabel="Set new password" busy={busy || newPassword.length < 10} onConfirm={reset} onCancel={() => setResetting(false)}
          message={<><span>Choose a new temporary password (10+ characters). The employee is signed out everywhere.</span><input className="remarks full" type="password" autoComplete="new-password" aria-label="New password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} /></>} />
      )}
    </>
  );
}
