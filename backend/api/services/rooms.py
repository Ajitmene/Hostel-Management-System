from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from api.core.errors import ApiError
from api.services import audit
from rooms.models import Room, RoomAllocation
from students.models import Student


def room_queryset():
    return Room.objects.annotate(occupied=Count("allocations", filter=Q(allocations__is_active=True)))


def serialize_room(r: Room) -> dict:
    occupied = r.occupied
    beds_free = max(r.capacity - occupied, 0)
    status = "closed" if not r.is_active else ("full" if beds_free == 0 else "available")
    return {
        "id": r.id, "room_number": r.room_number, "room_type": r.room_type, "block": r.block, "floor": r.floor,
        "capacity": r.capacity, "monthly_rate": r.monthly_rate, "is_active": r.is_active,
        "occupancy": occupied, "available_beds": beds_free, "status": status,
    }


def serialize_room_detail(r: Room) -> dict:
    allocs = RoomAllocation.objects.filter(room=r, is_active=True).select_related("student").order_by("start_date")
    data = serialize_room(r)
    data["occupants"] = [
        {"student_id": a.student_id, "enrollment_no": a.student.enrollment_no, "full_name": a.student.full_name,
         "allocation_id": a.id, "since": a.start_date}
        for a in allocs
    ]
    return data


def get_room_or_404(room_id: int) -> Room:
    room = room_queryset().filter(pk=room_id).first()
    if not room:
        raise ApiError(404, "not_found", "Room not found.")
    return room


def serialize_allocation(a: RoomAllocation) -> dict:
    return {
        "id": a.id, "student_id": a.student_id, "student_name": a.student.full_name,
        "enrollment_no": a.student.enrollment_no, "room_id": a.room_id, "room_number": a.room.room_number,
        "block": a.room.block, "start_date": a.start_date, "end_date": a.end_date, "is_active": a.is_active,
    }


def create_room(data: dict, actor, ip=None) -> Room:
    if Room.objects.filter(room_number__iexact=data["room_number"]).exists():
        raise ApiError(409, "duplicate", "A room with this number already exists.",
                       [{"field": "room_number", "message": "Already in use."}])
    with transaction.atomic():
        room = Room.objects.create(**data)
        audit.record(actor, "room.create", "room", room.id, {"room_number": room.room_number}, ip)
    return get_room_or_404(room.id)


def update_room(room_id: int, data: dict, actor, ip=None) -> Room:
    with transaction.atomic():
        room = Room.objects.select_for_update().filter(pk=room_id).first()
        if not room:
            raise ApiError(404, "not_found", "Room not found.")
        if Room.objects.exclude(pk=room_id).filter(room_number__iexact=data["room_number"]).exists():
            raise ApiError(409, "duplicate", "A room with this number already exists.",
                           [{"field": "room_number", "message": "Already in use."}])
        occupied = RoomAllocation.objects.filter(room=room, is_active=True).count()
        if data["capacity"] < occupied:
            raise ApiError(409, "capacity_below_occupancy",
                           f"Capacity cannot be lower than the {occupied} current occupant(s).")
        for field, value in data.items():
            setattr(room, field, value)
        room.save()
        audit.record(actor, "room.update", "room", room.id, {"fields": sorted(data)}, ip)
    return get_room_or_404(room_id)


def _assert_room_can_take_student(room: Room) -> None:
    if not room.is_active:
        raise ApiError(409, "room_closed", "This room is closed and cannot take new occupants.")
    occupied = RoomAllocation.objects.filter(room=room, is_active=True).count()
    if occupied >= room.capacity:
        raise ApiError(409, "room_full", f"Room {room.room_number} is full ({occupied}/{room.capacity}).")


def _create_allocation(student, room, start_date) -> RoomAllocation:
    try:
        with transaction.atomic():
            return RoomAllocation.objects.create(student=student, room=room, start_date=start_date)
    except IntegrityError:
        raise ApiError(409, "already_allocated", "This student already has an active room allocation.")


@transaction.atomic
def allocate_student(student_id: int, room_id: int, start_date, actor, ip=None) -> RoomAllocation:
    # Lock the room row first: concurrent requests for the same room queue here,
    # so the capacity check below cannot be raced past.
    room = Room.objects.select_for_update().filter(pk=room_id).first()
    if not room:
        raise ApiError(404, "not_found", "Room not found.")
    student = Student.objects.select_for_update().filter(pk=student_id).first()
    if not student:
        raise ApiError(404, "not_found", "Student not found.")
    if student.status != Student.Status.ACTIVE:
        raise ApiError(409, "student_not_active", "Only active students can be allocated a room.")
    if RoomAllocation.objects.filter(student=student, is_active=True).exists():
        raise ApiError(409, "already_allocated", "This student already has an active room allocation. Use transfer instead.")
    _assert_room_can_take_student(room)
    alloc = _create_allocation(student, room, start_date or timezone.localdate())
    audit.record(actor, "room.allocate", "allocation", alloc.id, {"student_id": student.id, "room_id": room.id}, ip)
    return RoomAllocation.objects.select_related("student", "room").get(pk=alloc.pk)


@transaction.atomic
def transfer_allocation(allocation_id: int, new_room_id: int, transfer_date, actor, ip=None) -> RoomAllocation:
    current = RoomAllocation.objects.select_for_update().filter(pk=allocation_id).first()
    if not current:
        raise ApiError(404, "not_found", "Allocation not found.")
    if not current.is_active:
        raise ApiError(409, "allocation_ended", "This allocation has already ended.")
    if current.room_id == new_room_id:
        raise ApiError(400, "same_room", "The student is already in this room.")
    # Lock both rooms in a fixed order to avoid deadlocks between concurrent transfers.
    rooms = {r.id: r for r in Room.objects.select_for_update().filter(id__in=[current.room_id, new_room_id]).order_by("id")}
    new_room = rooms.get(new_room_id)
    if not new_room:
        raise ApiError(404, "not_found", "Destination room not found.")
    when = transfer_date or timezone.localdate()
    if when < current.start_date:
        raise ApiError(400, "invalid_date", "Transfer date cannot be before the current allocation started.")
    _assert_room_can_take_student(new_room)
    student = Student.objects.get(pk=current.student_id)
    old_room_id = current.room_id
    current.is_active = False
    current.end_date = when
    current.save()
    alloc = _create_allocation(student, new_room, when)
    audit.record(actor, "room.transfer", "allocation", alloc.id,
                 {"student_id": student.id, "from_room_id": old_room_id, "to_room_id": new_room.id}, ip)
    return RoomAllocation.objects.select_related("student", "room").get(pk=alloc.pk)


def summary() -> dict:
    rows = list(room_queryset())
    open_rooms = [r for r in rows if r.is_active]
    beds = sum(r.capacity for r in open_rooms)
    occupied = sum(r.occupied for r in open_rooms)
    full = sum(1 for r in open_rooms if r.occupied >= r.capacity)
    return {
        "total_rooms": len(rows), "open_rooms": len(open_rooms), "available_rooms": len(open_rooms) - full,
        "full_rooms": full, "closed_rooms": len(rows) - len(open_rooms), "total_beds": beds,
        "occupied_beds": occupied, "free_beds": max(beds - occupied, 0),
        "occupancy_percent": round(occupied * 100 / beds, 1) if beds else None,
    }
