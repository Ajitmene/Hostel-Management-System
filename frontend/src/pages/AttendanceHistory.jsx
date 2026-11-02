import { useState } from "react";
import { attendance, students } from "../api/endpoints.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useLoad, usePagedQuery } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { Modal } from "../components/Modal.jsx";
import { Field, InfoBox, PageHeader, StatusBadge } from "../components/ui.jsx";
import { HistoryStats } from "../components/PageStats.jsx";
import { History, ListChecks, Percent, Pencil } from "lucide-react";
import { errorMessage } from "../utils/errors.js";
import { formatDate, today } from "../utils/format.js";

function CorrectionModal({ record, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState({ status: record.status, remarks: record.remarks, reason: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  const submit = async (e) => {
    e.preventDefault();
    if (form.reason.trim().length < 3) return setError("Explain why this record is being corrected.");
    setBusy(true);
    try {
      await attendance.correct(record.id, { ...form, reason: form.reason.trim() });
      toast.success("Attendance corrected and logged.");
      onSaved();
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  };
  return (
    <Modal title={`Correct ${record.student_name}, ${formatDate(record.date)}`} onClose={onClose}>
      <form onSubmit={submit} noValidate>
        {error && <div className="notice notice-error" role="alert">{error}</div>}
        <Field label="Status" name="status" as="select" value={form.status} onChange={set}>
          <option value="present">Present</option><option value="absent">Absent</option><option value="leave">Leave</option>
        </Field>
        <Field label="Remarks" name="remarks" value={form.remarks} onChange={set} maxLength={255} />
        <Field label="Reason for correction" name="reason" as="textarea" rows={2} value={form.reason} onChange={set} hint="Saved in the audit log with the old and new values." />
        <div className="form-actions"><button type="button" className="btn" onClick={onClose}>Cancel</button><button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save correction"}</button></div>
      </form>
    </Modal>
  );
}

function Records() {
  const { isAdmin, can } = useAuth();
  const q = usePagedQuery(attendance.list, { date_from: "", date_to: "" }, 15);
  const people = useLoad(() => (can("students.view") ? students.list({ page_size: 100, ordering: "name" }) : Promise.resolve({ data: null })), []);
  const [fixing, setFixing] = useState(null);
  const columns = [
    { header: "Date", render: (a) => formatDate(a.date) },
    { header: "Student", render: (a) => <>{a.student_name}<br /><small className="muted">{a.enrollment_no}</small></> },
    { header: "Status", render: (a) => <StatusBadge value={a.status} /> },
    { header: "Remarks", render: (a) => a.remarks || "–" },
    { header: "Recorded by", render: (a) => a.recorded_by },
  ];
  if (isAdmin) columns.push({ header: "Actions", className: "col-actions", render: (a) => <button className="btn btn-small" onClick={() => setFixing(a)}><Pencil aria-hidden="true" />Correct</button> });
  return (
    <>
      <div className="toolbar">
        {people.data && (
          <select aria-label="Student" value={q.params.student_id || ""} onChange={(e) => q.update({ student_id: e.target.value })}>
            <option value="">All students</option>
            {people.data.items.map((s) => <option key={s.id} value={s.id}>{s.full_name}</option>)}
          </select>
        )}
        <select aria-label="Status" value={q.params.status || ""} onChange={(e) => q.update({ status: e.target.value })}>
          <option value="">Any status</option><option value="present">Present</option><option value="absent">Absent</option><option value="leave">Leave</option>
        </select>
        <label className="inline-label">From <input type="date" max={today()} value={q.params.date_from || ""} onChange={(e) => q.update({ date_from: e.target.value })} /></label>
        <label className="inline-label">to <input type="date" max={today()} value={q.params.date_to || ""} onChange={(e) => q.update({ date_to: e.target.value })} /></label>
      </div>
      <DataTable columns={columns} rows={q.data?.items} loading={q.loading} error={q.error} onRetry={q.reload} empty={{ title: "No attendance records", hint: "Try a wider date range." }} />
      <Pagination data={q.data} onPage={q.setPage} />
      {fixing && <CorrectionModal record={fixing} onClose={() => setFixing(null)} onSaved={() => { setFixing(null); q.reload(); }} />}
    </>
  );
}

function Summary() {
  const [range, setRange] = useState({ date_from: new Date(Date.now() - 29 * 864e5).toLocaleDateString("en-CA"), date_to: today() });
  const s = useLoad(() => attendance.summary(range), [range.date_from, range.date_to]);
  const d = s.data;
  return (
    <>
      <div className="toolbar">
        <label className="inline-label">From <input type="date" max={today()} value={range.date_from} onChange={(e) => e.target.value && setRange((r) => ({ ...r, date_from: e.target.value }))} /></label>
        <label className="inline-label">to <input type="date" max={today()} value={range.date_to} onChange={(e) => e.target.value && setRange((r) => ({ ...r, date_to: e.target.value }))} /></label>
        {d && <span className="muted">Overall attendance: <strong>{d.overall_percentage ?? "–"}{d.overall_percentage != null && "%"}</strong></span>}
      </div>
      <p className="muted">Percentage = days present ÷ days marked.</p>
      <DataTable rows={d?.students} rowKey="student_id" loading={s.loading} error={s.error} onRetry={s.reload} empty={{ title: "No attendance in this period" }}
        columns={[
          { header: "Student", render: (r) => <>{r.full_name}<br /><small className="muted">{r.enrollment_no}</small></> },
          { header: "Present", className: "num", render: (r) => r.present },
          { header: "Absent", className: "num", render: (r) => r.absent },
          { header: "Leave", className: "num", render: (r) => r.leave },
          { header: "Marked", className: "num", render: (r) => r.marked_days },
          { header: "Attendance", render: (r) => r.percentage == null ? "–" : (
            <span className="pct"><span className="pct-bar"><i style={{ width: `${r.percentage}%` }} className={r.percentage < 75 ? "low" : ""} /></span>{r.percentage}%</span>
          ) },
        ]} />
    </>
  );
}

export default function AttendanceHistory() {
  const [tab, setTab] = useState("records");
  return (
    <>
      <PageHeader icon={History} title="Attendance history" subtitle="Look back at who was present, and how attendance is trending." />
      <HistoryStats />
      <InfoBox>
        <ul>
          <li><strong>Records</strong> lists every saved entry; filter by student, status or dates. <strong>Percentages</strong> shows days present ÷ days marked for each student.</li>
          <li>Students under 75% are highlighted in red so they are easy to spot.</li>
        </ul>
      </InfoBox>
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "records"} className={tab === "records" ? "tab on" : "tab"} onClick={() => setTab("records")}><ListChecks size={16} aria-hidden="true" />Records</button>
        <button role="tab" aria-selected={tab === "summary"} className={tab === "summary" ? "tab on" : "tab"} onClick={() => setTab("summary")}><Percent size={16} aria-hidden="true" />Percentages</button>
      </div>
      {tab === "records" ? <Records /> : <Summary />}
    </>
  );
}
