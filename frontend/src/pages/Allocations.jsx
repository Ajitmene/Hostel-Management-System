import { useState } from "react";
import { rooms, students } from "../api/endpoints.js";
import { useToast } from "../context/ToastContext.jsx";
import { useLoad, usePagedQuery } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import TransferModal from "../components/TransferModal.jsx";
import { ConfirmDialog } from "../components/Modal.jsx";
import { Field, InfoBox, PageHeader, StatusBadge } from "../components/ui.jsx";
import { AllocationStats } from "../components/PageStats.jsx";
import { ArrowRightLeft } from "lucide-react";
import { errorMessage } from "../utils/errors.js";
import { formatDate, today } from "../utils/format.js";

export default function Allocations() {
  const toast = useToast();
  const history = usePagedQuery(rooms.allocations, { active_only: true });
  const unassigned = useLoad(() => students.list({ status: "active", page_size: 100, ordering: "name" }), []);
  const free = useLoad(() => rooms.available(), []);
  const [form, setForm] = useState({ student_id: "", room_id: "", start_date: today() });
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [transfer, setTransfer] = useState(null);

  const candidates = (unassigned.data?.items || []).filter((s) => !s.room);
  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.value }));
  const refresh = () => { history.reload(); unassigned.reload(); free.reload(); };

  const ask = (e) => {
    e.preventDefault();
    if (!form.student_id || !form.room_id) return setError("Choose a student and a room.");
    setError("");
    setConfirm(true);
  };

  const allocate = async () => {
    setBusy(true);
    try {
      await rooms.allocate({ student_id: Number(form.student_id), room_id: Number(form.room_id), start_date: form.start_date });
      toast.success("Room allocated.");
      setForm({ student_id: "", room_id: "", start_date: today() });
      refresh();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
      setConfirm(false);
    }
  };

  const columns = [
    { header: "Student", render: (a) => <>{a.student_name}<br /><small className="muted">{a.enrollment_no}</small></> },
    { header: "Room", render: (a) => `${a.block}-${a.room_number}` },
    { header: "From", render: (a) => formatDate(a.start_date) },
    { header: "Until", render: (a) => (a.end_date ? formatDate(a.end_date) : "–") },
    { header: "State", render: (a) => <StatusBadge value={a.is_active ? "active" : "inactive"} /> },
    { header: "Actions", className: "col-actions", render: (a) => a.is_active && (
      <button className="btn btn-small" onClick={() => setTransfer({ id: a.id, student_name: a.student_name, room_id: a.room_id, room_number: `${a.block}-${a.room_number}` })}>Transfer</button>
    ) },
  ];

  return (
    <>
      <PageHeader icon={ArrowRightLeft} title="Room allocations" subtitle="Allocation and transfer run as one safe step, so a room can never be over-filled." />
      <AllocationStats refresh={history.data} />
      <InfoBox>
        <ul>
          <li>Only <strong>active</strong> students without a room, and rooms with at least one free bed, appear in the pickers.</li>
          <li>A student can hold <strong>one</strong> active room at a time. To move them, use <strong>Transfer</strong>; the old allocation is closed, not deleted.</li>
          <li>If two people allocate the last bed at the same moment, exactly one succeeds and the other sees a “room is full” message.</li>
        </ul>
      </InfoBox>
      <form className="panel form-grid" onSubmit={ask} noValidate>
        <h2 className="span-2">Allocate a student</h2>
        {error && <div className="notice notice-error span-2" role="alert">{error}</div>}
        <Field label="Student without a room" name="student_id" as="select" value={form.student_id} onChange={set}>
          <option value="">{candidates.length ? "Choose a student…" : "Every active student has a room"}</option>
          {candidates.map((s) => <option key={s.id} value={s.id}>{s.full_name} ({s.enrollment_no})</option>)}
        </Field>
        <Field label="Room with a free bed" name="room_id" as="select" value={form.room_id} onChange={set}>
          <option value="">{(free.data || []).length ? "Choose a room…" : "No free beds"}</option>
          {(free.data || []).map((r) => <option key={r.id} value={r.id}>{r.block}-{r.room_number} ({r.available_beds} free of {r.capacity})</option>)}
        </Field>
        <Field label="Start date" name="start_date" type="date" value={form.start_date} onChange={set} />
        <div className="form-actions"><button className="btn btn-primary">Allocate room</button></div>
      </form>

      <section className="panel">
        <div className="panel-head">
          <h2>Allocations</h2>
          <label className="check">
            <input type="checkbox" checked={!history.params.active_only} onChange={(e) => history.update({ active_only: !e.target.checked })} /> Include past allocations
          </label>
        </div>
        <DataTable columns={columns} rows={history.data?.items} loading={history.loading} error={history.error} onRetry={history.reload} empty={{ title: "No allocations yet" }} />
        <Pagination data={history.data} onPage={history.setPage} />
      </section>
      {confirm && <ConfirmDialog title="Allocate this room?" message="The student will be placed in the selected room from the start date." confirmLabel="Allocate" busy={busy} onConfirm={allocate} onCancel={() => setConfirm(false)} />}
      {transfer && <TransferModal allocation={transfer} onClose={() => setTransfer(null)} onDone={() => { setTransfer(null); refresh(); }} />}
    </>
  );
}
