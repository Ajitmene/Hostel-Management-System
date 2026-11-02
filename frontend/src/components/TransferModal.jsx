import { useState } from "react";
import { rooms } from "../api/endpoints.js";
import { useToast } from "../context/ToastContext.jsx";
import { useLoad } from "../hooks/usePagedQuery.js";
import { errorMessage } from "../utils/errors.js";
import { today } from "../utils/format.js";
import { Modal } from "./Modal.jsx";
import { Field, Loading } from "./ui.jsx";

/** Move a student from their current room. `allocation` = { id, student_name, room_id, room_number }. */
export default function TransferModal({ allocation, onClose, onDone }) {
  const toast = useToast();
  const free = useLoad(() => rooms.available(), []);
  const [roomId, setRoomId] = useState("");
  const [date, setDate] = useState(today());
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!roomId) return setError("Choose the destination room.");
    setBusy(true);
    try {
      await rooms.transfer(allocation.id, { new_room_id: Number(roomId), transfer_date: date });
      toast.success(`${allocation.student_name} moved to the new room.`);
      onDone();
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  const options = (free.data || []).filter((r) => r.id !== allocation.room_id);
  return (
    <Modal title={`Transfer ${allocation.student_name}`} onClose={onClose}>
      <form onSubmit={submit} noValidate>
        <p className="muted">Currently in room {allocation.room_number}. The old allocation is closed and kept in the history.</p>
        {error && <div className="notice notice-error" role="alert">{error}</div>}
        {free.loading ? <Loading /> : (
          <Field label="Move to" name="room" as="select" value={roomId} onChange={(e) => setRoomId(e.target.value)}>
            <option value="">Choose a room with a free bed…</option>
            {options.map((r) => <option key={r.id} value={r.id}>{r.block}-{r.room_number} ({r.available_beds} free)</option>)}
          </Field>
        )}
        <Field label="Transfer date" name="date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <div className="form-actions">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Moving…" : "Transfer"}</button>
        </div>
      </form>
    </Modal>
  );
}
