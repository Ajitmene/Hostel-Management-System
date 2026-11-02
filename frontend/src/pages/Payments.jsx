import { Link, useSearchParams } from "react-router-dom";
import { fees } from "../api/endpoints.js";
import { useAuth, useBase } from "../context/AuthContext.jsx";
import { usePagedQuery } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { InfoBox, PageHeader } from "../components/ui.jsx";
import { PaymentStats } from "../components/PageStats.jsx";
import { CreditCard, Plus } from "lucide-react";
import { formatDate, formatMoney, titleCase } from "../utils/format.js";

export default function Payments() {
  const { isAdmin } = useAuth();
  const base = useBase();
  const [search, setSearch] = useSearchParams();
  const q = usePagedQuery(fees.payments, { fee_id: search.get("fee_id") || "" });

  const columns = [
    { header: "Receipt", render: (p) => <Link to={`${base}/payments/${p.id}/receipt`}>{p.receipt_number}</Link> },
    { header: "Date", render: (p) => formatDate(p.payment_date) },
    { header: "Student", render: (p) => <>{p.student_name}<br /><small className="muted">{p.enrollment_no}</small></> },
    { header: "Amount", className: "num", render: (p) => formatMoney(p.amount) },
    { header: "Method", render: (p) => titleCase(p.method) },
    { header: "Reference", render: (p) => p.transaction_reference || "–" },
    { header: "Recorded by", render: (p) => p.recorded_by },
  ];

  return (
    <>
      <PageHeader icon={CreditCard} title="Payment history" subtitle="Every payment ever recorded. Entries are never edited or deleted."
        actions={isAdmin && <Link className="btn btn-primary" to={`${base}/payments/new`}><Plus aria-hidden="true" />Record payment</Link>} />
      <PaymentStats refresh={q.data} />
      <InfoBox>
        <p>Click a receipt number to open and print the receipt. Use the date filters to check a day, week or month, or open a single fee’s history from the Fees page.</p>
      </InfoBox>
      <div className="toolbar">
        <label className="inline-label">From <input type="date" value={q.params.date_from || ""} onChange={(e) => q.update({ date_from: e.target.value })} /></label>
        <label className="inline-label">to <input type="date" value={q.params.date_to || ""} onChange={(e) => q.update({ date_to: e.target.value })} /></label>
        {q.params.fee_id && <button className="btn btn-small" onClick={() => { setSearch({}); q.update({ fee_id: "" }); }}>Showing one fee · show all</button>}
      </div>
      <DataTable columns={columns} rows={q.data?.items} loading={q.loading} error={q.error} onRetry={q.reload} empty={{ icon: CreditCard, title: "No payments recorded", hint: "Payments appear here as soon as they are recorded." }} />
      <Pagination data={q.data} onPage={q.setPage} />
    </>
  );
}
