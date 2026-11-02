import { useState } from "react";
import { rooms } from "../api/endpoints.js";
import { useToast } from "../context/ToastContext.jsx";
import { errorMessage, fieldErrors } from "../utils/errors.js";
import { Modal } from "./Modal.jsx";
import { Field } from "./ui.jsx";

export default function RoomFormModal({ room, onClose, onSaved }) {
  const toast = useToast();
  const [form, setForm] = useState(
    room
      ? { room_number: room.room_number, room_type: room.room_type, block: room.block, floor: room.floor, capacity: room.capacity, monthly_rate: room.monthly_rate, is_active: room.is_active }
      : { room_number: "", room_type: "double", block: "", floor: 0, capacity: 2, monthly_rate: "", is_active: true }
  );
  const [errors, setErrors] = useState({});
  const [busy, setBusy] = useState(false);
  const set = (e) => setForm((f) => ({ ...f, [e.target.name]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    const found = {};
    if (!form.room_number.trim()) found.room_number = "Enter the room number.";
    if (!form.block.trim()) found.block = "Enter the block.";
    if (!(Number(form.capacity) >= 1)) found.capacity = "Capacity must be at least 1.";
    if (form.monthly_rate === "" || Number(form.monthly_rate) < 0) found.monthly_rate = "Enter the monthly rate.";
    if (Number(form.floor) < 0 || form.floor === "") found.floor = "Enter the floor (0 for ground).";
    setErrors(found);
    if (Object.keys(found).length) return;
    setBusy(true);
    try {
      const body = { ...form, floor: Number(form.floor), capacity: Number(form.capacity), monthly_rate: String(form.monthly_rate) };
      if (room) await rooms.update(room.id, body); else await rooms.create(body);
      toast.success(room ? "Room updated." : "Room added.");
      onSaved();
    } catch (err) {
      setErrors({ ...fieldErrors(err), form: errorMessage(err) });
    } finally {
      setBusy(false);
    }
  };

  return (
    <Modal title={room ? `Edit room ${room.room_number}` : "Add room"} onClose={onClose}>
      <form onSubmit={submit} noValidate className="form-grid">
        {errors.form && !Object.keys(errors).some((k) => k !== "form") && <div className="notice notice-error span-2" role="alert">{errors.form}</div>}
        <Field label="Room number" name="room_number" value={form.room_number} onChange={set} error={errors.room_number} />
        <Field label="Block" name="block" value={form.block} onChange={set} error={errors.block} />
        <Field label="Floor" name="floor" type="number" min="0" value={form.floor} onChange={set} error={errors.floor} />
        <Field label="Room type" name="room_type" as="select" value={form.room_type} onChange={set}>
          <option value="single">Single</option><option value="double">Double</option><option value="triple">Triple</option><option value="dormitory">Dormitory</option>
        </Field>
        <Field label="Capacity (beds)" name="capacity" type="number" min="1" value={form.capacity} onChange={set} error={errors.capacity} />
        <Field label="Monthly rate (₹)" name="monthly_rate" type="number" min="0" step="0.01" value={form.monthly_rate} onChange={set} error={errors.monthly_rate} />
        <label className="check span-2"><input type="checkbox" name="is_active" checked={form.is_active} onChange={set} /> Room is open for allocation</label>
        <div className="form-actions span-2">
          <button type="button" className="btn" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" disabled={busy}>{busy ? "Saving…" : "Save room"}</button>
        </div>
      </form>
    </Modal>
  );
}
