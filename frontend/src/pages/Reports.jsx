import { useState } from "react";
import { reports } from "../api/endpoints.js";
import { useLoad } from "../hooks/usePagedQuery.js";
import { useToast } from "../context/ToastContext.jsx";
import { EmptyState, ErrorNotice, InfoBox, Loading, PageHeader } from "../components/ui.jsx";
import { BarChart3, Download } from "lucide-react";
import { errorMessage } from "../utils/errors.js";
import { saveBlob } from "../utils/download.js";
import { titleCase, today } from "../utils/format.js";

const REPORTS = [
  { key: "registrations", label: "Student registrations", dates: true },
  { key: "occupancy", label: "Room occupancy", dates: false },
  { key: "available", label: "Available rooms", dates: false, path: "occupancy", extra: { available_only: true } },
  { key: "fees", label: "Fee collections", dates: true },
  { key: "outstanding", label: "Outstanding fees", dates: true, optionalDates: true },
  { key: "attendance", label: "Attendance summary", dates: true },
];

const DESCRIPTIONS = {
  registrations: "Students admitted in the chosen dates, with contact details, status and current room.",
  occupancy: "Every room with its capacity, occupied beds, free beds and status, plus overall bed occupancy.",
  available: "Only rooms that are open and still have free beds. Use it when placing new students.",
  fees: "Payments received in the chosen dates, with method, reference and who recorded each one.",
  outstanding: "Fees with an unpaid balance. Leave the dates empty to see all of them, or limit by due date.",
  attendance: "Days present, absent and on leave for each student in the chosen dates, with attendance percentage.",
};

export default function Reports() {
  const toast = useToast();
  const [key, setKey] = useState("occupancy");
  const [range, setRange] = useState({ date_from: new Date(Date.now() - 29 * 864e5).toLocaleDateString("en-CA"), date_to: today() });
  const [busy, setBusy] = useState(false);
  const def = REPORTS.find((r) => r.key === key);
  const params = { ...(def.extra || {}), ...(def.dates ? (def.optionalDates ? Object.fromEntries(Object.entries(range).filter(([, v]) => v)) : range) : {}) };
  const r = useLoad(() => reports.get(def.path || def.key, params), [key, range.date_from, range.date_to]);

  const download = async () => {
    setBusy(true);
    try {
      const res = await reports.csv(def.path || def.key, params);
      saveBlob(res.data, `${def.key}-report.csv`);
    } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
  };

  const d = r.data;
  return (
    <>
      <PageHeader icon={BarChart3} title="Reports" subtitle="Choose a report, set the dates, and download it as CSV." />
      <InfoBox title={`About: ${def.label}`}>
        <p>{DESCRIPTIONS[def.key]}</p>
        <p className="muted">CSV files open in Excel or Google Sheets. Text that could be read as a formula is made safe automatically.</p>
      </InfoBox>
      <div className="toolbar">
        <select aria-label="Report" value={key} onChange={(e) => setKey(e.target.value)}>{REPORTS.map((x) => <option key={x.key} value={x.key}>{x.label}</option>)}</select>
        {def.dates && <>
          <label className="inline-label">From <input type="date" max={today()} value={range.date_from} onChange={(e) => setRange((x) => ({ ...x, date_from: e.target.value }))} /></label>
          <label className="inline-label">to <input type="date" max={today()} value={range.date_to} onChange={(e) => setRange((x) => ({ ...x, date_to: e.target.value }))} /></label>
        </>}
        <button className="btn btn-primary" onClick={download} disabled={busy || !d}><Download aria-hidden="true" />{busy ? "Preparing…" : "Download CSV"}</button>
      </div>
      {r.loading && !d ? <Loading /> : r.error ? <ErrorNotice message={r.error} onRetry={r.reload} /> : d && (
        <section className="panel">
          <h2>{d.title}</h2>
          <div className="summary-strip">
            {Object.entries(d.summary).map(([k, v]) => <span key={k}><small>{titleCase(k)}</small><strong>{v ?? "–"}</strong></span>)}
          </div>
          {d.rows.length === 0 ? <EmptyState title="No rows for these filters" /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr>{d.columns.map((c) => <th key={c}>{c}</th>)}</tr></thead>
                <tbody>{d.rows.map((row, i) => <tr key={i}>{row.map((cell, j) => <td key={j} data-label={d.columns[j]}>{String(cell ?? "")}</td>)}</tr>)}</tbody>
              </table>
            </div>
          )}
        </section>
      )}
    </>
  );
}
