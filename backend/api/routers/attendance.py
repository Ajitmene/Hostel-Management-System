from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from accounts.models import User
from accounts.permissions import Permission
from api.core.db import DBRoute
from api.core.errors import ApiError
from api.core.pagination import Page, PageParams, make_page, paginate
from api.dependencies import client_ip, require_admin, require_any_permission, require_permission, verify_csrf
from api.schemas.attendance import (AttendanceBulkCreate, AttendanceCorrection, AttendanceOut, AttendanceSummary,
                                    AttStatus, RosterItem)
from api.services import attendance as svc
from django.utils import timezone

router = APIRouter(prefix="/attendance", tags=["Attendance"], route_class=DBRoute, dependencies=[Depends(verify_csrf)])
view_att = require_permission(Permission.ATTENDANCE_VIEW)
record_att = require_permission(Permission.ATTENDANCE_RECORD)


@router.get("", response_model=Page[AttendanceOut], summary="Attendance history",
            description="Roles: administrator, or employee with `attendance.view`.")
def list_attendance(
    params: PageParams = Depends(),
    student_id: int | None = Query(None, gt=0),
    date_: date | None = Query(None, alias="date", description="Exact date"),
    date_from: date | None = None,
    date_to: date | None = None,
    status: AttStatus | None = None,
    user: User = Depends(view_att),
):
    qs = svc.attendance_queryset()
    if student_id:
        qs = qs.filter(student_id=student_id)
    if date_:
        qs = qs.filter(date=date_)
    if date_from:
        qs = qs.filter(date__gte=date_from)
    if date_to:
        qs = qs.filter(date__lte=date_to)
    if status:
        qs = qs.filter(status=status)
    items, total = paginate(qs.order_by("-date", "student__full_name"), params)
    return make_page([svc.serialize_attendance(a) for a in items], total, params)


@router.post("", response_model=list[AttendanceOut], status_code=201, summary="Record attendance for a date",
             description="Roles: administrator, or employee with `attendance.record`. All-or-nothing: if any student already has a record "
                         "for the date the request is rejected with 409. Only an administrator can correct an existing record (PUT).",
             responses={409: {"description": "Attendance already exists for some students"}})
def record_attendance(body: AttendanceBulkCreate, request: Request, user: User = Depends(record_att)):
    records = svc.record_bulk(body.date, [e.model_dump() for e in body.records], user, client_ip(request))
    return [svc.serialize_attendance(a) for a in records]


@router.get("/roster", response_model=list[RosterItem], summary="Active students with their status for a date",
            description="Roles: administrator, or employee with `attendance.record` or `attendance.view`.")
def roster(date_: date | None = Query(None, alias="date"), user: User = Depends(require_any_permission(Permission.ATTENDANCE_VIEW, Permission.ATTENDANCE_RECORD))):
    return svc.roster(date_ or timezone.localdate())


@router.get("/summary", response_model=AttendanceSummary, summary="Attendance percentages",
            description="Roles: administrator, or employee with `attendance.view`. Percentage = present days / marked days.")
def summary(
    date_from: date | None = None,
    date_to: date | None = None,
    student_id: int | None = Query(None, gt=0),
    user: User = Depends(view_att),
):
    today = timezone.localdate()
    start = date_from or today.replace(day=1)
    end = date_to or today
    if start > end:
        raise ApiError(422, "invalid_range", "date_from must not be after date_to.")
    return svc.summary(start, end, student_id)


@router.put("/{attendance_id}", response_model=AttendanceOut, summary="Correct an attendance record",
            description="Roles: administrator only. A reason is required and the before/after values are written to the audit log.")
def correct(attendance_id: int, body: AttendanceCorrection, request: Request, user: User = Depends(require_admin)):
    record = svc.correct(attendance_id, body.status, body.remarks, body.reason, user, client_ip(request))
    return svc.serialize_attendance(record)
