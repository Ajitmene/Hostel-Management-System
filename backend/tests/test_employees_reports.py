from datetime import date, timedelta

from fees.models import FeeStructure, StudentFee
from tests.conftest import make_room, make_student

TODAY = date.today()


def emp_body(**kw):
    body = {
        "first_name": "Meera", "last_name": "Kulkarni", "email": "meera@example.com", "employee_id": "EMP-007",
        "phone": "+919800000010", "designation": "Warden", "department": "Hostel Operations",
        "joining_date": "2026-08-01", "permissions": ["students.view", "attendance.record"], "password": "A-strong-pass-123",
    }
    body.update(kw)
    return body


def test_employee_lifecycle(client, admin_h):
    r = client.post("/api/v1/employees", headers=admin_h, json=emp_body())
    assert r.status_code == 201
    emp = r.json()
    assert "password" not in emp and emp["permissions"] == ["students.view", "attendance.record"]
    # the new employee can log in and only has the granted permissions
    token = client.post("/api/v1/auth/token", data={"username": "meera@example.com", "password": "A-strong-pass-123"}).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/v1/students", headers=h).status_code == 200
    assert client.get("/api/v1/rooms", headers=h).status_code == 403

    upd = emp_body(designation="Senior Warden", permissions=["students.view", "rooms.view"])
    upd.pop("password")
    assert client.put(f"/api/v1/employees/{emp['id']}", headers=admin_h, json=upd).json()["designation"] == "Senior Warden"
    assert client.get("/api/v1/rooms", headers=h).status_code == 200  # permission change applies immediately

    off = client.patch(f"/api/v1/employees/{emp['id']}/status", headers=admin_h, json={"is_active": False})
    assert off.status_code == 200 and off.json()["is_active"] is False
    assert client.get("/api/v1/students", headers=h).status_code == 401  # signed out at once
    assert client.post("/api/v1/auth/token", data={"username": "meera@example.com", "password": "A-strong-pass-123"}).status_code == 401
    client.patch(f"/api/v1/employees/{emp['id']}/status", headers=admin_h, json={"is_active": True})
    assert client.post("/api/v1/auth/token", data={"username": "meera@example.com", "password": "A-strong-pass-123"}).status_code == 200


def test_employee_validation(client, admin_h):
    assert client.post("/api/v1/employees", headers=admin_h, json=emp_body()).status_code == 201
    assert client.post("/api/v1/employees", headers=admin_h, json=emp_body()).status_code == 409
    weak = client.post("/api/v1/employees", headers=admin_h, json=emp_body(email="w@example.com", employee_id="E2", password="password123"))
    assert weak.status_code == 422 and weak.json()["error"]["code"] == "weak_password"
    bad = client.post("/api/v1/employees", headers=admin_h, json=emp_body(email="p@example.com", employee_id="E3", permissions=["root.access"]))
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_permissions"


def test_reset_password_signs_employee_out(client, admin_h):
    emp = client.post("/api/v1/employees", headers=admin_h, json=emp_body()).json()
    token = client.post("/api/v1/auth/token", data={"username": "meera@example.com", "password": "A-strong-pass-123"}).json()["access_token"]
    assert client.post(f"/api/v1/employees/{emp['id']}/reset-password", headers=admin_h, json={"new_password": "Brand-new-pass-77"}).status_code == 200
    assert client.get("/api/v1/students", headers={"Authorization": f"Bearer {token}"}).status_code == 401
    assert client.post("/api/v1/auth/token", data={"username": "meera@example.com", "password": "Brand-new-pass-77"}).status_code == 200


def test_audit_log_records_admin_actions_without_secrets(client, admin_h):
    client.post("/api/v1/employees", headers=admin_h, json=emp_body())
    from accounts.models import AuditLog
    log = AuditLog.objects.get(action="employee.create")
    assert "A-strong-pass-123" not in str(log.details) and log.user.email == "admin@example.com"
    acts = client.get("/api/v1/dashboard/summary", headers=admin_h).json()["recent_activities"]
    assert any(a["action"] == "employee.create" for a in acts)


def test_reports_json_csv_and_filters(client, admin_h):
    s = make_student(1, admission_date=TODAY)
    room = make_room("101", capacity=2)
    client.post("/api/v1/rooms/allocations", headers=admin_h, json={"student_id": s.id, "room_id": room.id})
    fs = FeeStructure.objects.create(name="Monthly", amount="1000.00", frequency="monthly")
    fee = StudentFee.objects.create(student=s, structure=fs, amount_due="1000.00", due_date=TODAY - timedelta(days=3))
    client.post("/api/v1/fees/payments", headers=admin_h, json={
        "fee_id": fee.id, "amount": "400.00", "payment_date": str(TODAY), "method": "cash", "idempotency_key": "report-key-001"})

    occ = client.get("/api/v1/reports/occupancy", headers=admin_h).json()
    assert occ["summary"]["occupied_beds"] == 1 and occ["summary"]["occupancy_percent"] == 50.0
    assert client.get("/api/v1/reports/occupancy?available_only=true", headers=admin_h).json()["title"] == "Available rooms"
    fees = client.get("/api/v1/reports/fees", headers=admin_h).json()
    assert fees["summary"] == {"payments": 1, "total_collected": "400.00"}
    out = client.get("/api/v1/reports/outstanding", headers=admin_h).json()
    assert out["summary"]["total_outstanding"] == "600.00" and out["rows"][0][-1] == "overdue"
    assert client.get("/api/v1/reports/registrations", headers=admin_h).json()["summary"]["registrations"] == 1
    assert client.get(f"/api/v1/reports/fees?date_from={TODAY + timedelta(days=1)}&date_to={TODAY}", headers=admin_h).status_code == 422

    csv_r = client.get("/api/v1/reports/fees?format=csv", headers=admin_h)
    assert csv_r.headers["content-type"].startswith("text/csv") and "attachment" in csv_r.headers["content-disposition"]
    assert csv_r.text.splitlines()[0].startswith("Receipt,Date")


def test_csv_neutralises_formula_injection():
    from api.services.reports import to_csv
    out = to_csv({"columns": ["a"], "rows": [["=HYPERLINK(\"http://evil\")"], ["+1"], ["safe"]]})
    assert "'=HYPERLINK" in out and "'+1" in out and "\nsafe" in out


def test_dashboard_numbers_come_from_data(client, admin_h):
    s1, s2 = make_student(1), make_student(2)
    room = make_room("101", capacity=2)
    make_room("102", capacity=1)
    client.post("/api/v1/rooms/allocations", headers=admin_h, json={"student_id": s1.id, "room_id": room.id})
    d = client.get("/api/v1/dashboard/summary", headers=admin_h).json()
    assert d["total_students"] == 2 and d["total_rooms"] == 2 and d["occupied_rooms"] == 1
    assert d["available_rooms"] == 2 and d["total_beds"] == 3 and d["occupied_beds"] == 1
    assert d["attendance_today"]["unmarked"] == 2 and d["total_employees"] == 0
