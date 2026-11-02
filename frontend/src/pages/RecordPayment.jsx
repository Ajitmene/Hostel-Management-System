import { useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { fees } from "../api/endpoints.js";
import { useBase } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useLoad } from "../hooks/usePagedQuery.js";
import { ConfirmDialog } from "../components/Modal.jsx";
import { ErrorNotice, Field, InfoBox, Loading, PageHeader } from "../components/ui.jsx";
import { ArrowLeft, CreditCard } from "lucide-react";
import { errorMessage, fieldErrors } from "../utils/errors.js";
import { formatDate, formatMoney, newKey, today } from "../utils/format.js";

export default function RecordPayment() {
  const base = useBase();
  const navigate = useNavigate();
  const toast = useToast();
  const [search, setSearch] = useSearchParams();
  const feeId = search.get("fee") || "";
  const pending = useLoad(() => fees.pending({ page_size: 100, ordering: "due_date" }), []);
  const fee = useLoad(() => (feeId ? fees.get(feeId) : Promise.resolve({ data: null })), [feeId]);
  // One key per form: if the request is retried or double-clicked, the server
  // recognises it and never records the payment twice.
  const idempotencyKey = useMemo(() => newKey(), []);
  const [form, setForm] = useState({ amount: "", payment_date: today(), method: "cash", transaction_reference: "" });
  const [errors, setErrors] = useState({});
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  const f = fee.data;
  const balance = f ? Number(f.balance) : 0;

  const review = (e) => {
    e.preventDefault();
    const found = {};
    const amount = Number(form.amount);
    if (!f) found.fee = "Choose the fee being paid.";
    if (!(amount > 0)) found.amount = "Enter an amount above zero.";
    else if (!/^\d+(\.\d{1,2})?$/.test(String(form.amount))) found.amount = "Use at most two decimal places.";
    else if (f && amount > balance + 1e-9) found.amount = `Cannot exceed the balance of ${formatMoney(f.balance)}.`;
    if (!form.payment_date) found.payment_date = "Choose the payment date.";
    else if (form.payment_date > today()) found.payment_date = "The date cannot be in the future.";
    if (form.method !== "cash" && !form.transaction_reference.trim()) found.transaction_reference = "Enter the transaction or cheque reference.";
    setErrors(found);
    if (!Object.keys(found).length) setConfirm(true);
  };

  const submit = async () => {
    setBusy(true);
    try {
      const { data } = await fees.recordPayment({
        fee_id: f.id, amount: String(form.amount), payment_date: form.payment_date, method: form.method,
        transaction_reference: form.transaction_reference.trim() || null, idempotency_key: idempotencyKey,
      });
      toast.success(`Payment recorded. Receipt ${data.receipt_number}.`);
      navigate(`${base}/payments/${data.id}/receipt`);
    } catch (err) {
      setErrors({ ...fieldErrors(err), form: errorMessage(err) });
      setConfirm(false);
    } finally { setBusy(false); }
  };

  return (
    <>
      <PageHeader icon={CreditCard} title="Record a payment" subtitle="Payments are entered by hand. No online payment gateway is connected."
        actions={<Link className="btn" to={`${base}/fees`}><ArrowLeft aria-hidden="true" />Back to fees</Link>} />
      <InfoBox title="How recording works">
        <ul>
          <li>Pick the unpaid fee, enter what was received, and review before saving.</li>
          <li>You can part-pay a fee; you cannot pay more than the balance.</li>
          <li>Non-cash payments need a reference (UPI id, cheque number), and each reference can be used once.</li>
          <li>If you click twice or the connection drops, the payment is <strong>never recorded twice</strong>. Saved payments cannot be edited, which keeps the history trustworthy.</li>
        </ul>
      </InfoBox>
      {fee.error && <ErrorNotice message={fee.error} />}
      <form className="panel form-grid" onSubmit={review} noValidate>
        {errors.form && <div className="notice notice-error span-2" role="alert">{errors.form}</div>}
        <div className="span-2">
          <Field label="Fee being paid" name="fee" as="select" value={feeId} error={errors.fee}
            onChange={(e) => { setSearch(e.target.value ? { fee: e.target.value } : {}); setForm((x) => ({ ...x, amount: "" })); }}>
            <option value="">{pending.loading ? "Loading…" : "Choose an unpaid fee…"}</option>
            {(pending.data?.items || []).map((x) => <option key={x.id} value={x.id}>{x.student_name} · {x.structure_name} · balance {formatMoney(x.balance)}</option>)}
          </Field>
        </div>
        {fee.loading && feeId ? <Loading /> : f && (
          <div className="span-2 summary-strip">
            <span><small>Student</small>{f.student_name}</span>
            <span><small>Due date</small>{formatDate(f.due_date)}</span>
            <span><small>Amount due</small>{formatMoney(f.amount_due)}</span>
            <span><small>Already paid</small>{formatMoney(f.amount_paid)}</span>
            <span><small>Balance</small><strong>{formatMoney(f.balance)}</strong></span>
          </div>
        )}
        <Field label="Amount (₹)" name="amount" type="number" min="0.01" step="0.01" value={form.amount} onChange={set} error={errors.amount}
          hint={f ? <button type="button" className="link-btn" onClick={() => setForm((x) => ({ ...x, amount: f.balance }))}>Pay full balance</button> : undefined} />
        <Field label="Payment date" name="payment_date" type="date" max={today()} value={form.payment_date} onChange={set} error={errors.payment_date} />
        <Field label="Method" name="method" as="select" value={form.method} onChange={set}>
          <option value="cash">Cash</option><option value="upi">UPI</option><option value="card">Card</option><option value="bank_transfer">Bank transfer</option><option value="cheque">Cheque</option>
        </Field>
        <Field label="Transaction / cheque reference" name="transaction_reference" value={form.transaction_reference} onChange={set} error={errors.transaction_reference} hint={form.method === "cash" ? "Optional for cash." : "Required; each reference can be used once."} />
        <div className="form-actions span-2"><button className="btn btn-primary" disabled={!f}>Review payment</button></div>
      </form>
      {confirm && (
        <ConfirmDialog title="Record this payment?" confirmLabel="Record payment" busy={busy} onConfirm={submit} onCancel={() => setConfirm(false)}
          message={`${formatMoney(form.amount)} by ${form.method.replace("_", " ")} from ${f.student_name}, dated ${formatDate(form.payment_date)}. This cannot be edited afterwards.`} />
      )}
    </>
  );
}
