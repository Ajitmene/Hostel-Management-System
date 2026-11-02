import { ArrowRightLeft, BarChart3, BedDouble, CalendarCheck, CreditCard, GraduationCap, History, LayoutDashboard, UserCircle, UserCog, Wallet } from "lucide-react";
import DashboardLayout from "./DashboardLayout.jsx";

const NAV = [
  { group: "Overview", items: [{ to: "/admin/dashboard", label: "Dashboard", icon: LayoutDashboard }] },
  { group: "Residents", items: [
    { to: "/admin/students", label: "Students", icon: GraduationCap },
    { to: "/admin/rooms", label: "Rooms", icon: BedDouble },
    { to: "/admin/allocations", label: "Allocations", icon: ArrowRightLeft },
  ] },
  { group: "Finance", items: [
    { to: "/admin/fees", label: "Fees", icon: Wallet },
    { to: "/admin/payments", label: "Payments", icon: CreditCard },
  ] },
  { group: "Daily work", items: [
    { to: "/admin/attendance", label: "Take attendance", icon: CalendarCheck, end: true },
    { to: "/admin/attendance/history", label: "Attendance history", icon: History },
  ] },
  { group: "Administration", items: [
    { to: "/admin/employees", label: "Employees", icon: UserCog },
    { to: "/admin/reports", label: "Reports", icon: BarChart3 },
    { to: "/admin/profile", label: "My profile", icon: UserCircle },
  ] },
];

export default function AdminLayout() {
  return <DashboardLayout nav={NAV} home="/admin/dashboard" label="Administration" />;
}
