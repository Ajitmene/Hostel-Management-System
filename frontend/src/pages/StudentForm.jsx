import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { students } from "../api/endpoints.js";
import { useBase } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { ErrorNotice, Field, InfoBox, Loading, PageHeader } from "../components/ui.jsx";
import { Pencil, UserPlus } from "lucide-react";
import { errorMessage, fieldErrors } from "../utils/errors.js";
import { today } from "../utils/format.js";

const EMPTY = {
  enrollment_no: "", full_name: "", email: "", phone: "", gender: "", address: "",
  guardian_name: "", guardian_phone: "", admission_date: today(),
};
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const PHONE_RE = /^\+?[0-9]{7,15}$/;

export function validateStudent(f) {
  const e = {};
  if (!f.enrollment_no.trim()) e.enrollment_no = "Enter the enrollment number.";
  else if (!/^[A-Za-z0-9\-_/]+$/.test(f.enrollment_no)) e.enrollment_no = "Use letters, numbers, - _ or / only.";
  if (!f.full_name.trim()) e.full_name = "Enter the student’s full name.";
  if (!EMAIL_RE.test(f.email)) e.email = "Enter a valid email address.";
  if (!PHONE_RE.test(f.phone)) e.phone = "Use 7–15 digits, with an optional leading +.";
  if (!f.gender) e.gender = "Choose a gender.";
  if (!f.address.trim()) e.address = "Enter the home address.";
  if (!f.guardian_name.trim()) e.guardian_name = "Enter the guardian’s name.";
  if (!PHONE_RE.test(f.guardian_phone)) e.guardian_phone = "Use 7–15 digits, with an optional leading +.";
  if (!f.admission_date) e.admission_date = "Choose the admission date.";
  return e;
}

export default function StudentForm() {
  const { id } = useParams();
  const editing = !!id;
  const base = useBase();
  const navigate = useNavigate();
  const toast = useToast();
  const [form, setForm] = useState(EMPTY);
  const [errors, setErrors] = useState({});
  const [loading, setLoading] = useState(editing);
  const [loadError, setLoadError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!editing) return;
    students.get(id).then(({ data }) => {
      const { room, status, id: _id, ...rest } = data;
      setForm(rest);
    }).catch((e) => setLoadError(errorMessage(e))).finally(() => setLoading(false));
  }, [id, editing]);

  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    const found = validateStudent(form);
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      const body = { ...form, enrollment_no: form.enrollment_no.trim(), full_name: form.full_name.trim() };
      if (editing) await students.update(id, body); else await students.create(body);
      toast.success(editing ? "Student updated." : "Student added.");
      navigate(`${base}/students`);
    } catch (err) {
      setErrors({ ...fieldErrors(err), form: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  if (loading) return <Loading />;
  if (loadError) return <ErrorNotice message={loadError} />;

  return (
    <>
      <PageHeader icon={editing ? Pencil : UserPlus} title={editing ? "Edit student" : "Add student"} subtitle="Contact and guardian details are used for emergencies, so please keep them current." />
      <InfoBox title="Before you save">
        <ul>
          <li>The <strong>enrollment number</strong> and <strong>email</strong> must be unique. The system will tell you if either is already used.</li>
          <li>Phone numbers use digits only, with an optional leading + (for example +919800000001).</li>
          <li>Room allocation is done separately on the Allocations page, so a room can never be over-filled.</li>
        </ul>
      </InfoBox>
      <form className="panel form-grid" onSubmit={submit} noValidate>
        {errors.form && !Object.keys(errors).some((k) => k !== "form") && <div className="notice notice-error span-2" role="alert">{errors.form}</div>}
        <Field label="Enrollment number" name="enrollment_no" value={form.enrollment_no} onChange={set} error={errors.enrollment_no} />
        <Field label="Full name" name="full_name" value={form.full_name} onChange={set} error={errors.full_name} />
        <Field label="Email" name="email" type="email" value={form.email} onChange={set} error={errors.email} />
        <Field label="Phone" name="phone" inputMode="tel" value={form.phone} onChange={set} error={errors.phone} hint="Example: +919800000001" />
        <Field label="Gender" name="gender" as="select" value={form.gender} onChange={set} error={errors.gender}>
          <option value="">Choose…</option><option value="female">Female</option><option value="male">Male</option><option value="other">Other</option>
        </Field>
        <Field label="Admission date" name="admission_date" type="date" value={form.admission_date} onChange={set} error={errors.admission_date} />
        <div className="span-2"><Field label="Home address" name="address" as="textarea" rows={3} value={form.address} onChange={set} error={errors.address} /></div>
        <Field label="Guardian name" name="guardian_name" value={form.guardian_name} onChange={set} error={errors.guardian_name} />
        <Field label="Guardian phone" name="guardian_phone" inputMode="tel" value={form.guardian_phone} onChange={set} error={errors.guardian_phone} />
        <div className="form-actions span-2">
          <button type="button" className="btn" onClick={() => navigate(`${base}/students`)}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : editing ? "Save changes" : "Add student"}</button>
        </div>
      </form>
    </>
  );
}
