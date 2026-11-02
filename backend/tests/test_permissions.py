import pytest

from tests.conftest import make_student, student_payload


def test_employee_can_read_students_but_not_write(client, emp_h):
    make_student(1)
    assert client.get("/api/v1/students", headers=emp_h).status_code == 200
    r = client.post("/api/v1/students", headers=emp_h, json=student_payload())
    assert r.status_code == 403 and r.json()["error"]["code"] == "forbidden"
    assert client.put("/api/v1/students/1", headers=emp_h, json=student_payload()).status_code == 403
    assert client.patch("/api/v1/students/1/status", headers=emp_h, json={"status": "inactive"}).status_code == 403


@pytest.mark.parametrize("method,path", [
    ("get", "/api/v1/employees"),
    ("post", "/api/v1/employees"),
    ("get", "/api/v1/reports/occupancy"),
    ("get", "/api/v1/reports/fees"),
    ("post", "/api/v1/rooms"),
    ("post", "/api/v1/rooms/allocations"),
    ("post", "/api/v1/fees"),
    ("post", "/api/v1/fees/payments"),
    ("post", "/api/v1/fees/structures"),
])
def test_admin_only_endpoints_reject_employees(client, emp_h, method, path):
    r = getattr(client, method)(path, headers=emp_h, **({"json": {}} if method == "post" else {}))
    assert r.status_code == 403, f"{method} {path} -> {r.status_code}"


def test_employee_without_permission_is_blocked(client, emp_h, employee_user):
    profile = employee_user.employee_profile
    profile.permissions = ["students.view"]
    profile.save()
    assert client.get("/api/v1/students", headers=emp_h).status_code == 200
    assert client.get("/api/v1/rooms", headers=emp_h).status_code == 403
    assert client.get("/api/v1/fees", headers=emp_h).status_code == 403
    assert client.get("/api/v1/attendance", headers=emp_h).status_code == 403


def test_employee_cannot_grant_themselves_admin(client, emp_h, employee_user):
    r = client.put(f"/api/v1/employees/{employee_user.employee_profile.id}", headers=emp_h, json={})
    assert r.status_code == 403
    employee_user.refresh_from_db()
    assert employee_user.role == "employee"


def test_client_supplied_role_is_ignored_when_creating_employee(client, admin_h):
    payload = {
        "first_name": "New", "last_name": "Hire", "email": "hire@example.com", "employee_id": "EMP-100",
        "phone": "+919800000500", "designation": "Clerk", "department": "Office", "joining_date": "2026-08-01",
        "permissions": ["students.view"], "password": "Long-enough-pass-1", "role": "admin", "is_staff": True,
    }
    r = client.post("/api/v1/employees", headers=admin_h, json=payload)
    assert r.status_code == 201 and r.json()["role"] == "employee"
    from accounts.models import User
    u = User.objects.get(email="hire@example.com")
    assert u.role == "employee" and not u.is_staff


def test_dashboard_is_role_specific(client, admin_h, emp_h):
    make_student(1)
    admin = client.get("/api/v1/dashboard/summary", headers=admin_h).json()
    emp = client.get("/api/v1/dashboard/summary", headers=emp_h).json()
    assert admin["total_students"] == 1 and admin["pending_fees"] is not None
    assert emp["pending_fees"] is None and emp["total_employees"] is None and emp["quick_links"]
