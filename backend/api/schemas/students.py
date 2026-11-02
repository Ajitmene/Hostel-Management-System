from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from api.schemas.common import Name, Phone

Gender = Literal["male", "female", "other"]
StudentStatus = Literal["active", "inactive", "left"]


class StudentCreate(BaseModel):
    enrollment_no: str = Field(min_length=1, max_length=30, pattern=r"^[A-Za-z0-9\-_/]+$")
    full_name: Name
    email: EmailStr
    phone: Phone
    gender: Gender
    address: str = Field(min_length=1, max_length=500)
    guardian_name: Name
    guardian_phone: Phone
    admission_date: date

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "enrollment_no": "2026-BIT-014", "full_name": "Asha Patil", "email": "asha@example.com",
        "phone": "+919800000001", "gender": "female", "address": "12 MG Road, Pune",
        "guardian_name": "Ramesh Patil", "guardian_phone": "+919800000002", "admission_date": "2026-07-01",
    }]})


class StudentUpdate(StudentCreate):
    pass


class StatusUpdate(BaseModel):
    status: StudentStatus


class RoomRef(BaseModel):
    id: int
    room_number: str
    block: str


class StudentOut(BaseModel):
    id: int
    enrollment_no: str
    full_name: str
    email: str
    phone: str
    gender: str
    address: str
    guardian_name: str
    guardian_phone: str
    admission_date: date
    status: str
    room: RoomRef | None = None


class StudentSummary(BaseModel):
    total: int
    active: int
    inactive: int
    left: int
    allocated: int
    unallocated: int
