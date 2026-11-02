"""Shared fixtures. Tests run against a throwaway test database that Django
creates and destroys (never your real hostel_db).

On a machine without MySQL, run them on SQLite:   set DB_ENGINE=sqlite
"""
import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-that-is-long-enough-1234567890")
os.environ.setdefault("DJANGO_SECRET_KEY", "test-django-secret-key-1234567890-abcdefghij")

import django  # noqa: E402

django.setup()

from accounts.models import EmployeeProfile, Role, User  # noqa: E402
from api.core.config import get_settings  # noqa: E402
from api.main import app  # noqa: E402
from rooms.models import Room  # noqa: E402
from students.models import Student  # noqa: E402

ADMIN_PASSWORD = "Admin-passphrase-1"
EMPLOYEE_PASSWORD = "Employee-passphrase-1"


@pytest.fixture(autouse=True)
def _enable_db(transactional_db):
    """Every API test needs a real, committed database because FastAPI runs the
    ORM in other threads."""


@pytest.fixture
def client():
    get_settings.cache_clear()
    with TestClient(app, base_url="http://localhost") as c:
        yield c


@pytest.fixture
def admin_user():
    return User.objects.create_superuser("admin@example.com", ADMIN_PASSWORD, first_name="Ada", last_name="Admin")


@pytest.fixture
def employee_user():
    user = User.objects.create_user("emp@example.com", EMPLOYEE_PASSWORD, first_name="Eli", last_name="Employee")
    EmployeeProfile.objects.create(
        user=user, employee_id="EMP-001", phone="+919800000001", designation="Warden",
        department="Ops", joining_date=date(2026, 1, 1),
        permissions=["students.view", "rooms.view", "fees.view", "attendance.view", "attendance.record"],
    )
    return user


def _bearer(client, email, password):
    r = client.post("/api/v1/auth/token", data={"username": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture
def admin_h(client, admin_user):
    return _bearer(client, "admin@example.com", ADMIN_PASSWORD)


@pytest.fixture
def emp_h(client, employee_user):
    return _bearer(client, "emp@example.com", EMPLOYEE_PASSWORD)


def make_student(n=1, **kw):
    data = dict(
        enrollment_no=f"ENR-{n:03d}", full_name=f"Student {n}", email=f"s{n}@example.com", phone="+919800000100",
        gender="female", address="Pune", guardian_name="Guardian", guardian_phone="+919800000200",
        admission_date=date(2026, 7, 1),
    )
    data.update(kw)
    return Student.objects.create(**data)


def make_room(number="101", capacity=2, **kw):
    data = dict(room_number=number, room_type="double", block="A", floor=1, capacity=capacity, monthly_rate="4500.00")
    data.update(kw)
    return Room.objects.create(**data)


def student_payload(n=1, **kw):
    data = {
        "enrollment_no": f"NEW-{n:03d}", "full_name": f"New Student {n}", "email": f"new{n}@example.com",
        "phone": "+919800000300", "gender": "male", "address": "Pune", "guardian_name": "Parent",
        "guardian_phone": "+919800000400", "admission_date": "2026-07-01",
    }
    data.update(kw)
    return data
