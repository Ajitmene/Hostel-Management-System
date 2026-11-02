import { useState } from "react";
import { Link } from "react-router-dom";
import { rooms as roomsApi, students } from "../api/endpoints.js";
import { useAuth, useBase } from "../context/AuthContext.jsx";
import { useToast } from "../context/ToastContext.jsx";
import { usePagedQuery, useLoad } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { ConfirmDialog } from "../components/Modal.jsx";
import { Avatar, InfoBox, PageHeader, SearchInput, StatusBadge } from "../components/ui.jsx";
import { StudentStats } from "../components/PageStats.jsx";
import { GraduationCap, Pencil, Plus, UserCheck, UserX } from "lucide-react";
import { errorMessage } from "../utils/errors.js";
import { formatDate } from "../utils/format.js";

export default function StudentList() {
  const { isAdmin, can } = useAuth();
  const base = useBase();
  const toast = useToast();
  const q = usePagedQuery(students.list, { ordering: "name" });
  const rooms = useLoad(() => (can("rooms.view") ? roomsApi.list({ page_size: 100 }) : Promise.resolve({ data: null })), []);
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);

  const changeStatus = async () => {
    setBusy(true);
    try {
      await students.setStatus(confirm.student.id, confirm.status);
      toast.success(confirm.status === "active" ? "Student reactivated." : "Student deactivated. Their records were kept.");
      setConfirm(null);
      q.reload();
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { header: "Enrollment no", render: (s) => <Link to={`${base}/students/${s.id}`}>{s.enrollment_no}</Link> },
    { header: "Name", render: (s) => <span className="name-cell"><Avatar name={s.full_name} size={32} />{s.full_name}</span> },
    { header: "Contact", render: (s) => <>{s.phone}<br /><small className="muted">{s.email}</small></> },
    { header: "Room", render: (s) => (s.room ? `${s.room.block}-${s.room.room_number}` : <span className="muted">Not allocated</span>) },
    { header: "Admitted", render: (s) => formatDate(s.admission_date) },
    { header: "Status", render: (s) => <StatusBadge value={s.status} /> },
  ];
  if (isAdmin) {
    columns.push({
      header: "Actions", className: "col-actions",
      render: (s) => (
        <>
          <Link className="btn btn-small" to={`${base}/students/${s.id}/edit`}><Pencil aria-hidden="true" />Edit</Link>{" "}
          {s.status === "active" ? (
            <button className="btn btn-small btn-danger-ghost" onClick={() => setConfirm({ student: s, status: "inactive" })}><UserX aria-hidden="true" />Deactivate</button>
          ) : (
            <button className="btn btn-small" onClick={() => setConfirm({ student: s, status: "active" })}><UserCheck aria-hidden="true" />Reactivate</button>
          )}
        </>
      ),
    });
  }

  return (
    <>
      <PageHeader icon={GraduationCap} title="Students" subtitle="Search, filter and manage student records."
        actions={isAdmin && <Link className="btn btn-primary" to={`${base}/students/new`}><Plus aria-hidden="true" />Add student</Link>} />
      <StudentStats refresh={q.data} />
      <InfoBox>
        <ul>
          <li>Search by name or enrollment number, or filter by status and room.</li>
          <li>Open a student to see their room, fees and recent attendance.</li>
          {isAdmin ? <li>Deactivating a student releases their bed but <strong>keeps every fee, payment and attendance record</strong>. Students are never deleted.</li> : <li>You have read-only access to student records. Changes are made by an administrator.</li>}
        </ul>
      </InfoBox>
      <div className="toolbar">
        <SearchInput value={q.params.q} onChange={(v) => q.update({ q: v })} placeholder="Search by name or enrollment no" />
        <select aria-label="Status" value={q.params.status || ""} onChange={(e) => q.update({ status: e.target.value })}>
          <option value="">All statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="left">Left hostel</option>
        </select>
        {rooms.data && (
          <select aria-label="Room" value={q.params.room_id || ""} onChange={(e) => q.update({ room_id: e.target.value })}>
            <option value="">All rooms</option>
            {rooms.data.items.map((r) => <option key={r.id} value={r.id}>{r.block}-{r.room_number}</option>)}
          </select>
        )}
      </div>
      <DataTable columns={columns} rows={q.data?.items} loading={q.loading} error={q.error} onRetry={q.reload}
        empty={{ icon: GraduationCap, title: "No students match", hint: "Try a different search or clear the filters." }} />
      <Pagination data={q.data} onPage={q.setPage} />
      {confirm && (
        <ConfirmDialog
          title={confirm.status === "active" ? "Reactivate student?" : "Deactivate student?"}
          message={confirm.status === "active"
            ? `${confirm.student.full_name} will be marked active again.`
            : `${confirm.student.full_name} will be marked inactive and released from their room. Fee, attendance and room history are kept.`}
          confirmLabel={confirm.status === "active" ? "Reactivate" : "Deactivate"} danger={confirm.status !== "active"}
          busy={busy} onConfirm={changeStatus} onCancel={() => setConfirm(null)} />
      )}
    </>
  );
}
