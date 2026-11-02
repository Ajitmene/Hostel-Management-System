import { Link, useParams } from "react-router-dom";
import { fees } from "../api/endpoints.js";
import { useBase } from "../context/AuthContext.jsx";
import { useLoad } from "../hooks/usePagedQuery.js";
import { ErrorNotice, Loading, PageHeader } from "../components/ui.jsx";
import { ArrowLeft, Printer, ReceiptText } from "lucide-react";
import { formatDate, formatMoney, titleCase } from "../utils/format.js";

export default function Receipt() {
  const { id } = useParams();
  const base = useBase();
  const r = useLoad(() => fees.receipt(id), [id]);
  if (r.loading) return <Loading />;
  if (r.error) return <ErrorNotice message={r.error} onRetry={r.reload} />;
  const p = r.data;
  return (
    <>
      <PageHeader icon={ReceiptText} title="Payment receipt" subtitle="Print this page or save it as a PDF from the print dialog." actions={<><Link className="btn" to={`${base}/payments`}><ArrowLeft aria-hidden="true" />Back to payments</Link><button className="btn btn-primary" onClick={() => window.print()}><Printer aria-hidden="true" />Print</button></>} />
      <article className="receipt">
        <header>
          <div><strong>Hostel Desk</strong><small>Payment receipt</small></div>
          <div className="receipt-no"><small>Receipt no</small><strong>{p.receipt_number}</strong></div>
        </header>
        <dl className="details">
          <dt>Received from</dt><dd>{p.student_name} ({p.enrollment_no})</dd>
          <dt>Date</dt><dd>{formatDate(p.payment_date)}</dd>
          <dt>For</dt><dd>{p.structure_name}{p.fee_description ? ` · ${p.fee_description}` : ""}</dd>
          <dt>Method</dt><dd>{titleCase(p.method)}{p.transaction_reference ? ` · ${p.transaction_reference}` : ""}</dd>
          <dt>Recorded by</dt><dd>{p.recorded_by}</dd>
        </dl>
        <div className="receipt-total"><span>Amount received</span><strong>{formatMoney(p.amount)}</strong></div>
        <table className="table receipt-table">
          <tbody>
            <tr><td>Total fee</td><td className="num">{formatMoney(p.amount_due)}</td></tr>
            <tr><td>Paid to date (including this payment)</td><td className="num">{formatMoney(p.total_paid)}</td></tr>
            <tr><td>Balance remaining</td><td className="num"><strong>{formatMoney(p.balance_after)}</strong></td></tr>
          </tbody>
        </table>
        <footer>Recorded manually. This is not a bank or gateway confirmation.</footer>
      </article>
    </>
  );
}
