from fastapi import APIRouter, Depends, Query, Request

from accounts.models import User
from accounts.permissions import Permission
from api.core.db import DBRoute
from api.core.pagination import Page, PageParams, apply_ordering, make_page, paginate
from api.dependencies import client_ip, require_admin, require_permission, verify_csrf
from api.schemas.students import StatusUpdate, StudentCreate, StudentOut, StudentStatus, StudentSummary, StudentUpdate
from api.services import students as svc

router = APIRouter(prefix="/students", tags=["Students"], route_class=DBRoute, dependencies=[Depends(verify_csrf)])

ORDERING = {"name": "full_name", "enrollment_no": "enrollment_no", "admission_date": "admission_date", "status": "status"}


@router.get("", response_model=Page[StudentOut], summary="List students",
            description="Roles: administrator, or employee with `students.view`. Supports search, filters, sorting and pagination.")
def list_students(
    params: PageParams = Depends(),
    q: str | None = Query(None, max_length=100, description="Search by name or enrollment number"),
    status: StudentStatus | None = None,
    room_id: int | None = Query(None, gt=0, description="Only students currently in this room"),
    ordering: str = Query("name", description="name, enrollment_no, admission_date, status (prefix with - for descending)"),
    user: User = Depends(require_permission(Permission.STUDENTS_VIEW)),
):
    qs = apply_ordering(svc.filter_students(svc.student_queryset(), q, status, room_id), ordering, ORDERING)
    items, total = paginate(qs, params)
    return make_page([svc.serialize_student(s) for s in items], total, params)


@router.post("", response_model=StudentOut, status_code=201, summary="Create a student",
             description="Roles: administrator only.", responses={409: {"description": "Duplicate enrollment number or email"}})
def create_student(body: StudentCreate, request: Request, user: User = Depends(require_admin)):
    return svc.serialize_student(svc.create_student(body.model_dump(), user, client_ip(request)))


@router.get("/summary", response_model=StudentSummary, summary="Student counts",
            description="Roles: administrator, or employee with `students.view`.")
def students_summary(user: User = Depends(require_permission(Permission.STUDENTS_VIEW))):
    return svc.summary()


@router.get("/{student_id}", response_model=StudentOut, summary="Get a student",
            description="Roles: administrator, or employee with `students.view`.")
def get_student(student_id: int, user: User = Depends(require_permission(Permission.STUDENTS_VIEW))):
    return svc.serialize_student(svc.get_student_or_404(student_id))


@router.put("/{student_id}", response_model=StudentOut, summary="Update a student", description="Roles: administrator only.")
def update_student(student_id: int, body: StudentUpdate, request: Request, user: User = Depends(require_admin)):
    return svc.serialize_student(svc.update_student(student_id, body.model_dump(), user, client_ip(request)))


@router.patch("/{student_id}/status", response_model=StudentOut, summary="Activate or deactivate a student",
              description="Roles: administrator only. Leaving `inactive`/`left` ends the active room allocation but keeps all history.")
def update_status(student_id: int, body: StatusUpdate, request: Request, user: User = Depends(require_admin)):
    return svc.serialize_student(svc.set_status(student_id, body.status, user, client_ip(request)))
