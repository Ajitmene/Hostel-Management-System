import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

// Realistic API shapes, so every page renders its tables, cards and icons for real.
const page = (items) => ({ data: { items, total: items.length, page: 1, page_size: 10, pages: 1 } });
const ok = (data) => Promise.resolve({ data });
const student = { id: 1, enrollment_no: "E-1", full_name: "Asha Patil", email: "a@example.com", phone: "+919800000001", gender: "female", address: "Pune", guardian_name: "R Patil", guardian_phone: "+919800000002", admission_date: "2026-07-01", status: "active", room: { id: 1, room_number: "101", block: "A" } };
const room = { id: 1, room_number: "101", room_type: "double", block: "A", floor: 1, capacity: 2, monthly_rate: "4500.00", is_active: true, occupancy: 1, available_beds: 1, status: "available" };
const fee = { id: 1, student_id: 1, student_name: "Asha Patil", enrollment_no: "E-1", structure_id: 1, structure_name: "Monthly fee", description: "Nov", amount_due: "4500.00", amount_paid: "1000.00", balance: "3500.00", due_date: "2026-11-10", status: "partial" };
const payment = { id: 1, receipt_number: "RCP-1", fee_id: 1, student_id: 1, student_name: "Asha Patil", enrollment_no: "E-1", amount: "1000.00", payment_date: "2026-11-01", method: "upi", transaction_reference: "U1", recorded_by: "admin@example.com", created_at: "2026-11-01T10:00:00Z" };
const adminSummary = { role: "admin", total_students: 5, total_employees: 2, total_rooms: 3, occupied_rooms: 2, available_rooms: 2, total_beds: 8, occupied_beds: 5, pending_fees: "3500.00", overdue_fee_count: 1, attendance_today: { present: 3, absent: 1, leave: 0, unmarked: 1 }, recent_activities: [{ id: 1, action: "payment.record", entity_type: "payment", entity_id: "1", user: "admin@example.com", created_at: "2026-11-01T10:00:00Z" }] };
const feeSummary = { total_fees: 2, total_due: "9000.00", total_collected: "1000.00", outstanding: "8000.00", overdue_count: 1, overdue_amount: "3500.00", pending_count: 1, partial_count: 1, paid_count: 0, collected_this_month: "1000.00", payments_this_month: 1, payments_total: 1 };
const attSummary = { date_from: "2026-10-01", date_to: "2026-11-01", totals: { present: 8, absent: 1, leave: 1 }, overall_percentage: 80, students: [{ student_id: 1, enrollment_no: "E-1", full_name: "Asha Patil", present: 8, absent: 1, leave: 1, marked_days: 10, percentage: 80 }] };
const employee = { id: 1, user_id: 2, first_name: "Meera", last_name: "K", email: "m@example.com", employee_id: "EMP-1", phone: "+919800000010", designation: "Warden", department: "Ops", joining_date: "2026-08-01", permissions: ["students.view"], is_active: true, role: "employee" };

vi.mock("../api/endpoints.js", () => ({
  auth: { me: vi.fn(), refresh: vi.fn(), login: vi.fn(), logout: vi.fn(), changePassword: vi.fn() },
  dashboard: { summary: vi.fn(() => ok(adminSummary)) },
  students: { list: vi.fn(() => ok(page([student]).data)), get: vi.fn(() => ok(student)), summary: vi.fn(() => ok({ total: 5, active: 4, inactive: 1, left: 0, allocated: 3, unallocated: 1 })), create: vi.fn(), update: vi.fn(), setStatus: vi.fn() },
  rooms: { list: vi.fn(() => ok(page([room]).data)), get: vi.fn(() => ok({ ...room, occupants: [{ student_id: 1, enrollment_no: "E-1", full_name: "Asha Patil", allocation_id: 1, since: "2026-07-01" }] })), summary: vi.fn(() => ok({ total_rooms: 3, open_rooms: 3, available_rooms: 2, full_rooms: 1, closed_rooms: 0, total_beds: 8, occupied_beds: 5, free_beds: 3, occupancy_percent: 62.5 })), available: vi.fn(() => ok([room])), allocations: vi.fn(() => ok(page([{ id: 1, student_id: 1, student_name: "Asha Patil", enrollment_no: "E-1", room_id: 1, room_number: "101", block: "A", start_date: "2026-07-01", end_date: null, is_active: true }]).data)), create: vi.fn(), update: vi.fn(), allocate: vi.fn(), transfer: vi.fn() },
  fees: { list: vi.fn(() => ok(page([fee]).data)), pending: vi.fn(() => ok(page([fee]).data)), get: vi.fn(() => ok(fee)), summary: vi.fn(() => ok(feeSummary)), structures: vi.fn(() => ok([{ id: 1, name: "Monthly fee", amount: "4500.00", frequency: "monthly", description: "", is_active: true }])), payments: vi.fn(() => ok(page([payment]).data)), receipt: vi.fn(() => ok({ ...payment, fee_description: "Nov", structure_name: "Monthly fee", amount_due: "4500.00", total_paid: "1000.00", balance_after: "3500.00" })), create: vi.fn(), createStructure: vi.fn(), recordPayment: vi.fn() },
  attendance: { list: vi.fn(() => ok(page([{ id: 1, student_id: 1, student_name: "Asha Patil", enrollment_no: "E-1", date: "2026-11-01", status: "present", remarks: "", recorded_by: "admin@example.com" }]).data)), roster: vi.fn(() => ok([{ student_id: 1, enrollment_no: "E-1", full_name: "Asha Patil", room: "A-101", attendance_id: null, status: null, remarks: "" }, { student_id: 2, enrollment_no: "E-2", full_name: "Ravi S", room: null, attendance_id: 5, status: "absent", remarks: "ill" }])), summary: vi.fn(() => ok(attSummary)), record: vi.fn(), correct: vi.fn() },
  employees: { list: vi.fn(() => ok(page([employee]).data)), get: vi.fn(() => ok(employee)), create: vi.fn(), update: vi.fn(), setStatus: vi.fn(), resetPassword: vi.fn() },
  reports: { get: vi.fn(() => ok({ title: "Room occupancy", columns: ["Block", "Room"], rows: [["A", "101"]], summary: { rooms: 1 } })), csv: vi.fn() },
}));

import App from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import { auth, dashboard } from "../api/endpoints.js";

const ADMIN = { id: 1, email: "admin@example.com", first_name: "Ada", last_name: "Admin", role: "admin", permissions: [], employee_id: null };
const EMP = { id: 2, email: "e@example.com", first_name: "Eli", last_name: "E", role: "employee", permissions: ["students.view", "rooms.view", "fees.view", "attendance.view", "attendance.record"], employee_id: "EMP-1" };

const employeeSummary = { role: "employee", total_students: 5, available_rooms: 2, attendance_today: { present: 3, absent: 1, leave: 0, unmarked: 1 }, tasks: ["Record today’s attendance for 1 student(s)."], quick_links: [{ label: "Students", path: "/employee/students" }, { label: "Record attendance", path: "/employee/attendance" }] };

function visit(path, user) {
  auth.me.mockResolvedValue({ data: { user, csrf_token: "c" } });
  dashboard.summary.mockImplementation(() => ok(user.role === "admin" ? adminSummary : employeeSummary));
  return render(
    <MemoryRouter initialEntries={[path]}><ToastProvider><AuthProvider><App /></AuthProvider></ToastProvider></MemoryRouter>
  );
}

const ADMIN_PAGES = [
  ["/admin/dashboard", /Hostel overview/], ["/admin/students", /Search, filter and manage/], ["/admin/students/new", /Before you save/],
  ["/admin/students/1/edit", /Edit student/], ["/admin/students/1", /About this record/], ["/admin/rooms", /Bed occupancy/],
  ["/admin/rooms/1", /Free beds/], ["/admin/allocations", /Students waiting for a room/], ["/admin/fees", /Total charged/],
  ["/admin/payments", /Collected this month/], ["/admin/payments/new", /How recording works/], ["/admin/payments/1/receipt", /Amount received/],
  ["/admin/attendance", /Still to mark/], ["/admin/attendance/history", /Overall attendance/], ["/admin/employees", /Deactivated/],
  ["/admin/employees/new", /Permissions explained/], ["/admin/employees/1/edit", /Permissions explained/], ["/admin/reports", /About: Room occupancy/],
  ["/admin/profile", /Keeping your account safe/],
];

describe("every administrator page renders with realistic data", () => {
  it.each(ADMIN_PAGES)("%s", async (path, text) => {
    visit(path, ADMIN);
    expect((await screen.findAllByText(text, {}, { timeout: 4000 })).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Something went wrong/i)).not.toBeInTheDocument();
  });
});

describe("employee pages", () => {
  it.each([
    ["/employee/dashboard", /Your access/], ["/employee/students", /read-only access to student records/], ["/employee/rooms", /read-only access to rooms/],
    ["/employee/fees", /view fees and payment status/], ["/employee/attendance", /Still to mark/], ["/employee/payments/1/receipt", /Amount received/],
  ])("%s", async (path, text) => {
    visit(path, EMP);
    expect((await screen.findAllByText(text, {}, { timeout: 4000 })).length).toBeGreaterThan(0);
  });

  it("hides administrator-only buttons from employees", async () => {
    visit("/employee/students", EMP);
    await screen.findByText("Asha Patil");
    await waitFor(() => expect(screen.queryByRole("link", { name: /Add student/ })).not.toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /Deactivate/ })).not.toBeInTheDocument();
  });
});
