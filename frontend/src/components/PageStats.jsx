import { AlertTriangle, BedDouble, Banknote, CheckCircle2, Clock, CreditCard, DoorClosed, DoorOpen, GraduationCap, HandCoins, Hourglass, Percent, ReceiptText, UserCheck, UserX, Users, Wallet } from "lucide-react";
import { attendance, employees, fees, rooms, students } from "../api/endpoints.js";
import { useLoad } from "../hooks/usePagedQuery.js";
import { formatMoney } from "../utils/format.js";
import { StatCard } from "./ui.jsx";

/** Small, self-loading summary rows shown at the top of each page.
 *  `refresh` is any value that changes when the page's data changes. */
const Row = ({ children }) => <div className="stats">{children}</div>;
const s = (r) => r.data || {};

export function StudentStats({ refresh }) {
  const d = s(useLoad(() => students.summary(), [refresh]));
  return (
    <Row>
      <StatCard icon={Users} tone="blue" label="All students" value={d.total} />
      <StatCard icon={UserCheck} tone="green" label="Active" value={d.active} hint={d.inactive || d.left ? `${d.inactive ?? 0} inactive · ${d.left ?? 0} left` : undefined} />
      <StatCard icon={DoorOpen} tone="teal" label="Have a room" value={d.allocated} />
      <StatCard icon={d.unallocated ? Hourglass : CheckCircle2} tone={d.unallocated ? "amber" : "green"} label="Waiting for a room" value={d.unallocated} hint={d.unallocated ? "Active, not yet allocated" : "Everyone is placed"} />
    </Row>
  );
}

export function RoomStats({ refresh }) {
  const d = s(useLoad(() => rooms.summary(), [refresh]));
  return (
    <Row>
      <StatCard icon={BedDouble} tone="blue" label="Rooms" value={d.total_rooms} hint={d.closed_rooms ? `${d.closed_rooms} closed` : "All open"} />
      <StatCard icon={DoorOpen} tone="green" label="Rooms with free beds" value={d.available_rooms} />
      <StatCard icon={DoorClosed} tone="red" label="Full rooms" value={d.full_rooms} />
      <StatCard icon={Percent} tone="violet" label="Bed occupancy" value={d.occupancy_percent == null ? "–" : `${d.occupancy_percent}%`} hint={d.total_beds != null ? `${d.occupied_beds} of ${d.total_beds} beds` : undefined} />
    </Row>
  );
}

export function FeeStats({ refresh }) {
  const d = s(useLoad(() => fees.summary(), [refresh]));
  return (
    <Row>
      <StatCard icon={Wallet} tone="blue" label="Total charged" value={formatMoney(d.total_due)} hint={`${d.total_fees ?? 0} fee records`} />
      <StatCard icon={HandCoins} tone="green" label="Collected" value={formatMoney(d.total_collected)} />
      <StatCard icon={Clock} tone="amber" label="Outstanding" value={formatMoney(d.outstanding)} hint={`${(d.pending_count ?? 0) + (d.partial_count ?? 0)} not yet due or part-paid`} />
      <StatCard icon={AlertTriangle} tone="red" label="Overdue" value={formatMoney(d.overdue_amount)} hint={`${d.overdue_count ?? 0} fee${d.overdue_count === 1 ? "" : "s"} past due`} />
    </Row>
  );
}

export function PaymentStats({ refresh }) {
  const d = s(useLoad(() => fees.summary(), [refresh]));
  return (
    <Row>
      <StatCard icon={Banknote} tone="green" label="Collected this month" value={formatMoney(d.collected_this_month)} hint={`${d.payments_this_month ?? 0} payment${d.payments_this_month === 1 ? "" : "s"}`} />
      <StatCard icon={CreditCard} tone="blue" label="All-time collected" value={formatMoney(d.total_collected)} hint={`${d.payments_total ?? 0} payments recorded`} />
      <StatCard icon={ReceiptText} tone="amber" label="Still to collect" value={formatMoney(d.outstanding)} />
    </Row>
  );
}

export function EmployeeStats({ refresh }) {
  const all = s(useLoad(() => employees.list({ page_size: 1 }), [refresh]));
  const on = s(useLoad(() => employees.list({ page_size: 1, is_active: true }), [refresh]));
  const off = s(useLoad(() => employees.list({ page_size: 1, is_active: false }), [refresh]));
  return (
    <Row>
      <StatCard icon={Users} tone="blue" label="Employees" value={all.total} />
      <StatCard icon={UserCheck} tone="green" label="Active accounts" value={on.total} />
      <StatCard icon={UserX} tone="red" label="Deactivated" value={off.total} />
    </Row>
  );
}

export function AllocationStats({ refresh }) {
  const r = s(useLoad(() => rooms.summary(), [refresh]));
  const st = s(useLoad(() => students.summary(), [refresh]));
  return (
    <Row>
      <StatCard icon={DoorOpen} tone="green" label="Free beds" value={r.free_beds} hint={`${r.available_rooms ?? 0} rooms can take someone`} />
      <StatCard icon={BedDouble} tone="teal" label="Beds in use" value={r.occupied_beds} hint={r.total_beds != null ? `of ${r.total_beds} open beds` : undefined} />
      <StatCard icon={st.unallocated ? Hourglass : CheckCircle2} tone={st.unallocated ? "amber" : "green"} label="Students waiting for a room" value={st.unallocated} />
    </Row>
  );
}

export function HistoryStats() {
  const from = new Date(Date.now() - 29 * 864e5).toLocaleDateString("en-CA");
  const d = s(useLoad(() => attendance.summary({ date_from: from }), []));
  const low = (d.students || []).filter((x) => x.percentage != null && x.percentage < 75).length;
  return (
    <Row>
      <StatCard icon={Percent} tone="violet" label="Overall attendance, last 30 days" value={d.overall_percentage == null ? "–" : `${d.overall_percentage}%`} />
      <StatCard icon={CheckCircle2} tone="green" label="Days present" value={d.totals?.present} />
      <StatCard icon={UserX} tone="red" label="Days absent" value={d.totals?.absent} hint={`${d.totals?.leave ?? 0} on leave`} />
      <StatCard icon={low ? AlertTriangle : UserCheck} tone={low ? "amber" : "green"} label="Students under 75%" value={low} hint={low ? "Worth a conversation" : "Everyone is on track"} />
    </Row>
  );
}

export { GraduationCap };
