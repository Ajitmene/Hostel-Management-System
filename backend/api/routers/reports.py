from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from django.utils import timezone

from api.core.db import DBRoute
from api.core.errors import ApiError
from api.dependencies import require_admin, verify_csrf
from api.schemas.reports import ReportOut
from api.services import reports as svc

router = APIRouter(prefix="/reports", tags=["Reports"], route_class=DBRoute,
                   dependencies=[Depends(verify_csrf), Depends(require_admin)])

Fmt = Literal["json", "csv"]


def _range(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    end = date_to or timezone.localdate()
    start = date_from or (end - timedelta(days=30))
    if start > end:
        raise ApiError(422, "invalid_range", "date_from must not be after date_to.")
    return start, end


def _respond(report: dict, fmt: str, filename: str):
    if fmt == "csv":
        return Response(
            content=svc.to_csv(report), media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )
    return report


@router.get("/registrations", response_model=ReportOut, summary="Student registrations",
            description="Roles: administrator only. Use `format=csv` to download.")
def registrations(date_from: date | None = None, date_to: date | None = None,
                  fmt: Fmt = Query("json", alias="format")):
    start, end = _range(date_from, date_to)
    return _respond(svc.registrations(start, end), fmt, "student-registrations")


@router.get("/occupancy", response_model=ReportOut, summary="Room occupancy and available rooms",
            description="Roles: administrator only. Set `available_only` for the available-rooms report.")
def occupancy(available_only: bool = False, fmt: Fmt = Query("json", alias="format")):
    return _respond(svc.occupancy(available_only), fmt, "available-rooms" if available_only else "room-occupancy")


@router.get("/fees", response_model=ReportOut, summary="Fee collections",
            description="Roles: administrator only. Payments received between the two dates.")
def fees(date_from: date | None = None, date_to: date | None = None, fmt: Fmt = Query("json", alias="format")):
    start, end = _range(date_from, date_to)
    return _respond(svc.fee_collections(start, end), fmt, "fee-collections")


@router.get("/outstanding", response_model=ReportOut, summary="Outstanding fees",
            description="Roles: administrator only. Fees with an unpaid balance, optionally limited by due date.")
def outstanding(date_from: date | None = None, date_to: date | None = None, fmt: Fmt = Query("json", alias="format")):
    if date_from and date_to and date_from > date_to:
        raise ApiError(422, "invalid_range", "date_from must not be after date_to.")
    return _respond(svc.outstanding(date_from, date_to), fmt, "outstanding-fees")


@router.get("/attendance", response_model=ReportOut, summary="Attendance summary",
            description="Roles: administrator only.")
def attendance(date_from: date | None = None, date_to: date | None = None, fmt: Fmt = Query("json", alias="format")):
    start, end = _range(date_from, date_to)
    return _respond(svc.attendance_report(start, end), fmt, "attendance-summary")
