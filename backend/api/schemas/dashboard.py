from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from api.schemas.common import MoneyOut


class AttendanceToday(BaseModel):
    present: int
    absent: int
    leave: int
    unmarked: int


class Activity(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    user: str | None
    created_at: datetime


class QuickLink(BaseModel):
    label: str
    path: str


class DashboardSummary(BaseModel):
    role: str
    # Present for everyone who may see them; null when the caller lacks permission.
    total_students: int | None = None
    attendance_today: AttendanceToday | None = None
    # Admin-only figures
    total_employees: int | None = None
    total_rooms: int | None = None
    occupied_rooms: int | None = None
    available_rooms: int | None = None
    total_beds: int | None = None
    occupied_beds: int | None = None
    pending_fees: MoneyOut | None = None
    overdue_fee_count: int | None = None
    recent_activities: list[Activity] | None = None
    # Employee-only
    tasks: list[str] | None = None
    quick_links: list[QuickLink] | None = None
