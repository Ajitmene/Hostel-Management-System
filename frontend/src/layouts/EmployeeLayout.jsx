import { BedDouble, CalendarCheck, CreditCard, GraduationCap, History, LayoutDashboard, UserCircle, Wallet } from "lucide-react";
import DashboardLayout from "./DashboardLayout.jsx";
import { useAuth } from "../context/AuthContext.jsx";

// Each entry is only shown when the employee holds a permission it needs.
const ALL = [
  { group: "Overview", items: [{ to: "/employee/dashboard", label: "Dashboard", icon: LayoutDashboard }] },
  { group: "Residents", items: [
    { to: "/employee/students", label: "Students", icon: GraduationCap, needs: ["students.view"] },
    { to: "/employee/rooms", label: "Rooms", icon: BedDouble, needs: ["rooms.view"] },
  ] },
  { group: "Finance", items: [
    { to: "/employee/fees", label: "Fees", icon: Wallet, needs: ["fees.view"] },
    { to: "/employee/payments", label: "Payments", icon: CreditCard, needs: ["fees.view"] },
  ] },
  { group: "Daily work", items: [
    { to: "/employee/attendance", label: "Take attendance", icon: CalendarCheck, end: true, needs: ["attendance.record"] },
    { to: "/employee/attendance/history", label: "Attendance history", icon: History, needs: ["attendance.view"] },
  ] },
  { group: "Account", items: [{ to: "/employee/profile", label: "My profile", icon: UserCircle }] },
];

export default function EmployeeLayout() {
  const { can } = useAuth();
  const nav = ALL.map((g) => ({ ...g, items: g.items.filter((i) => !i.needs || i.needs.some(can)) })).filter((g) => g.items.length);
  return <DashboardLayout nav={nav} home="/employee/dashboard" label="Employee desk" />;
}
