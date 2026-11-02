import { useState } from "react";
import { Link } from "react-router-dom";
import { rooms } from "../api/endpoints.js";
import { useAuth, useBase } from "../context/AuthContext.jsx";
import { usePagedQuery } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import Pagination from "../components/Pagination.jsx";
import RoomFormModal from "../components/RoomFormModal.jsx";
import { BedStrip, InfoBox, PageHeader, SearchInput, StatusBadge } from "../components/ui.jsx";
import { RoomStats } from "../components/PageStats.jsx";
import { BedDouble, Pencil, Plus } from "lucide-react";
import { formatMoney, titleCase } from "../utils/format.js";

export default function RoomList() {
  const { isAdmin } = useAuth();
  const base = useBase();
  const q = usePagedQuery(rooms.list, { ordering: "block" });
  const [editing, setEditing] = useState(null); // null | "new" | room

  const columns = [
    { header: "Room", render: (r) => <Link to={`${base}/rooms/${r.id}`}><strong>{r.block}-{r.room_number}</strong></Link> },
    { header: "Floor", render: (r) => r.floor },
    { header: "Type", render: (r) => titleCase(r.room_type) },
    { header: "Beds", render: (r) => <><BedStrip occupied={r.occupancy} capacity={r.capacity} closed={!r.is_active} /> <small className="muted">{r.occupancy}/{r.capacity}</small></> },
    { header: "Monthly rate", className: "num", render: (r) => formatMoney(r.monthly_rate) },
    { header: "Status", render: (r) => <StatusBadge value={r.status} /> },
  ];
  if (isAdmin) columns.push({ header: "Actions", className: "col-actions", render: (r) => <button className="btn btn-small" onClick={() => setEditing(r)}><Pencil aria-hidden="true" />Edit</button> });

  return (
    <>
      <PageHeader icon={BedDouble} title="Rooms" subtitle="Occupancy is counted from active allocations."
        actions={isAdmin && <button className="btn btn-primary" onClick={() => setEditing("new")}><Plus aria-hidden="true" />Add room</button>} />
      <RoomStats refresh={q.data} />
      <InfoBox>
        <ul>
          <li>Each square in the <strong>Beds</strong> column is one bed; a filled square is an occupied bed.</li>
          <li><strong>Has free beds</strong> means the room is open and not full. <strong>Closed</strong> rooms (for example under repair) cannot take new occupants.</li>
          {isAdmin ? <li>You cannot lower a room’s capacity below the number of people already in it.</li> : <li>You have read-only access to rooms.</li>}
        </ul>
      </InfoBox>
      <div className="toolbar">
        <SearchInput value={q.params.q} onChange={(v) => q.update({ q: v })} placeholder="Room number" />
        <input type="search" className="search search-short" aria-label="Block" placeholder="Block" defaultValue="" onChange={(e) => q.update({ block: e.target.value.trim() })} />
        <select aria-label="Room type" value={q.params.room_type || ""} onChange={(e) => q.update({ room_type: e.target.value })}>
          <option value="">All types</option><option value="single">Single</option><option value="double">Double</option><option value="triple">Triple</option><option value="dormitory">Dormitory</option>
        </select>
        <select aria-label="Availability" value={q.params.status || ""} onChange={(e) => q.update({ status: e.target.value })}>
          <option value="">Any availability</option><option value="available">Has free beds</option><option value="full">Full</option><option value="closed">Closed</option>
        </select>
      </div>
      <DataTable columns={columns} rows={q.data?.items} loading={q.loading} error={q.error} onRetry={q.reload}
        empty={{ icon: BedDouble, title: "No rooms found", hint: isAdmin ? "Add the first room to get started." : "No rooms match your filters." }} />
      <Pagination data={q.data} onPage={q.setPage} />
      {editing && <RoomFormModal room={editing === "new" ? null : editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); q.reload(); }} />}
    </>
  );
}
