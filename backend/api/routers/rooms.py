from typing import Literal

from fastapi import APIRouter, Depends, Query, Request
from django.db.models import F

from accounts.models import User
from accounts.permissions import Permission
from api.core.db import DBRoute
from api.core.errors import ApiError
from api.core.pagination import Page, PageParams, apply_ordering, make_page, paginate
from api.dependencies import client_ip, require_admin, require_permission, verify_csrf
from api.schemas.rooms import (AllocationCreate, AllocationOut, RoomCreate, RoomDetail, RoomOut,
                               RoomSummary, RoomType, RoomUpdate, TransferRequest)
from api.services import rooms as svc
from rooms.models import RoomAllocation

router = APIRouter(prefix="/rooms", tags=["Rooms and allocations"], route_class=DBRoute, dependencies=[Depends(verify_csrf)])

ORDERING = {"room_number": "room_number", "block": "block", "floor": "floor", "capacity": "capacity", "monthly_rate": "monthly_rate"}
view_rooms = require_permission(Permission.ROOMS_VIEW)


def _filtered(qs, q=None, block=None, room_type=None, status=None):
    if q:
        qs = qs.filter(room_number__icontains=q)
    if block:
        qs = qs.filter(block__iexact=block)
    if room_type:
        qs = qs.filter(room_type=room_type)
    if status == "available":
        qs = qs.filter(is_active=True, occupied__lt=F("capacity"))
    elif status == "full":
        qs = qs.filter(is_active=True, occupied__gte=F("capacity"))
    elif status == "closed":
        qs = qs.filter(is_active=False)
    return qs


@router.get("", response_model=Page[RoomOut], summary="List rooms",
            description="Roles: administrator, or employee with `rooms.view`.")
def list_rooms(
    params: PageParams = Depends(),
    q: str | None = Query(None, max_length=20, description="Room number contains"),
    block: str | None = Query(None, max_length=50),
    room_type: RoomType | None = None,
    status: Literal["available", "full", "closed"] | None = None,
    ordering: str = Query("block", description="block, room_number, floor, capacity, monthly_rate"),
    user: User = Depends(view_rooms),
):
    qs = apply_ordering(_filtered(svc.room_queryset(), q, block, room_type, status), ordering, ORDERING)
    items, total = paginate(qs, params)
    return make_page([svc.serialize_room(r) for r in items], total, params)


@router.post("", response_model=RoomDetail, status_code=201, summary="Create a room", description="Roles: administrator only.")
def create_room(body: RoomCreate, request: Request, user: User = Depends(require_admin)):
    return svc.serialize_room_detail(svc.create_room(body.model_dump(), user, client_ip(request)))


@router.get("/summary", response_model=RoomSummary, summary="Room and bed totals",
            description="Roles: administrator, or employee with `rooms.view`. Counts only open rooms for bed figures.")
def rooms_summary(user: User = Depends(view_rooms)):
    return svc.summary()


@router.get("/available", response_model=list[RoomOut], summary="Rooms with free beds",
            description="Roles: administrator, or employee with `rooms.view`.")
def available_rooms(user: User = Depends(view_rooms)):
    qs = _filtered(svc.room_queryset(), status="available").order_by("block", "room_number")
    return [svc.serialize_room(r) for r in qs]


@router.get("/allocations", response_model=Page[AllocationOut], summary="Allocation history",
            description="Roles: administrator, or employee with `rooms.view`.")
def list_allocations(
    params: PageParams = Depends(),
    active_only: bool = True,
    student_id: int | None = Query(None, gt=0),
    room_id: int | None = Query(None, gt=0),
    user: User = Depends(view_rooms),
):
    qs = RoomAllocation.objects.select_related("student", "room")
    if active_only:
        qs = qs.filter(is_active=True)
    if student_id:
        qs = qs.filter(student_id=student_id)
    if room_id:
        qs = qs.filter(room_id=room_id)
    items, total = paginate(qs, params)
    return make_page([svc.serialize_allocation(a) for a in items], total, params)


@router.post("/allocations", response_model=AllocationOut, status_code=201, summary="Allocate a student to a room",
             description="Roles: administrator only. Runs in a transaction with a row lock, so capacity can never be exceeded.",
             responses={409: {"description": "Room full, room closed, student inactive or already allocated"}})
def allocate(body: AllocationCreate, request: Request, user: User = Depends(require_admin)):
    alloc = svc.allocate_student(body.student_id, body.room_id, body.start_date, user, client_ip(request))
    return svc.serialize_allocation(alloc)


@router.post("/allocations/{allocation_id}/transfer", response_model=AllocationOut, status_code=201,
             summary="Transfer a student to another room", description="Roles: administrator only. Ends the old allocation and creates a new one atomically.")
def transfer(allocation_id: int, body: TransferRequest, request: Request, user: User = Depends(require_admin)):
    alloc = svc.transfer_allocation(allocation_id, body.new_room_id, body.transfer_date, user, client_ip(request))
    return svc.serialize_allocation(alloc)


@router.get("/{room_id}", response_model=RoomDetail, summary="Get a room with its occupants",
            description="Roles: administrator, or employee with `rooms.view`.")
def get_room(room_id: int, user: User = Depends(view_rooms)):
    return svc.serialize_room_detail(svc.get_room_or_404(room_id))


@router.put("/{room_id}", response_model=RoomDetail, summary="Update a room", description="Roles: administrator only.")
def update_room(room_id: int, body: RoomUpdate, request: Request, user: User = Depends(require_admin)):
    return svc.serialize_room_detail(svc.update_room(room_id, body.model_dump(), user, client_ip(request)))
