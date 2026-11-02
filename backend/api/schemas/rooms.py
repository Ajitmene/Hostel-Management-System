from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.common import MoneyOut

RoomType = Literal["single", "double", "triple", "dormitory"]


class RoomCreate(BaseModel):
    room_number: str = Field(min_length=1, max_length=20)
    room_type: RoomType
    block: str = Field(min_length=1, max_length=50)
    floor: int = Field(ge=0, le=100)
    capacity: int = Field(ge=1, le=50)
    monthly_rate: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    is_active: bool = True

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "room_number": "101", "room_type": "double", "block": "A", "floor": 1,
        "capacity": 2, "monthly_rate": "4500.00", "is_active": True,
    }]})


class RoomUpdate(RoomCreate):
    pass


class RoomOut(BaseModel):
    id: int
    room_number: str
    room_type: str
    block: str
    floor: int
    capacity: int
    monthly_rate: MoneyOut
    is_active: bool
    occupancy: int
    available_beds: int
    status: str  # available | full | closed


class OccupantOut(BaseModel):
    student_id: int
    enrollment_no: str
    full_name: str
    allocation_id: int
    since: date


class RoomDetail(RoomOut):
    occupants: list[OccupantOut]


class AllocationCreate(BaseModel):
    student_id: int = Field(gt=0)
    room_id: int = Field(gt=0)
    start_date: date | None = None

    model_config = ConfigDict(json_schema_extra={"examples": [{"student_id": 1, "room_id": 1}]})


class TransferRequest(BaseModel):
    new_room_id: int = Field(gt=0)
    transfer_date: date | None = None


class AllocationOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    enrollment_no: str
    room_id: int
    room_number: str
    block: str
    start_date: date
    end_date: date | None
    is_active: bool


class RoomSummary(BaseModel):
    total_rooms: int
    open_rooms: int
    available_rooms: int
    full_rooms: int
    closed_rooms: int
    total_beds: int
    occupied_beds: int
    free_beds: int
    occupancy_percent: float | None
