import { Link } from "react-router-dom";
import { BedDouble, CalendarCheck, CheckCircle2, ClipboardList, DoorOpen, GraduationCap, History, LayoutDashboard, ListChecks, Users, Wallet } from "lucide-react";
import { dashboard } from "../api/endpoints.js";
import { useAuth } from "../context/AuthContext.jsx";
import { useLoad } from "../hooks/usePagedQuery.js";
import { ErrorNotice, InfoBox, Loading, PageHeader, StatCard } from "../components/ui.jsx";

const LINK_ICONS = { Students: GraduationCap, Rooms: BedDouble, Fees: Wallet, "Record attendance": CalendarCheck, "Attendance history": History };
const PERMISSIONS = {
  "students.view": "View student records",
  "rooms.view": "See rooms and which beds are free",
  "fees.view": "See fees, payments and receipts",
  "attendance.view": "Look through attendance history",
  "attendance.record": "Record daily attendance",
};

export default function EmployeeDashboard() {
  const { user } = useAuth();
  const { data: d, loading, error, reload } = useLoad(() => dashboard.summary());
  if (loading && !d) return <Loading />;
  if (error) return <ErrorNotice message={error} onRetry={reload} />;
  const att = d.attendance_today;

  return (
    <>
      <PageHeader icon={LayoutDashboard} title={`Welcome, ${user.first_name || "team"}`} subtitle="What needs your attention today." />
      <InfoBox title="Your access">
        <p>You can see only the areas an administrator has switched on for your account. If something you need is missing, ask an administrator.</p>
        {user.permissions.length ? (
          <ul className="perm-list">{user.permissions.map((p) => <li key={p}><CheckCircle2 size={16} aria-hidden="true" />{PERMISSIONS[p] || p}</li>)}</ul>
        ) : <p className="muted">No permissions have been assigned to your account yet.</p>}
      </InfoBox>

      <section className="panel">
        <h2><ListChecks size={18} aria-hidden="true" />Today’s tasks</h2>
        {d.tasks.length === 0 ? <p className="muted">Nothing outstanding right now.</p> : (
          <ul className="tasks">{d.tasks.map((t) => <li key={t}><CheckCircle2 size={16} aria-hidden="true" />{t}</li>)}</ul>
        )}
      </section>

      <div className="stats">
        {d.total_students != null && <StatCard icon={Users} tone="blue" label="Active students" value={d.total_students} />}
        {d.available_rooms != null && <StatCard icon={DoorOpen} tone="green" label="Rooms with free beds" value={d.available_rooms} />}
        {att && (
          <>
            <StatCard icon={CheckCircle2} tone="green" label="Present today" value={att.present} />
            <StatCard icon={CalendarCheck} tone="red" label="Absent today" value={att.absent} />
            <StatCard icon={History} tone="amber" label="On leave" value={att.leave} />
            <StatCard icon={ClipboardList} tone="blue" label="Not yet marked" value={att.unmarked} />
          </>
        )}
      </div>

      <section className="panel">
        <h2>Quick links</h2>
        <div className="quick-links">
          {d.quick_links.map((l) => { const Icon = LINK_ICONS[l.label] || LayoutDashboard; return <Link key={l.path} className="btn" to={l.path}><Icon aria-hidden="true" />{l.label}</Link>; })}
        </div>
      </section>
    </>
  );
}
