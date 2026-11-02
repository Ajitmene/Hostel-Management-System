from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.utils import timezone

from api.core.errors import ApiError
from api.services import audit
from attendance.models import Attendance
from rooms.models import RoomAllocation
from students.models import Student


def attendance_queryset():
    return Attendance.objects.select_related("student", "recorded_by")


def serialize_attendance(a: Attendance) -> dict:
    return {
        "id": a.id, "student_id": a.student_id, "student_name": a.student.full_name,
        "enrollment_no": a.student.enrollment_no, "date": a.date, "status": a.status,
        "remarks": a.remarks, "recorded_by": a.recorded_by.email,
    }


def record_bulk(day, entries: list[dict], actor, ip=None) -> list[Attendance]:
    if day > timezone.localdate():
        raise ApiError(400, "invalid_date", "Attendance cannot be recorded for a future date.")
    ids = [e["student_id"] for e in entries]
    if len(ids) != len(set(ids)):
        raise ApiError(422, "duplicate_entries", "Each student may appear only once per submission.")
    students = {s.id: s for s in Student.objects.filter(id__in=ids)}
    missing = sorted(set(ids) - set(students))
    if missing:
        raise ApiError(404, "not_found", "Some students were not found.", {"student_ids": missing})
    inactive = sorted(i for i, s in students.items() if s.status != Student.Status.ACTIVE)
    if inactive:
        raise ApiError(409, "student_not_active", "Attendance can only be recorded for active students.", {"student_ids": inactive})
    try:
        with transaction.atomic():
            existing = sorted(Attendance.objects.filter(date=day, student_id__in=ids).values_list("student_id", flat=True))
            if existing:
                raise ApiError(409, "attendance_exists",
                               "Attendance already exists for some students on this date. An administrator can correct it.",
                               {"student_ids": existing})
            created = [Attendance(student_id=e["student_id"], date=day, status=e["status"],
                                  remarks=e.get("remarks", ""), recorded_by=actor) for e in entries]
            Attendance.objects.bulk_create(created)
            audit.record(actor, "attendance.record", "attendance", str(day), {"count": len(created)}, ip)
    except IntegrityError:
        raise ApiError(409, "attendance_exists", "Attendance was recorded concurrently. Reload and try again.")
    return list(attendance_queryset().filter(date=day, student_id__in=ids))


def correct(attendance_id: int, status: str, remarks: str, reason: str, actor, ip=None) -> Attendance:
    with transaction.atomic():
        record = Attendance.objects.select_for_update().filter(pk=attendance_id).first()
        if not record:
            raise ApiError(404, "not_found", "Attendance record not found.")
        before = {"status": record.status, "remarks": record.remarks}
        record.status, record.remarks = status, remarks
        record.save()
        audit.record(actor, "attendance.correct", "attendance", record.id,
                     {"before": before, "after": {"status": status, "remarks": remarks}, "reason": reason}, ip)
    return attendance_queryset().get(pk=attendance_id)


def roster(day) -> list[dict]:
    students = Student.objects.filter(status=Student.Status.ACTIVE).order_by("full_name")
    marks = {a.student_id: a for a in Attendance.objects.filter(date=day)}
    rooms = {a.student_id: a.room for a in RoomAllocation.objects.filter(is_active=True).select_related("room")}
    out = []
    for s in students:
        mark = marks.get(s.id)
        room = rooms.get(s.id)
        out.append({
            "student_id": s.id, "enrollment_no": s.enrollment_no, "full_name": s.full_name,
            "room": f"{room.block}-{room.room_number}" if room else None,
            "attendance_id": mark.id if mark else None, "status": mark.status if mark else None,
            "remarks": mark.remarks if mark else "",
        })
    return out


def summary(date_from, date_to, student_id: int | None = None) -> dict:
    in_range = Q(attendance_records__date__gte=date_from, attendance_records__date__lte=date_to)
    qs = Student.objects.annotate(
        present=Count("attendance_records", filter=in_range & Q(attendance_records__status="present")),
        absent=Count("attendance_records", filter=in_range & Q(attendance_records__status="absent")),
        leave=Count("attendance_records", filter=in_range & Q(attendance_records__status="leave")),
    )
    if student_id:
        qs = qs.filter(pk=student_id)
    rows, totals = [], {"present": 0, "absent": 0, "leave": 0}
    for s in qs.order_by("full_name"):
        marked = s.present + s.absent + s.leave
        if marked == 0 and s.status != Student.Status.ACTIVE:
            continue
        for key in totals:
            totals[key] += getattr(s, key)
        rows.append({
            "student_id": s.id, "enrollment_no": s.enrollment_no, "full_name": s.full_name,
            "present": s.present, "absent": s.absent, "leave": s.leave, "marked_days": marked,
            "percentage": round(s.present * 100 / marked, 1) if marked else None,
        })
    all_marked = sum(totals.values())
    return {
        "date_from": date_from, "date_to": date_to, "totals": totals,
        "overall_percentage": round(totals["present"] * 100 / all_marked, 1) if all_marked else None,
        "students": rows,
    }
