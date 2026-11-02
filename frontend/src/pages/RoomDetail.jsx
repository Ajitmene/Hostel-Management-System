import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { rooms } from "../api/endpoints.js";
import { useAuth, useBase } from "../context/AuthContext.jsx";
import { useLoad } from "../hooks/usePagedQuery.js";
import DataTable from "../components/DataTable.jsx";
import RoomFormModal from "../components/RoomFormModal.jsx";
import TransferModal from "../components/TransferModal.jsx";
import { BedStrip, ErrorNotice, InfoBox, Loading, PageHeader, StatCard, StatusBadge } from "../components/ui.jsx";
import { Banknote, BedDouble, DoorOpen, Users } from "lucide-react";
import { formatDate, formatMoney, titleCase } from "../utils/format.js";

export default function RoomDetail() {
  const { id } = useParams();
  const { isAdmin, can } = useAuth();
  const base = useBase();
  const r = useLoad(() => rooms.get(id), [id]);
  const [editing, setEditing] = useState(false);
  const [transfer, setTransfer] = useState(null);

  if (r.loading && !r.data) return <Loading />;
  if (r.error) return <ErrorNotice message={r.error} onRetry={r.reload} />;
  const room = r.data;

  return (
    <>
      <PageHeader icon={BedDouble} title={`Room ${room.block}-${room.room_number}`} subtitle={`${titleCase(room.room_type)} · floor ${room.floor}`}
        actions={<>
          <Link className="btn" to={`${base}/rooms`}>Back to rooms</Link>
          {isAdmin && <button className="btn btn-primary" onClick={() => setEditing(true)}>Edit room</button>}
        </>} />
      <div className="stats">
        <StatCard icon={BedDouble} tone="blue" label="Capacity" value={room.capacity} hint="beds in this room" />
        <StatCard icon={Users} tone="teal" label="Occupied" value={room.occupancy} />
        <StatCard icon={DoorOpen} tone={room.available_beds ? "green" : "red"} label="Free beds" value={room.available_beds} hint={room.is_active ? undefined : "Room is closed"} />
        <StatCard icon={Banknote} tone="amber" label="Monthly rate" value={formatMoney(room.monthly_rate)} />
      </div>
      <InfoBox>
        <p>Occupants are the students with an active allocation to this room. {isAdmin ? "Use Transfer to move someone; the old allocation is closed and kept in the history." : "Only administrators can move students between rooms."}</p>
      </InfoBox>
      <section className="panel">
        <dl className="details">
          <dt>Status</dt><dd><StatusBadge value={room.status} /></dd>
          <dt>Beds</dt><dd><BedStrip occupied={room.occupancy} capacity={room.capacity} closed={!room.is_active} /> {room.occupancy} of {room.capacity} taken</dd>
          <dt>Monthly rate</dt><dd>{formatMoney(room.monthly_rate)}</dd>
        </dl>
      </section>
      <section className="panel">
        <h2>Current occupants</h2>
        <DataTable rows={room.occupants} rowKey="allocation_id" empty={{ title: "Nobody is in this room", hint: isAdmin ? "Allocate a student from the Allocations page." : undefined }}
          columns={[
            { header: "Student", render: (o) => (can("students.view") ? <Link to={`${base}/students/${o.student_id}`}>{o.full_name}</Link> : o.full_name) },
            { header: "Enrollment no", render: (o) => o.enrollment_no },
            { header: "Since", render: (o) => formatDate(o.since) },
            ...(isAdmin ? [{ header: "Actions", className: "col-actions", render: (o) => (
              <button className="btn btn-small" onClick={() => setTransfer({ id: o.allocation_id, student_name: o.full_name, room_id: room.id, room_number: `${room.block}-${room.room_number}` })}>Transfer</button>
            ) }] : []),
          ]} />
      </section>
      {editing && <RoomFormModal room={room} onClose={() => setEditing(false)} onSaved={() => { setEditing(false); r.reload(); }} />}
      {transfer && <TransferModal allocation={transfer} onClose={() => setTransfer(null)} onDone={() => { setTransfer(null); r.reload(); }} />}
    </>
  );
}
