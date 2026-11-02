import { Link, useParams } from "react-router-dom";
import { attendance, fees, students } from "../api/endpoints.js";
import { useAuth, useBase } from "../context/AuthContext.jsx";
import { useLoad } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import { Avatar, ErrorNotice, InfoBox, Loading, PageHeader, StatCard, StatusBadge } from "../components/ui.jsx";
import { AlertTriangle, BedDouble, CalendarCheck, GraduationCap, Percent, Wallet } from "lucide-react";
import { formatDate, formatMoney } from "../utils/format.js";

export default function StudentDetail() {
  const { id } = useParams();
  const { isAdmin, can } = useAuth();
  const base = useBase();
  const s = useLoad(() => students.get(id), [id]);
  const f = useLoad(() => (can("fees.view") ? fees.list({ student_id: id, page_size: 20 }) : Promise.resolve({ data: null })), [id]);
  const a = useLoad(() => (can("attendance.view") ? attendance.summary({ student_id: id, date_from: new Date(Date.now() - 30 * 864e5).toLocaleDateString("en-CA") }) : Promise.resolve({ data: null })), [id]);

  if (s.loading) return <Loading />;
  if (s.error) return <ErrorNotice message={s.error} onRetry={s.reload} />;
  const st = s.data;
  const att = a.data?.students?.[0];

  return (
    <>
      <PageHeader icon={GraduationCap} title={st.full_name} subtitle={`Enrollment ${st.enrollment_no}`}
        actions={<>
          <Link className="btn" to={`${base}/students`}>Back to students</Link>
          {isAdmin && <Link className="btn btn-primary" to={`${base}/students/${st.id}/edit`}>Edit</Link>}
        </>} />
      <div className="stats">
        <StatCard icon={BedDouble} tone="teal" label="Room" value={st.room ? `${st.room.block}-${st.room.room_number}` : "None"} hint={st.room ? "Currently allocated" : "Not allocated yet"} />
        {a.data && <StatCard icon={Percent} tone="violet" label="Attendance, 30 days" value={att && att.marked_days ? `${att.percentage}%` : "–"} hint={att && att.marked_days ? `${att.marked_days} days marked` : "No records yet"} />}
        {f.data && <StatCard icon={Wallet} tone="amber" label="Fee balance" value={formatMoney(f.data.items.reduce((n, x) => n + Number(x.balance), 0))} hint={`${f.data.items.length} fee record${f.data.items.length === 1 ? "" : "s"}`} />}
        {f.data && <StatCard icon={f.data.items.some((x) => x.status === "overdue") ? AlertTriangle : CalendarCheck} tone={f.data.items.some((x) => x.status === "overdue") ? "red" : "green"} label="Overdue fees" value={f.data.items.filter((x) => x.status === "overdue").length} />}
      </div>
      <InfoBox title="About this record">
        <p>This page brings together everything held about the student. Room, attendance and fee panels only appear if your account may view them.</p>
      </InfoBox>
      <div className="grid-2">
        <section className="panel">
          <h2>Details</h2>
          <dl className="details">
            <dt>Status</dt><dd><StatusBadge value={st.status} /></dd>
            <dt>Email</dt><dd>{st.email}</dd>
            <dt>Phone</dt><dd>{st.phone}</dd>
            <dt>Gender</dt><dd className="cap">{st.gender}</dd>
            <dt>Address</dt><dd>{st.address}</dd>
            <dt>Guardian</dt><dd>{st.guardian_name} · {st.guardian_phone}</dd>
            <dt>Admitted</dt><dd>{formatDate(st.admission_date)}</dd>
            <dt>Room</dt>
            <dd>{st.room ? (can("rooms.view") ? <Link to={`${base}/rooms/${st.room.id}`}>{st.room.block}-{st.room.room_number}</Link> : `${st.room.block}-${st.room.room_number}`) : <span className="muted">Not allocated</span>}</dd>
          </dl>
        </section>
        {a.data && (
          <section className="panel">
            <h2>Attendance, last 30 days</h2>
            {att && att.marked_days ? (
              <>
                <p className="big-number">{att.percentage}%</p>
                <p className="muted">{att.present} present · {att.absent} absent · {att.leave} on leave ({att.marked_days} days marked)</p>
              </>
            ) : <p className="muted">No attendance recorded in this period.</p>}
          </section>
        )}
      </div>
      {f.data && (
        <section className="panel">
          <h2>Fees</h2>
          <DataTable rows={f.data.items} loading={f.loading} empty={{ title: "No fees charged yet" }}
            columns={[
              { header: "Fee", render: (x) => <>{x.structure_name}<br /><small className="muted">{x.description}</small></> },
              { header: "Due date", render: (x) => formatDate(x.due_date) },
              { header: "Amount", className: "num", render: (x) => formatMoney(x.amount_due) },
              { header: "Paid", className: "num", render: (x) => formatMoney(x.amount_paid) },
              { header: "Balance", className: "num", render: (x) => formatMoney(x.balance) },
              { header: "Status", render: (x) => <StatusBadge value={x.status} /> },
            ]} />
        </section>
      )}
    </>
  );
}
