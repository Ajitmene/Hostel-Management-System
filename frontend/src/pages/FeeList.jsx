import { useState } from "react";
import { Link } from "react-router-dom";
import { fees, students } from "../api/endpoints.js";
import { useAuth, useBase } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useLoad, usePagedQuery } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { Modal } from "../components/Modal.jsx";
import { Field, InfoBox, PageHeader, SearchInput, StatusBadge } from "../components/ui.jsx";
import { FeeStats } from "../components/PageStats.jsx";
import { CreditCard, FilePlus2, History, Layers, Wallet } from "lucide-react";
import { errorMessage, fieldErrors } from "../utils/errors.js";
import { formatDate, formatMoney } from "../utils/format.js";

function StructureModal({ onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState({ name: "", amount: "", frequency: "monthly", description: "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    const found = {};
    if (!form.name.trim()) found.name = "Enter a name.";
    if (!(Number(form.amount) > 0)) found.amount = "Enter an amount above zero.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      await fees.createStructure({ ...form, amount: String(form.amount) });
      toast.success("Fee structure added.");
      onSaved();
    } catch (err) {
      setErrors({ ...fieldErrors(err), form: errorMessage(err) });
    } finally { setBusy(false); }
  };
  return (
    <Modal title="New fee structure" onClose={onClose}>
      <form onSubmit={submit} noValidate>
        {errors.form && <div className="notice notice-error" role="alert">{errors.form}</div>}
        <Field label="Name" name="name" value={form.name} onChange={set} error={errors.name} />
        <Field label="Amount (₹)" name="amount" type="number" min="0.01" step="0.01" value={form.amount} onChange={set} error={errors.amount} />
        <Field label="Frequency" name="frequency" as="select" value={form.frequency} onChange={set}>
          <option value="monthly">Monthly</option><option value="semester">Per semester</option><option value="yearly">Yearly</option><option value="one_time">One time</option>
        </Field>
        <Field label="Description" name="description" as="textarea" rows={2} value={form.description} onChange={set} />
        <div className="form-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Add structure"}</button></div>
      </form>
    </Modal>
  );
}

function ChargeModal({ onClose, onSaved }) {
  const toast = useToast();
  const people = useLoad(() => students.list({ status: "active", page_size: 100, ordering: "name" }), []);
  const structures = useLoad(() => fees.structures(), []);
  const [form, setForm] = useState({ student_id: "", structure_id: "", due_date: "", amount_due: "", description: "" });
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    const found = {};
    if (!form.student_id) found.student_id = "Choose a student.";
    if (!form.structure_id) found.structure_id = "Choose a fee structure.";
    if (!form.due_date) found.due_date = "Choose the due date.";
    if (form.amount_due !== "" && !(Number(form.amount_due) > 0)) found.amount_due = "Enter an amount above zero, or leave blank.";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      const body = { student_id: Number(form.student_id), structure_id: Number(form.structure_id), due_date: form.due_date, description: form.description };
      if (form.amount_due !== "") body.amount_due = String(form.amount_due);
      await fees.create(body);
      toast.success("Fee charged.");
      onSaved();
    } catch (err) {
      setErrors({ ...fieldErrors(err), form: errorMessage(err) });
    } finally { setBusy(false); }
  };
  return (
    <Modal title="Charge a fee" onClose={onClose}>
      <form onSubmit={submit} noValidate>
        {errors.form && <div className="notice notice-error" role="alert">{errors.form}</div>}
        <Field label="Student" name="student_id" as="select" value={form.student_id} onChange={set} error={errors.student_id}>
          <option value="">Choose…</option>
          {(people.data?.items || []).map((s) => <option key={s.id} value={s.id}>{s.full_name} ({s.enrollment_no})</option>)}
        </Field>
        <Field label="Fee structure" name="structure_id" as="select" value={form.structure_id} onChange={set} error={errors.structure_id}>
          <option value="">Choose…</option>
          {(structures.data || []).filter((s) => s.is_active).map((s) => <option key={s.id} value={s.id}>{s.name} ({formatMoney(s.amount)})</option>)}
        </Field>
        <Field label="Due date" name="due_date" type="date" value={form.due_date} onChange={set} error={errors.due_date} />
        <Field label="Amount override (₹)" name="amount_due" type="number" min="0.01" step="0.01" value={form.amount_due} onChange={set} error={errors.amount_due} hint="Leave blank to use the structure’s amount." />
        <Field label="Note" name="description" value={form.description} onChange={set} hint="For example: November 2026" />
        <div className="form-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Charge fee"}</button></div>
      </form>
    </Modal>
  );
}

export default function FeeList() {
  const { isAdmin } = useAuth();
  const base = useBase();
  const q = usePagedQuery(fees.list, { ordering: "-due_date" });
  const [modal, setModal] = useState(null);

  const columns = [
    { header: "Student", render: (f) => <>{f.student_name}<br /><small className="muted">{f.enrollment_no}</small></> },
    { header: "Fee", render: (f) => <>{f.structure_name}<br /><small className="muted">{f.description}</small></> },
    { header: "Due date", render: (f) => formatDate(f.due_date) },
    { header: "Amount", className: "num", render: (f) => formatMoney(f.amount_due) },
    { header: "Paid", className: "num", render: (f) => formatMoney(f.amount_paid) },
    { header: "Balance", className: "num", render: (f) => formatMoney(f.balance) },
    { header: "Status", render: (f) => <StatusBadge value={f.status} /> },
  ];
  if (isAdmin) columns.push({ header: "Actions", className: "col-actions", render: (f) => (
    <>
      <Link className="btn btn-small" to={`${base}/payments?fee_id=${f.id}`}><History aria-hidden="true" />History</Link>{" "}
      {f.status !== "paid" && <Link className="btn btn-small btn-primary" to={`${base}/payments/new?fee=${f.id}`}><CreditCard aria-hidden="true" />Record payment</Link>}
    </>
  ) });

  return (
    <>
      <PageHeader icon={Wallet} title="Fees" subtitle="Balances are worked out from recorded payments."
        actions={isAdmin && <><button className="btn" onClick={() => setModal("structure")}><Layers aria-hidden="true" />New fee structure</button><button className="btn btn-primary" onClick={() => setModal("charge")}><FilePlus2 aria-hidden="true" />Charge a fee</button></>} />
      <FeeStats refresh={q.data} />
      <InfoBox>
        <ul>
          <li><strong>Pending</strong>: nothing paid yet and not due yet. <strong>Partial</strong>: part-paid. <strong>Overdue</strong>: past the due date and not fully paid. <strong>Paid</strong>: settled in full.</li>
          <li>Paid amount and balance are added up from the payment records, so they can never disagree with the payment history.</li>
          {isAdmin ? <li>A <strong>fee structure</strong> is a template (name, amount, how often). <strong>Charge a fee</strong> applies it to a student for a due date.</li> : <li>You can view fees and payment status. Charging fees and recording payments is done by an administrator.</li>}
        </ul>
      </InfoBox>
      <div className="toolbar">
        <SearchInput value={q.params.q} onChange={(v) => q.update({ q: v })} placeholder="Student name or enrollment no" />
        <select aria-label="Status" value={q.params.status || ""} onChange={(e) => q.update({ status: e.target.value })}>
          <option value="">All statuses</option><option value="pending">Pending</option><option value="partial">Partially paid</option><option value="overdue">Overdue</option><option value="paid">Paid</option>
        </select>
        <label className="inline-label">Due from <input type="date" value={q.params.due_from || ""} onChange={(e) => q.update({ due_from: e.target.value })} /></label>
        <label className="inline-label">to <input type="date" value={q.params.due_to || ""} onChange={(e) => q.update({ due_to: e.target.value })} /></label>
      </div>
      <DataTable columns={columns} rows={q.data?.items} loading={q.loading} error={q.error} onRetry={q.reload}
        empty={{ icon: Wallet, title: "No fee records", hint: isAdmin ? "Create a fee structure, then charge it to students." : "No fees match your filters." }} />
      <Pagination data={q.data} onPage={q.setPage} />
      {modal === "structure" && <StructureModal onClose={() => setModal(null)} onSaved={() => setModal(null)} />}
      {modal === "charge" && <ChargeModal onClose={() => setModal(null)} onSaved={() => { setModal(null); q.reload(); }} />}
    </>
  );
}
