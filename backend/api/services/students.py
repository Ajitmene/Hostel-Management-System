from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from django.utils import timezone

from api.core.errors import ApiError
from api.services import audit
from rooms.models import RoomAllocation
from students.models import Student


def student_queryset():
    active = RoomAllocation.objects.filter(is_active=True).select_related("room")
    return Student.objects.prefetch_related(Prefetch("allocations", queryset=active, to_attr="active_allocs"))


def serialize_student(s: Student) -> dict:
    alloc = s.active_allocs[0] if getattr(s, "active_allocs", None) else None
    return {
        "id": s.id, "enrollment_no": s.enrollment_no, "full_name": s.full_name, "email": s.email,
        "phone": s.phone, "gender": s.gender, "address": s.address, "guardian_name": s.guardian_name,
        "guardian_phone": s.guardian_phone, "admission_date": s.admission_date, "status": s.status,
        "room": {"id": alloc.room.id, "room_number": alloc.room.room_number, "block": alloc.room.block} if alloc else None,
    }


def filter_students(qs, q=None, status=None, room_id=None):
    if q:
        qs = qs.filter(Q(full_name__icontains=q) | Q(enrollment_no__icontains=q))
    if status:
        qs = qs.filter(status=status)
    if room_id:
        qs = qs.filter(allocations__room_id=room_id, allocations__is_active=True)
    return qs


def get_student_or_404(student_id: int) -> Student:
    student = student_queryset().filter(pk=student_id).first()
    if not student:
        raise ApiError(404, "not_found", "Student not found.")
    return student


def _check_unique(data: dict, exclude_id: int | None = None) -> None:
    problems = []
    qs = Student.objects.all()
    if exclude_id:
        qs = qs.exclude(pk=exclude_id)
    if qs.filter(enrollment_no__iexact=data["enrollment_no"]).exists():
        problems.append({"field": "enrollment_no", "message": "This enrollment number is already in use."})
    if qs.filter(email__iexact=data["email"]).exists():
        problems.append({"field": "email", "message": "This email is already registered to another student."})
    if problems:
        raise ApiError(409, "duplicate", "A student with these details already exists.", problems)


def create_student(data: dict, actor, ip=None) -> Student:
    _check_unique(data)
    try:
        with transaction.atomic():
            student = Student.objects.create(**data)
            audit.record(actor, "student.create", "student", student.id, {"enrollment_no": student.enrollment_no}, ip)
    except IntegrityError:
        raise ApiError(409, "duplicate", "A student with these details already exists.")
    return get_student_or_404(student.id)


def update_student(student_id: int, data: dict, actor, ip=None) -> Student:
    student = get_student_or_404(student_id)
    _check_unique(data, exclude_id=student.id)
    with transaction.atomic():
        for field, value in data.items():
            setattr(student, field, value)
        student.save()
        audit.record(actor, "student.update", "student", student.id, {"fields": sorted(data)}, ip)
    return get_student_or_404(student_id)


def set_status(student_id: int, status: str, actor, ip=None) -> Student:
    """Deactivating never deletes history: the active allocation is ended, not removed."""
    student = get_student_or_404(student_id)
    with transaction.atomic():
        previous = student.status
        student.status = status
        student.save(update_fields=["status", "updated_at"])
        if status != Student.Status.ACTIVE:
            today = timezone.localdate()
            for alloc in RoomAllocation.objects.select_for_update().filter(student=student, is_active=True):
                alloc.is_active = False
                alloc.end_date = max(today, alloc.start_date)
                alloc.save()
        audit.record(actor, "student.status", "student", student.id, {"from": previous, "to": status}, ip)
    return get_student_or_404(student_id)


def summary() -> dict:
    counts = dict(Student.objects.values_list("status").annotate(n=Count("id")))
    active = counts.get("active", 0)
    allocated = RoomAllocation.objects.filter(is_active=True, student__status=Student.Status.ACTIVE).count()
    return {
        "total": sum(counts.values()), "active": active, "inactive": counts.get("inactive", 0),
        "left": counts.get("left", 0), "allocated": allocated, "unallocated": max(active - allocated, 0),
    }
