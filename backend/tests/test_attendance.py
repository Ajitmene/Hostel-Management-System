from datetime import date, timedelta

from attendance.models import Attendance
from tests.conftest import make_student

TODAY = date.today()


def mark(client, h, day, entries):
    return client.post("/api/v1/attendance", headers=h, json={"date": str(day), "records": entries})


def test_employee_can_record_and_view_attendance(client, emp_h):
    s1, s2 = make_student(1), make_student(2)
    r = mark(client, emp_h, TODAY, [{"student_id": s1.id, "status": "present"}, {"student_id": s2.id, "status": "leave", "remarks": "Home"}])
    assert r.status_code == 201 and len(r.json()) == 2
    assert r.json()[0]["recorded_by"] == "emp@example.com"
    hist = client.get(f"/api/v1/attendance?date={TODAY}", headers=emp_h).json()
    assert hist["total"] == 2
    assert client.get(f"/api/v1/attendance?status=leave", headers=emp_h).json()["total"] == 1


def test_duplicate_attendance_is_rejected_and_nothing_is_saved(client, admin_h):
    s1, s2 = make_student(1), make_student(2)
    assert mark(client, admin_h, TODAY, [{"student_id": s1.id, "status": "present"}]).status_code == 201
    r = mark(client, admin_h, TODAY, [{"student_id": s1.id, "status": "absent"}, {"student_id": s2.id, "status": "present"}])
    assert r.status_code == 409 and r.json()["error"]["code"] == "attendance_exists"
    assert r.json()["error"]["details"]["student_ids"] == [s1.id]
    assert Attendance.objects.count() == 1  # all-or-nothing: s2 was NOT saved


def test_database_unique_constraint_backs_up_the_check():
    import pytest
    from django.db import IntegrityError, transaction
    from accounts.models import User
    s = make_student(1)
    u = User.objects.create_user("x@example.com", "Some-long-pass-1")
    Attendance.objects.create(student=s, date=TODAY, status="present", recorded_by=u)
    with pytest.raises(IntegrityError), transaction.atomic():
        Attendance.objects.create(student=s, date=TODAY, status="absent", recorded_by=u)


def test_invalid_inputs(client, emp_h):
    s = make_student(1)
    assert mark(client, emp_h, TODAY + timedelta(days=1), [{"student_id": s.id, "status": "present"}]).status_code == 400
    assert mark(client, emp_h, TODAY, [{"student_id": s.id, "status": "sleeping"}]).status_code == 422
    assert mark(client, emp_h, TODAY, [{"student_id": 9999, "status": "present"}]).status_code == 404
    assert mark(client, emp_h, TODAY, [{"student_id": s.id, "status": "present"}, {"student_id": s.id, "status": "absent"}]).status_code == 422
    assert mark(client, emp_h, TODAY, []).status_code == 422
    gone = make_student(2, status="left")
    assert mark(client, emp_h, TODAY, [{"student_id": gone.id, "status": "present"}]).status_code == 409


def test_employee_without_record_permission_cannot_record(client, emp_h, employee_user):
    p = employee_user.employee_profile
    p.permissions = ["attendance.view"]
    p.save()
    s = make_student(1)
    assert mark(client, emp_h, TODAY, [{"student_id": s.id, "status": "present"}]).status_code == 403
    assert client.get("/api/v1/attendance", headers=emp_h).status_code == 200


def test_only_admin_can_correct_and_reason_is_audited(client, admin_h, emp_h):
    s = make_student(1)
    rec = mark(client, admin_h, TODAY, [{"student_id": s.id, "status": "absent"}]).json()[0]
    body = {"status": "present", "remarks": "Marked by mistake", "reason": "Data entry error"}
    assert client.put(f"/api/v1/attendance/{rec['id']}", headers=emp_h, json=body).status_code == 403
    r = client.put(f"/api/v1/attendance/{rec['id']}", headers=admin_h, json=body)
    assert r.status_code == 200 and r.json()["status"] == "present"
    from accounts.models import AuditLog
    log = AuditLog.objects.get(action="attendance.correct")
    assert log.details["before"]["status"] == "absent" and log.details["reason"] == "Data entry error"
    assert client.put(f"/api/v1/attendance/{rec['id']}", headers=admin_h, json={**body, "reason": ""}).status_code == 422


def test_summary_percentages_and_roster(client, admin_h):
    s1, s2 = make_student(1), make_student(2)
    for offset, status in enumerate(["present", "present", "absent", "leave"]):
        mark(client, admin_h, TODAY - timedelta(days=offset), [{"student_id": s1.id, "status": status}])
    mark(client, admin_h, TODAY, [{"student_id": s2.id, "status": "present"}])
    data = client.get(f"/api/v1/attendance/summary?date_from={TODAY - timedelta(days=10)}&date_to={TODAY}", headers=admin_h).json()
    rows = {r["student_id"]: r for r in data["students"]}
    assert rows[s1.id]["percentage"] == 50.0 and rows[s1.id]["marked_days"] == 4
    assert rows[s2.id]["percentage"] == 100.0
    assert data["totals"] == {"present": 3, "absent": 1, "leave": 1}
    assert client.get(f"/api/v1/attendance/summary?date_from={TODAY}&date_to={TODAY - timedelta(days=1)}", headers=admin_h).status_code == 422
    roster = client.get(f"/api/v1/attendance/roster?date={TODAY}", headers=admin_h).json()
    assert {r["student_id"]: r["status"] for r in roster} == {s1.id: "present", s2.id: "present"}
