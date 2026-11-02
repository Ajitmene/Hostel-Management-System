import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";
import ProtectedRoute from "./routes/ProtectedRoute.jsx";
import AdminLayout from "./layouts/AdminLayout.jsx";
import EmployeeLayout from "./layouts/EmployeeLayout.jsx";
import { Loading } from "./components/ui.jsx";
import Login from "./pages/Login.jsx";
import NotFound from "./pages/NotFound.jsx";
import AdminDashboard from "./pages/AdminDashboard.jsx";
import EmployeeDashboard from "./pages/EmployeeDashboard.jsx";
import StudentList from "./pages/StudentList.jsx";
import StudentForm from "./pages/StudentForm.jsx";
import StudentDetail from "./pages/StudentDetail.jsx";
import RoomList from "./pages/RoomList.jsx";
import RoomDetail from "./pages/RoomDetail.jsx";
import Allocations from "./pages/Allocations.jsx";
import FeeList from "./pages/FeeList.jsx";
import RecordPayment from "./pages/RecordPayment.jsx";
import Payments from "./pages/Payments.jsx";
import Receipt from "./pages/Receipt.jsx";
import AttendanceEntry from "./pages/AttendanceEntry.jsx";
import AttendanceHistory from "./pages/AttendanceHistory.jsx";
import EmployeeList from "./pages/EmployeeList.jsx";
import EmployeeForm from "./pages/EmployeeForm.jsx";
import Reports from "./pages/Reports.jsx";
import Profile from "./pages/Profile.jsx";

const guard = (element, props) => <ProtectedRoute {...props}>{element}</ProtectedRoute>;

function Home() {
  const { user, loading } = useAuth();
  if (loading) return <Loading label="Checking your session…" />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "admin" ? "/admin/dashboard" : "/employee/dashboard"} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/" element={<Home />} />

      {/* Administrator area: every page re-checks the role in the browser; the API enforces it for real. */}
      <Route path="/admin" element={guard(<AdminLayout />, { roles: ["admin"] })}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<AdminDashboard />} />
        <Route path="students" element={<StudentList />} />
        <Route path="students/new" element={<StudentForm />} />
        <Route path="students/:id" element={<StudentDetail />} />
        <Route path="students/:id/edit" element={<StudentForm />} />
        <Route path="rooms" element={<RoomList />} />
        <Route path="rooms/:id" element={<RoomDetail />} />
        <Route path="allocations" element={<Allocations />} />
        <Route path="fees" element={<FeeList />} />
        <Route path="payments" element={<Payments />} />
        <Route path="payments/new" element={<RecordPayment />} />
        <Route path="payments/:id/receipt" element={<Receipt />} />
        <Route path="attendance" element={<AttendanceEntry />} />
        <Route path="attendance/history" element={<AttendanceHistory />} />
        <Route path="employees" element={<EmployeeList />} />
        <Route path="employees/new" element={<EmployeeForm />} />
        <Route path="employees/:id/edit" element={<EmployeeForm />} />
        <Route path="reports" element={<Reports />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<NotFound />} />
      </Route>

      {/* Employee area: each page also needs the matching permission. */}
      <Route path="/employee" element={guard(<EmployeeLayout />, { roles: ["employee"] })}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<EmployeeDashboard />} />
        <Route path="students" element={guard(<StudentList />, { permission: "students.view" })} />
        <Route path="students/:id" element={guard(<StudentDetail />, { permission: "students.view" })} />
        <Route path="rooms" element={guard(<RoomList />, { permission: "rooms.view" })} />
        <Route path="rooms/:id" element={guard(<RoomDetail />, { permission: "rooms.view" })} />
        <Route path="fees" element={guard(<FeeList />, { permission: "fees.view" })} />
        <Route path="payments" element={guard(<Payments />, { permission: "fees.view" })} />
        <Route path="payments/:id/receipt" element={guard(<Receipt />, { permission: "fees.view" })} />
        <Route path="attendance" element={guard(<AttendanceEntry />, { permission: "attendance.record" })} />
        <Route path="attendance/history" element={guard(<AttendanceHistory />, { permission: "attendance.view" })} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<NotFound />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
