import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../api/endpoints.js", () => ({
  auth: { me: vi.fn(), refresh: vi.fn(), login: vi.fn(), logout: vi.fn(), changePassword: vi.fn() },
  dashboard: { summary: vi.fn() },
  students: { list: vi.fn(), get: vi.fn() },
  rooms: { list: vi.fn(), available: vi.fn(), summary: vi.fn() },
  fees: { summary: vi.fn() }, attendance: { summary: vi.fn() }, employees: { list: vi.fn() }, reports: {},
}));

import App from "../App.jsx";
import { AuthProvider } from "../context/AuthContext.jsx";
import { ToastProvider } from "../context/ToastContext.jsx";
import { auth, dashboard, employees, fees, rooms, students } from "../api/endpoints.js";
import { validateStudent } from "../pages/StudentForm.jsx";

const ADMIN = { id: 1, email: "admin@example.com", first_name: "Ada", last_name: "Admin", role: "admin", permissions: [], employee_id: null };
const EMPLOYEE = { id: 2, email: "emp@example.com", first_name: "Eli", last_name: "Employee", role: "employee", permissions: ["students.view", "attendance.record"], employee_id: "EMP-1" };
const unauthenticated = () => { const e = new Error("401"); e.response = { status: 401, data: { error: { code: "not_authenticated", message: "Authentication required." } } }; return e; };

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <ToastProvider><AuthProvider><App /></AuthProvider></ToastProvider>
    </MemoryRouter>
  );
}
const signedInAs = (user) => auth.me.mockResolvedValue({ data: { user, csrf_token: "csrf" } });

beforeEach(() => {
  vi.clearAllMocks();
  dashboard.summary.mockResolvedValue({ data: { role: "employee", tasks: [], quick_links: [], attendance_today: null } });
  students.list.mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 } });
  employees.list.mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 10, pages: 0 } });
  rooms.list.mockResolvedValue({ data: { items: [], total: 0, page: 1, page_size: 100, pages: 0 } });
  fees.summary.mockResolvedValue({ data: { collected_this_month: "0.00", payments_this_month: 0, outstanding: "0.00", overdue_amount: "0.00" } });
});

describe("route protection", () => {
  it("sends signed-out visitors to the login page", async () => {
    auth.me.mockRejectedValue(unauthenticated());
    auth.refresh.mockRejectedValue(unauthenticated());
    renderAt("/admin/students");
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows an access-denied message when an employee opens an administrator page", async () => {
    signedInAs(EMPLOYEE);
    renderAt("/admin/employees");
    expect(await screen.findByText(/don’t have access to this page/i)).toBeInTheDocument();
    expect(employees.list).not.toHaveBeenCalled();
  });

  it("blocks an employee from a page their permissions don't cover", async () => {
    signedInAs(EMPLOYEE); // has students.view but not rooms.view
    renderAt("/employee/rooms");
    expect(await screen.findByText(/don’t have access to this page/i)).toBeInTheDocument();
  });

  it("keeps administrators out of the employee area too", async () => {
    signedInAs(ADMIN);
    renderAt("/employee/dashboard");
    expect(await screen.findByText(/don’t have access to this page/i)).toBeInTheDocument();
  });

  it("only lists navigation the employee may use", async () => {
    signedInAs(EMPLOYEE);
    renderAt("/employee/dashboard");
    await waitFor(() => expect(screen.getByRole("link", { name: "Students" })).toBeInTheDocument());
    expect(screen.getByRole("link", { name: "Take attendance" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Rooms" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Employees" })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Reports" })).not.toBeInTheDocument();
  });

  it("shows the full menu to administrators", async () => {
    signedInAs(ADMIN);
    dashboard.summary.mockResolvedValue({ data: { role: "admin", total_students: 0, total_employees: 0, total_rooms: 0, occupied_rooms: 0, available_rooms: 0, total_beds: 0, occupied_beds: 0, pending_fees: "0.00", overdue_fee_count: 0, attendance_today: { present: 0, absent: 0, leave: 0, unmarked: 0 }, recent_activities: [] } });
    renderAt("/admin/dashboard");
    expect(await screen.findByRole("link", { name: "Employees" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Reports" })).toBeInTheDocument();
  });
});

describe("login form", () => {
  beforeEach(() => { auth.me.mockRejectedValue(unauthenticated()); auth.refresh.mockRejectedValue(unauthenticated()); });

  it("validates before calling the API", async () => {
    renderAt("/login");
    await userEvent.click(await screen.findByRole("button", { name: "Sign in" }));
    expect(await screen.findByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("Enter your password.")).toBeInTheDocument();
    expect(auth.login).not.toHaveBeenCalled();
  });

  it("shows the server's message for bad credentials", async () => {
    const err = new Error("401");
    err.response = { status: 401, data: { error: { code: "invalid_credentials", message: "Incorrect email or password." } } };
    auth.login.mockRejectedValue(err);
    renderAt("/login");
    await userEvent.type(await screen.findByLabelText("Email"), "a@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "wrong");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
  });

  it("lands an employee on the employee dashboard after signing in", async () => {
    auth.login.mockResolvedValue({ data: { user: EMPLOYEE, csrf_token: "csrf" } });
    renderAt("/login");
    await userEvent.type(await screen.findByLabelText("Email"), "emp@example.com");
    await userEvent.type(screen.getByLabelText("Password"), "a-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByText(/Welcome, Eli/)).toBeInTheDocument();
  });
});

describe("student form validation", () => {
  const good = { enrollment_no: "E-1", full_name: "A B", email: "a@b.co", phone: "+919800000001", gender: "male", address: "x", guardian_name: "G", guardian_phone: "9800000002", admission_date: "2026-01-01" };
  it("accepts valid data", () => expect(validateStudent(good)).toEqual({}));
  it("rejects bad email and phone", () => {
    const e = validateStudent({ ...good, email: "nope", phone: "12" });
    expect(Object.keys(e).sort()).toEqual(["email", "phone"]);
  });
});
