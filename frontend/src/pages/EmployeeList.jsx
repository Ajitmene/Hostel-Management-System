import { useState } from "react";
import { Link } from "react-router-dom";
import { employees } from "../api/endpoints.js";
import { useToast } from "../context/ToastContext.jsx";
import { usePagedQuery } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import { ConfirmDialog } from "../components/Modal.jsx";
import { InfoBox, PageHeader, SearchInput, StatusBadge } from "../components/ui.jsx";
import { EmployeeStats } from "../components/PageStats.jsx";
import { Pencil, Plus, UserCheck, UserCog, UserX } from "lucide-react";
import { errorMessage } from "../utils/errors.js";
import { formatDate } from "../utils/format.js";

export default function EmployeeList() {
  const toast = useToast();
  const q = usePagedQuery(employees.list, {});
  const [confirm, setConfirm] = useState(null);
  const [busy, setBusy] = useState(false);

  const toggle = async () => {
    setBusy(true);
    try {
      await employees.setStatus(confirm.id, !confirm.is_active);
      toast.success(confirm.is_active ? "Account deactivated. They have been signed out." : "Account activated.");
      setConfirm(null);
      q.reload();
    } catch (e) { toast.error(errorMessage(e)); } finally { setBusy(false); }
  };

  const columns = [
    { header: "Employee ID", render: (e) => e.employee_id },
    { header: "Name", render: (e) => <>{e.first_name} {e.last_name}<br /><small className="muted">{e.email}</small></> },
    { header: "Role", render: (e) => <>{e.designation}<br /><small className="muted">{e.department}</small></> },
    { header: "Joined", render: (e) => formatDate(e.joining_date) },
    { header: "Access", render: (e) => `${e.permissions.length} permission${e.permissions.length === 1 ? "" : "s"}` },
    { header: "Status", render: (e) => <StatusBadge value={e.is_active ? "active" : "inactive"} /> },
    { header: "Actions", className: "col-actions", render: (e) => (
      <>
        <Link className="btn btn-small" to={`/admin/employees/${e.id}/edit`}><Pencil aria-hidden="true" />Edit</Link>{" "}
        <button className={`btn btn-small ${e.is_active ? "btn-danger-ghost" : ""}`} onClick={() => setConfirm(e)}>{e.is_active ? <UserX aria-hidden="true" /> : <UserCheck aria-hidden="true" />}{e.is_active ? "Deactivate" : "Activate"}</button>
      </>
    ) },
  ];

  return (
    <>
      <PageHeader icon={UserCog} title="Employees" subtitle="Employees can never become administrators from this screen."
        actions={<Link className="btn btn-primary" to="/admin/employees/new"><Plus aria-hidden="true" />Add employee</Link>} />
      <EmployeeStats refresh={q.data} />
      <InfoBox>
        <ul>
          <li>Each employee can use only the permissions you tick. Edit a person to change them; the change applies immediately.</li>
          <li><strong>Deactivating</strong> an account signs that person out straight away and blocks sign-in. Their history is kept.</li>
          <li>Administrator accounts are not managed here; they are created by the system owner.</li>
        </ul>
      </InfoBox>
      <div className="toolbar">
        <SearchInput value={q.params.q} onChange={(v) => q.update({ q: v })} placeholder="Name, email or employee ID" />
        <select aria-label="Status" value={q.params.is_active ?? ""} onChange={(e) => q.update({ is_active: e.target.value })}>
          <option value="">All accounts</option><option value="true">Active</option><option value="false">Inactive</option>
        </select>
      </div>
      <DataTable columns={columns} rows={q.data?.items} loading={q.loading} error={q.error} onRetry={q.reload} empty={{ icon: UserCog, title: "No employees yet", hint: "Add the first employee account." }} />
      <Pagination data={q.data} onPage={q.setPage} />
      {confirm && (
        <ConfirmDialog title={confirm.is_active ? "Deactivate account?" : "Activate account?"} danger={confirm.is_active} busy={busy} confirmLabel={confirm.is_active ? "Deactivate" : "Activate"}
          message={confirm.is_active ? `${confirm.first_name} ${confirm.last_name} will be signed out immediately and will not be able to sign in.` : `${confirm.first_name} ${confirm.last_name} will be able to sign in again.`}
          onConfirm={toggle} onCancel={() => setConfirm(null)} />
      )}
    </>
  );
}
