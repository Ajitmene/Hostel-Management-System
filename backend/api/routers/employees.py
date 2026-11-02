from fastapi import APIRouter, Depends, Query, Request

from accounts.models import User
from api.core.db import DBRoute
from api.core.pagination import Page, PageParams, make_page, paginate
from api.dependencies import client_ip, require_admin, verify_csrf
from api.schemas.common import Message
from api.schemas.employees import EmployeeCreate, EmployeeOut, EmployeeStatus, EmployeeUpdate, PasswordReset
from api.services import employees as svc
from django.db.models import Q

router = APIRouter(prefix="/employees", tags=["Employees"], route_class=DBRoute,
                   dependencies=[Depends(verify_csrf), Depends(require_admin)])


@router.get("", response_model=Page[EmployeeOut], summary="List employees", description="Roles: administrator only.")
def list_employees(
    params: PageParams = Depends(),
    q: str | None = Query(None, max_length=100, description="Search name, email or employee ID"),
    is_active: bool | None = None,
):
    qs = svc.employee_queryset()
    if q:
        qs = qs.filter(Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
                       | Q(user__email__icontains=q) | Q(employee_id__icontains=q))
    if is_active is not None:
        qs = qs.filter(user__is_active=is_active)
    items, total = paginate(qs.order_by("employee_id"), params)
    return make_page([svc.serialize_employee(p) for p in items], total, params)


@router.post("", response_model=EmployeeOut, status_code=201, summary="Create an employee account",
             description="Roles: administrator only. The role is always `employee`; administrator accounts can only be created "
                         "with `manage.py createsuperuser` or Django Admin.")
def create_employee(body: EmployeeCreate, request: Request, admin: User = Depends(require_admin)):
    return svc.serialize_employee(svc.create_employee(body.model_dump(), admin, client_ip(request)))


@router.get("/{employee_id}", response_model=EmployeeOut, summary="Get an employee", description="Roles: administrator only.")
def get_employee(employee_id: int):
    return svc.serialize_employee(svc.get_employee_or_404(employee_id))


@router.put("/{employee_id}", response_model=EmployeeOut, summary="Update an employee and their permissions",
            description="Roles: administrator only.")
def update_employee(employee_id: int, body: EmployeeUpdate, request: Request, admin: User = Depends(require_admin)):
    return svc.serialize_employee(svc.update_employee(employee_id, body.model_dump(), admin, client_ip(request)))


@router.patch("/{employee_id}/status", response_model=EmployeeOut, summary="Activate or deactivate an account",
              description="Roles: administrator only. Deactivation signs the employee out immediately.")
def set_status(employee_id: int, body: EmployeeStatus, request: Request, admin: User = Depends(require_admin)):
    return svc.serialize_employee(svc.set_active(employee_id, body.is_active, admin, client_ip(request)))


@router.post("/{employee_id}/reset-password", response_model=Message, summary="Set a new password for an employee",
             description="Roles: administrator only. Signs the employee out everywhere.")
def reset_password(employee_id: int, body: PasswordReset, request: Request, admin: User = Depends(require_admin)):
    svc.reset_password(employee_id, body.new_password, admin, client_ip(request))
    return {"message": "Password updated."}
