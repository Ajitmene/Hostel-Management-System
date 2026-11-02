from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

AttStatus = Literal["present", "absent", "leave"]


class AttendanceEntry(BaseModel):
    student_id: int = Field(gt=0)
    status: AttStatus
    remarks: str = Field(default="", max_length=255)


class AttendanceBulkCreate(BaseModel):
    date: date
    records: list[AttendanceEntry] = Field(min_length=1, max_length=500)

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "date": "2026-11-02", "records": [{"student_id": 1, "status": "present"}, {"student_id": 2, "status": "leave", "remarks": "Family event"}],
    }]})


class AttendanceCorrection(BaseModel):
    status: AttStatus
    remarks: str = Field(default="", max_length=255)
    reason: str = Field(min_length=3, max_length=255, description="Why the record is being corrected (audited).")


class AttendanceOut(BaseModel):
    id: int
    student_id: int
    student_name: str
    enrollment_no: str
    date: date
    status: str
    remarks: str
    recorded_by: str


class RosterItem(BaseModel):
    student_id: int
    enrollment_no: str
    full_name: str
    room: str | None
    attendance_id: int | None
    status: str | None
    remarks: str


class SummaryRow(BaseModel):
    student_id: int
    enrollment_no: str
    full_name: str
    present: int
    absent: int
    leave: int
    marked_days: int
    percentage: float | None


class AttendanceSummary(BaseModel):
    date_from: date
    date_to: date
    totals: dict[str, int]
    overall_percentage: float | None
    students: list[SummaryRow]
