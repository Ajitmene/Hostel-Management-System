from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from api.schemas.common import Name, Phone


class EmployeeBase(BaseModel):
    first_name: Name
    last_name: Name
    email: EmailStr
    employee_id: str = Field(min_length=1, max_length=20, pattern=r"^[A-Za-z0-9\-_/]+$")
    phone: Phone
    designation: str = Field(min_length=1, max_length=100)
    department: str = Field(min_length=1, max_length=100)
    joining_date: date
    permissions: list[str] = Field(default_factory=list, description="Permission codes, e.g. students.view")


class EmployeeCreate(EmployeeBase):
    password: str = Field(min_length=10, max_length=256)

    model_config = ConfigDict(json_schema_extra={"examples": [{
        "first_name": "Meera", "last_name": "Kulkarni", "email": "meera@example.com", "employee_id": "EMP-007",
        "phone": "+919800000010", "designation": "Warden", "department": "Hostel Operations",
        "joining_date": "2026-08-01", "permissions": ["students.view", "rooms.view", "attendance.view", "attendance.record"],
        "password": "a-strong-passphrase",
    }]})


class EmployeeUpdate(EmployeeBase):
    pass


class EmployeeStatus(BaseModel):
    is_active: bool


class PasswordReset(BaseModel):
    new_password: str = Field(min_length=10, max_length=256)


class EmployeeOut(BaseModel):
    id: int
    user_id: int
    first_name: str
    last_name: str
    email: str
    employee_id: str
    phone: str
    designation: str
    department: str
    joining_date: date
    permissions: list[str]
    is_active: bool
    role: str
