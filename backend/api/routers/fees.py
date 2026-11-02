from datetime import date

from fastapi import APIRouter, Depends, Query, Request, Response

from accounts.models import User
from accounts.permissions import Permission
from api.core.db import DBRoute
from api.core.errors import ApiError
from api.core.pagination import Page, PageParams, apply_ordering, make_page, paginate
from api.dependencies import client_ip, require_admin, require_permission, verify_csrf
from api.schemas.fees import (FeeStatus, FeeSummary, FeeStructureCreate, FeeStructureOut, PaymentCreate, PaymentOut,
                              ReceiptOut, StudentFeeCreate, StudentFeeOut)
from api.services import fees as svc
from django.utils import timezone
from fees.models import FeeStructure

router = APIRouter(prefix="/fees", tags=["Fees and payments"], route_class=DBRoute, dependencies=[Depends(verify_csrf)])
view_fees = require_permission(Permission.FEES_VIEW)
ORDERING = {"due_date": "due_date", "amount_due": "amount_due", "student": "student__full_name"}


def _fee_list(params, q, student_id, status, due_from, due_to, ordering, unpaid_only=False):
    today = timezone.localdate()
    qs = svc.fee_queryset()
    if q:
        from django.db.models import Q
        qs = qs.filter(Q(student__full_name__icontains=q) | Q(student__enrollment_no__icontains=q))
    if student_id:
        qs = qs.filter(student_id=student_id)
    if due_from:
        qs = qs.filter(due_date__gte=due_from)
    if due_to:
        qs = qs.filter(due_date__lte=due_to)
    if unpaid_only:
        from django.db.models import F
        qs = qs.filter(paid__lt=F("amount_due"))
    if status:
        qs = svc.filter_by_status(qs, status, today)
    items, total = paginate(apply_ordering(qs, ordering, ORDERING), params)
    return make_page([svc.serialize_fee(f, today) for f in items], total, params)


@router.get("", response_model=Page[StudentFeeOut], summary="List student fees",
            description="Roles: administrator, or employee with `fees.view`.")
def list_fees(
    params: PageParams = Depends(),
    q: str | None = Query(None, max_length=100),
    student_id: int | None = Query(None, gt=0),
    status: FeeStatus | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    ordering: str = Query("-due_date"),
    user: User = Depends(view_fees),
):
    return _fee_list(params, q, student_id, status, due_from, due_to, ordering)


@router.post("", response_model=StudentFeeOut, status_code=201, summary="Charge a fee to a student",
             description="Roles: administrator only. `amount_due` defaults to the fee structure's amount.")
def create_fee(body: StudentFeeCreate, request: Request, user: User = Depends(require_admin)):
    return svc.serialize_fee(svc.create_fee(body.model_dump(), user, client_ip(request)))


@router.get("/summary", response_model=FeeSummary, summary="Fee and collection totals",
            description="Roles: administrator, or employee with `fees.view`.")
def fees_summary(user: User = Depends(view_fees)):
    return svc.summary()


@router.get("/structures", response_model=list[FeeStructureOut], summary="List fee structures",
            description="Roles: administrator, or employee with `fees.view`.")
def list_structures(user: User = Depends(view_fees)):
    return [svc.serialize_structure(s) for s in FeeStructure.objects.all()]


@router.post("/structures", response_model=FeeStructureOut, status_code=201, summary="Create a fee structure",
             description="Roles: administrator only.")
def create_structure(body: FeeStructureCreate, request: Request, user: User = Depends(require_admin)):
    return svc.serialize_structure(svc.create_structure(body.model_dump(), user, client_ip(request)))


@router.get("/pending", response_model=Page[StudentFeeOut], summary="Unpaid and overdue fees",
            description="Roles: administrator, or employee with `fees.view`. Set `overdue_only` to see only past-due fees.")
def pending_fees(
    params: PageParams = Depends(),
    overdue_only: bool = False,
    q: str | None = Query(None, max_length=100),
    ordering: str = Query("due_date"),
    user: User = Depends(view_fees),
):
    return _fee_list(params, q, None, "overdue" if overdue_only else None, None, None, ordering, unpaid_only=True)


@router.get("/payments", response_model=Page[PaymentOut], summary="Payment history",
            description="Roles: administrator, or employee with `fees.view`.")
def list_payments(
    params: PageParams = Depends(),
    fee_id: int | None = Query(None, gt=0),
    student_id: int | None = Query(None, gt=0),
    date_from: date | None = None,
    date_to: date | None = None,
    user: User = Depends(view_fees),
):
    qs = svc.payment_queryset()
    if fee_id:
        qs = qs.filter(fee_id=fee_id)
    if student_id:
        qs = qs.filter(fee__student_id=student_id)
    if date_from:
        qs = qs.filter(payment_date__gte=date_from)
    if date_to:
        qs = qs.filter(payment_date__lte=date_to)
    items, total = paginate(qs, params)
    return make_page([svc.serialize_payment(p) for p in items], total, params)


@router.post("/payments", response_model=PaymentOut, status_code=201, summary="Record a payment",
             description="Roles: administrator only. Manual recording only: no online payment gateway is integrated. "
                         "Sending the same `idempotency_key` again returns the original payment (HTTP 200) instead of creating a duplicate.",
             responses={200: {"description": "Duplicate submission: the original payment is returned"},
                        409: {"description": "Overpayment, fee already paid, or duplicate transaction reference"}})
def record_payment(body: PaymentCreate, request: Request, response: Response, user: User = Depends(require_admin)):
    payment, created = svc.record_payment(body.model_dump(), user, client_ip(request))
    response.status_code = 201 if created else 200
    return svc.serialize_payment(payment)


@router.get("/payments/{payment_id}/receipt", response_model=ReceiptOut, summary="Payment receipt",
            description="Roles: administrator, or employee with `fees.view`.")
def receipt(payment_id: int, user: User = Depends(view_fees)):
    payment = svc.payment_queryset().filter(pk=payment_id).first()
    if not payment:
        raise ApiError(404, "not_found", "Payment not found.")
    return svc.serialize_receipt(payment)


@router.get("/{fee_id}", response_model=StudentFeeOut, summary="Get a fee record",
            description="Roles: administrator, or employee with `fees.view`.")
def get_fee(fee_id: int, user: User = Depends(view_fees)):
    return svc.serialize_fee(svc.get_fee_or_404(fee_id))
