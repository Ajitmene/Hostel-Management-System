import csv
import io
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce

from api.services import attendance as attendance_service
from api.services.fees import derive_status
from django.utils import timezone
from fees.models import Payment, StudentFee
from rooms.models import Room, RoomAllocation
from students.models import Student

ZERO = Decimal("0.00")
MONEY = DecimalField(max_digits=14, decimal_places=2)


def registrations(date_from, date_to) -> dict:
    qs = Student.objects.filter(admission_date__gte=date_from, admission_date__lte=date_to).order_by("admission_date", "full_name")
    rooms = {a.student_id: a.room for a in RoomAllocation.objects.filter(is_active=True).select_related("room")}
    rows = []
    for s in qs:
        r = rooms.get(s.id)
        rows.append([s.enrollment_no, s.full_name, s.email, s.phone, s.gender, s.admission_date.isoformat(),
                     s.status, f"{r.block}-{r.room_number}" if r else ""])
    return {"title": "Student registrations",
            "columns": ["Enrollment no", "Name", "Email", "Phone", "Gender", "Admission date", "Status", "Room"],
            "rows": rows, "summary": {"registrations": len(rows)}}


def occupancy(available_only: bool = False) -> dict:
    rooms = Room.objects.annotate(occupied=Count("allocations", filter=Q(allocations__is_active=True))).order_by("block", "room_number")
    rows, beds, filled = [], 0, 0
    for r in rooms:
        free = max(r.capacity - r.occupied, 0)
        status = "closed" if not r.is_active else ("full" if free == 0 else "available")
        if available_only and status != "available":
            continue
        rows.append([r.block, r.room_number, r.floor, r.room_type, r.capacity, r.occupied, free, status])
        if r.is_active:
            beds += r.capacity
            filled += r.occupied
    return {"title": "Available rooms" if available_only else "Room occupancy",
            "columns": ["Block", "Room", "Floor", "Type", "Capacity", "Occupied", "Free beds", "Status"],
            "rows": rows, "summary": {"rooms": len(rows), "open_beds": beds, "occupied_beds": filled,
                                      "occupancy_percent": round(filled * 100 / beds, 1) if beds else None}}


def fee_collections(date_from, date_to) -> dict:
    qs = Payment.objects.filter(payment_date__gte=date_from, payment_date__lte=date_to) \
        .select_related("fee__student", "fee__structure", "recorded_by").order_by("payment_date", "id")
    rows, total = [], ZERO
    for p in qs:
        total += p.amount
        rows.append([p.receipt_number, p.payment_date.isoformat(), p.fee.student.enrollment_no, p.fee.student.full_name,
                     p.fee.structure.name, str(p.amount), p.method, p.transaction_reference or "", p.recorded_by.email])
    return {"title": "Fee collections",
            "columns": ["Receipt", "Date", "Enrollment no", "Student", "Fee", "Amount", "Method", "Reference", "Recorded by"],
            "rows": rows, "summary": {"payments": len(rows), "total_collected": str(total)}}


def outstanding(date_from=None, date_to=None) -> dict:
    qs = StudentFee.objects.select_related("student", "structure").annotate(
        paid=Coalesce(Sum("payments__amount"), Value(ZERO), output_field=MONEY)
    ).filter(paid__lt=F("amount_due"))
    if date_from:
        qs = qs.filter(due_date__gte=date_from)
    if date_to:
        qs = qs.filter(due_date__lte=date_to)
    today = timezone.localdate()
    rows, total = [], ZERO
    for f in qs.order_by("due_date", "id"):
        bal = f.amount_due - f.paid
        total += bal
        rows.append([f.student.enrollment_no, f.student.full_name, f.structure.name, f.due_date.isoformat(),
                     str(f.amount_due), str(f.paid), str(bal), derive_status(f.amount_due, f.paid, f.due_date, today)])
    return {"title": "Outstanding fees",
            "columns": ["Enrollment no", "Student", "Fee", "Due date", "Amount due", "Paid", "Balance", "Status"],
            "rows": rows, "summary": {"fees": len(rows), "total_outstanding": str(total)}}


def attendance_report(date_from, date_to) -> dict:
    data = attendance_service.summary(date_from, date_to)
    rows = [[s["enrollment_no"], s["full_name"], s["present"], s["absent"], s["leave"], s["marked_days"],
             "" if s["percentage"] is None else s["percentage"]] for s in data["students"]]
    return {"title": "Attendance summary",
            "columns": ["Enrollment no", "Student", "Present", "Absent", "Leave", "Marked days", "Attendance %"],
            "rows": rows, "summary": {**data["totals"], "overall_percentage": data["overall_percentage"]}}


def _safe_cell(value):
    """Neutralise spreadsheet formula injection (cells starting with = + - @)."""
    text = "" if value is None else str(value)
    return "'" + text if text[:1] in ("=", "+", "-", "@", "\t", "\r") else text


def to_csv(report: dict) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(report["columns"])
    for row in report["rows"]:
        writer.writerow([_safe_cell(c) for c in row])
    return buf.getvalue()
