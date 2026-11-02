import { useEffect, useState } from "react";
import { attendance } from "../api/endpoints.js";
import { useAuth, useBase } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { useLoad } from "../hooks/usePagedQuery.js";
import { Link } from "react-router-dom";
import DataTable from "../components/DataTable.jsx";
import { ErrorNotice, InfoBox, Loading, PageHeader, StatCard, StatusBadge } from "../components/ui.jsx";
import { CalendarCheck, CheckCircle2, ClipboardList, History, UserX } from "lucide-react";
import { errorMessage } from "../utils/errors.js";
import { formatDate, today } from "../utils/format.js";

const OPTIONS = [["present", "Present"], ["absent", "Absent"], ["leave", "Leave"]];

export default function AttendanceEntry() {
  const { can } = useAuth();
  const base = useBase();
  const toast = useToast();
  const [date, setDate] = useState(today());
  const roster = useLoad(() => attendance.roster(date), [date]);
  const [choices, setChoices] = useState({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => { setChoices({}); setError(""); }, [date]);

  const rows = roster.data || [];
  const open = rows.filter((r) => !r.attendance_id);
  const pick = (id, patch) => setChoices((c) => ({ ...c, [id]: { status: "", remarks: "", ...c[id], ...patch } }));
  const markAll = (status) => setChoices(Object.fromEntries(open.map((r) => [r.student_id, { remarks: "", ...choices[r.student_id], status }])));
  const ready = open.filter((r) => choices[r.student_id]?.status);
  const count = (st) => rows.filter((r) => r.status === st).length;

  const save = async () => {
    setBusy(true);
    setError("");
    try {
      await attendance.record({
        date,
        records: ready.map((r) => ({ student_id: r.student_id, status: choices[r.student_id].status, remarks: choices[r.student_id].remarks || "" })),
      });
      toast.success(`Attendance saved for ${ready.length} student${ready.length === 1 ? "" : "s"}.`);
      setChoices({});
      roster.reload();
    } catch (err) {
      setError(errorMessage(err));
      roster.reload();
    } finally { setBusy(false); }
  };

  const columns = [
    { header: "Student", render: (r) => <>{r.full_name}<br /><small className="muted">{r.enrollment_no}{r.room ? ` · ${r.room}` : ""}</small></> },
    { header: "Attendance", render: (r) => r.attendance_id ? <StatusBadge value={r.status} /> : (
      <div className="segmented" role="radiogroup" aria-label={`Attendance for ${r.full_name}`}>
        {OPTIONS.map(([value, label]) => (
          <label key={value} className={choices[r.student_id]?.status === value ? `seg seg-${value} on` : "seg"}>
            <input type="radio" name={`att-${r.student_id}`} checked={choices[r.student_id]?.status === value} onChange={() => pick(r.student_id, { status: value })} />
            {label}
          </label>
        ))}
      </div>
    ) },
    { header: "Remarks", render: (r) => r.attendance_id ? (r.remarks || "–") : (
      <input className="remarks" aria-label={`Remarks for ${r.full_name}`} maxLength={255} placeholder="Optional" value={choices[r.student_id]?.remarks || ""} onChange={(e) => pick(r.student_id, { remarks: e.target.value })} />
    ) },
  ];

  return (
    <>
      <PageHeader icon={CalendarCheck} title="Take attendance" subtitle={`Active students for ${formatDate(date)}.`}
        actions={can("attendance.view") && <Link className="btn" to={`${base}/attendance/history`}><History aria-hidden="true" />History</Link>} />
      <div className="stats">
        <StatCard icon={CheckCircle2} tone="green" label="Present" value={count("present")} />
        <StatCard icon={UserX} tone="red" label="Absent" value={count("absent")} />
        <StatCard icon={History} tone="amber" label="On leave" value={count("leave")} />
        <StatCard icon={ClipboardList} tone="blue" label="Still to mark" value={open.length} hint={`${rows.length} active students`} />
      </div>
      <InfoBox>
        <ul>
          <li>Choose Present, Absent or Leave for each student, then press <strong>Save attendance</strong>. <em>Mark all present</em> is a quick start; change the exceptions.</li>
          <li>You can save in several rounds. Students already recorded for the date show their saved status and cannot be changed here.</li>
          <li>A mistake in a saved record can be fixed only by an administrator, who must give a reason; the change is logged.</li>
        </ul>
      </InfoBox>
      <div className="toolbar">
        <label className="inline-label">Date <input type="date" value={date} max={today()} onChange={(e) => e.target.value && setDate(e.target.value)} /></label>
        {open.length > 0 && <><button className="btn btn-small" onClick={() => markAll("present")}>Mark all present</button><button className="btn btn-small" onClick={() => setChoices({})}>Clear</button></>}
        <span className="muted">{rows.length - open.length} recorded · {open.length} to do</span>
      </div>
      {error && <ErrorNotice message={error} />}
      {roster.loading && !roster.data ? <Loading /> : roster.error ? <ErrorNotice message={roster.error} onRetry={roster.reload} /> : (
        <DataTable columns={columns} rows={rows} rowKey="student_id" empty={{ title: "No active students", hint: "Add students before recording attendance." }} />
      )}
      {open.length > 0 && (
        <div className="sticky-bar">
          <span>{ready.length} of {open.length} marked</span>
          <button className="btn btn-primary" disabled={!ready.length || busy} onClick={save}>{busy ? "Saving…" : "Save attendance"}</button>
        </div>
      )}
      {rows.length > 0 && open.length === 0 && <div className="notice notice-ok">Attendance is complete for this date. Only an administrator can correct saved records.</div>}
    </>
  );
}
