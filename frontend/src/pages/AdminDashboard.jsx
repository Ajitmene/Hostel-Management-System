import { Link } from "react-router-dom";
import { AlertTriangle, BedDouble, CalendarCheck, CreditCard, DoorOpen, GraduationCap, HandCoins, KeyRound, LayoutDashboard, Plus, UserCog, Users, Wallet } from "lucide-react";
import { dashboard, fees, rooms } from "../api/endpoints.js";
import { useLoad } from "../hooks/usePagedQuery.js";
import { ErrorNotice, InfoBox, Loading, PageHeader, StatCard } from "../components/ui.jsx";
import { formatDateTime, formatMoney, titleCase } from "../utils/format.js";

const ACTIVITY = {
  student: [GraduationCap, "blue"], room: [BedDouble, "teal"], allocation: [BedDouble, "teal"], payment: [CreditCard, "green"],
  fee: [Wallet, "amber"], fee_structure: [Wallet, "amber"], attendance: [CalendarCheck, "violet"], employee: [UserCog, "blue"], user: [KeyRound, "violet"],
};

function BedMeter({ occupied, total }) {
  const pct = total ? Math.round((occupied * 100) / total) : 0;
  return (
    <section className="bedmeter" aria-label="Bed occupancy">
      <div className="bedmeter-figure"><strong>{occupied}</strong><span>of {total} beds taken</span></div>
      <div className="bedmeter-bar" role="img" aria-label={`${pct}% of beds occupied`}><div style={{ width: `${pct}%` }} /></div>
      <small>{pct}% occupied across open rooms · {Math.max(total - occupied, 0)} beds free</small>
    </section>
  );
}

function ByBlock({ items }) {
  const blocks = {};
  items.filter((r) => r.is_active).forEach((r) => {
    const b = (blocks[r.block] ||= { beds: 0, taken: 0, rooms: 0 });
    b.beds += r.capacity; b.taken += r.occupancy; b.rooms += 1;
  });
  const rows = Object.entries(blocks).sort(([a], [b]) => a.localeCompare(b));
  if (!rows.length) return <p className="muted">Add rooms to see occupancy by block.</p>;
  return rows.map(([name, b]) => (
    <div key={name} className="block-row">
      <strong>Block {name}</strong>
      <div className="bar" role="img" aria-label={`Block ${name}: ${b.taken} of ${b.beds} beds`}><i style={{ width: `${b.beds ? (b.taken * 100) / b.beds : 0}%` }} /></div>
      <small className="muted">{b.taken}/{b.beds} beds · {b.rooms} rooms</small>
    </div>
  ));
}

export default function AdminDashboard() {
  const { data: d, loading, error, reload } = useLoad(() => dashboard.summary());
  const money = useLoad(() => fees.summary());
  const blocks = useLoad(() => rooms.list({ page_size: 100 }));
  if (loading && !d) return <Loading />;
  if (error) return <ErrorNotice message={error} onRetry={reload} />;
  const att = d.attendance_today;
  const marked = att.present + att.absent + att.leave;
  const total = marked + att.unmarked;
  const w = (n) => `${total ? (n * 100) / total : 0}%`;
  const m = money.data;

  return (
    <>
      <PageHeader icon={LayoutDashboard} title="Hostel overview" subtitle="A live picture of residents, rooms, money and attendance." />
      <InfoBox title="How to read this page">
        <ul>
          <li>Every figure is calculated from the database when the page opens; nothing is typed in by hand.</li>
          <li>Bed figures count <strong>open</strong> rooms only. Closed rooms are left out.</li>
          <li><strong>Pending fees</strong> = everything charged minus everything collected. <strong>Overdue</strong> counts fees past their due date that are not fully paid.</li>
          <li>Click a card to jump to the matching list.</li>
        </ul>
      </InfoBox>
      <BedMeter occupied={d.occupied_beds} total={d.total_beds} />
      <div className="stats">
        <StatCard icon={GraduationCap} tone="blue" label="Active students" value={d.total_students} to="/admin/students" />
        <StatCard icon={Users} tone="violet" label="Employees" value={d.total_employees} to="/admin/employees" />
        <StatCard icon={BedDouble} tone="teal" label="Open rooms" value={d.total_rooms} hint={`${d.occupied_rooms} with occupants`} to="/admin/rooms" />
        <StatCard icon={DoorOpen} tone="green" label="Rooms with free beds" value={d.available_rooms} to="/admin/rooms" />
        <StatCard icon={Wallet} tone="amber" label="Pending fees" value={formatMoney(d.pending_fees)} to="/admin/fees" />
        <StatCard icon={AlertTriangle} tone="red" label="Overdue fees" value={d.overdue_fee_count} hint={m ? formatMoney(m.overdue_amount) : undefined} to="/admin/fees" />
      </div>

      <div className="grid-2">
        <section className="panel">
          <h2><HandCoins size={18} aria-hidden="true" />Money this month</h2>
          {m ? (
            <div className="summary-strip">
              <span><small>Collected this month</small><strong>{formatMoney(m.collected_this_month)}</strong></span>
              <span><small>Payments</small><strong>{m.payments_this_month}</strong></span>
              <span><small>Still to collect</small><strong>{formatMoney(m.outstanding)}</strong></span>
            </div>
          ) : <Loading />}
          <p className="muted">Payments are entered manually; this is the total of recorded payments dated this month.</p>
          <Link className="btn btn-small" to="/admin/payments">View payment history</Link>
        </section>
        <section className="panel">
          <h2><CalendarCheck size={18} aria-hidden="true" />Attendance today</h2>
          <div className="att-bar" role="img" aria-label={`${att.present} present, ${att.absent} absent, ${att.leave} on leave, ${att.unmarked} not marked`}>
            <i className="p" style={{ width: w(att.present) }} /><i className="a" style={{ width: w(att.absent) }} /><i className="l" style={{ width: w(att.leave) }} />
          </div>
          <div className="stats stats-tight">
            <StatCard label="Present" value={att.present} tone="green" />
            <StatCard label="Absent" value={att.absent} tone="red" />
            <StatCard label="On leave" value={att.leave} tone="amber" />
            <StatCard label="Not yet marked" value={att.unmarked} tone="blue" />
          </div>
          {att.unmarked > 0 && <Link className="btn btn-small btn-primary" to="/admin/attendance">Record today’s attendance</Link>}
        </section>
      </div>

      <div className="grid-2">
        <section className="panel">
          <h2><BedDouble size={18} aria-hidden="true" />Occupancy by block</h2>
          {blocks.data ? <ByBlock items={blocks.data.items} /> : <Loading />}
        </section>
        <section className="panel">
          <h2>Recent activity</h2>
          {d.recent_activities.length === 0 ? <p className="muted">No activity recorded yet. Actions such as adding a student or recording a payment appear here.</p> : (
            <ul className="activity">
              {d.recent_activities.map((a) => {
                const [Icon, tone] = ACTIVITY[a.entity_type] || [KeyRound, "violet"];
                return (
                  <li key={a.id}>
                    <span className={`act-icon tile-${tone}`} aria-hidden="true"><Icon size={16} /></span>
                    <span className="act-main"><span>{titleCase(a.action.replace(".", " "))}</span><small>{a.user || "system"} · {formatDateTime(a.created_at)}</small></span>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
      </div>

      <section className="panel">
        <h2>Quick actions</h2>
        <div className="quick-links">
          <Link className="btn" to="/admin/students/new"><Plus aria-hidden="true" />Add student</Link>
          <Link className="btn" to="/admin/allocations"><BedDouble aria-hidden="true" />Allocate a room</Link>
          <Link className="btn" to="/admin/payments/new"><CreditCard aria-hidden="true" />Record payment</Link>
          <Link className="btn" to="/admin/attendance"><CalendarCheck aria-hidden="true" />Take attendance</Link>
          <Link className="btn" to="/admin/employees/new"><UserCog aria-hidden="true" />Add employee</Link>
        </div>
      </section>
    </>
  );
}
