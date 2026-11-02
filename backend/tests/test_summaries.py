from datetime import date, timedelta

from fees.models import FeeStructure, StudentFee
from tests.conftest import make_room, make_student

TODAY = date.today()


def test_student_summary_counts(client, admin_h, emp_h):
    s1, s2 = make_student(1), make_student(2)
    make_student(3, status="inactive")
    make_student(4, status="left")
    room = make_room("101")
    client.post("/api/v1/rooms/allocations", headers=admin_h, json={"student_id": s1.id, "room_id": room.id})
    data = client.get("/api/v1/students/summary", headers=emp_h).json()
    assert data == {"total": 4, "active": 2, "inactive": 1, "left": 1, "allocated": 1, "unallocated": 1}


def test_room_summary_beds(client, admin_h, emp_h):
    a, b = make_room("101", capacity=2), make_room("102", capacity=1)
    make_room("103", capacity=4, is_active=False)
    client.post("/api/v1/rooms/allocations", headers=admin_h, json={"student_id": make_student(1).id, "room_id": b.id})
    client.post("/api/v1/rooms/allocations", headers=admin_h, json={"student_id": make_student(2).id, "room_id": a.id})
    d = client.get("/api/v1/rooms/summary", headers=emp_h).json()
    assert d["total_rooms"] == 3 and d["open_rooms"] == 2 and d["closed_rooms"] == 1
    assert d["full_rooms"] == 1 and d["available_rooms"] == 1
    assert (d["total_beds"], d["occupied_beds"], d["free_beds"], d["occupancy_percent"]) == (3, 2, 1, 66.7)


def test_fee_summary_money_and_buckets(client, admin_h, emp_h):
    s = make_student(1)
    fs = FeeStructure.objects.create(name="Rent", amount="1000.00", frequency="monthly")
    pending = StudentFee.objects.create(student=s, structure=fs, amount_due="1000.00", due_date=TODAY + timedelta(days=5))
    overdue = StudentFee.objects.create(student=s, structure=fs, amount_due="800.00", due_date=TODAY - timedelta(days=9))
    paid = StudentFee.objects.create(student=s, structure=fs, amount_due="500.00", due_date=TODAY - timedelta(days=40))
    for fee, amount, key in [(paid, "500.00", "sum-key-0001"), (overdue, "300.00", "sum-key-0002")]:
        r = client.post("/api/v1/fees/payments", headers=admin_h, json={
            "fee_id": fee.id, "amount": amount, "payment_date": str(TODAY), "method": "cash", "idempotency_key": key})
        assert r.status_code == 201
    d = client.get("/api/v1/fees/summary", headers=emp_h).json()
    assert d["total_fees"] == 3 and d["total_due"] == "2300.00" and d["total_collected"] == "800.00"
    assert d["outstanding"] == "1500.00" and d["overdue_count"] == 1 and d["overdue_amount"] == "500.00"
    assert (d["pending_count"], d["partial_count"], d["paid_count"]) == (1, 0, 1)
    assert d["collected_this_month"] == "800.00" and d["payments_this_month"] == 2 and d["payments_total"] == 2


def test_summaries_require_permission(client, emp_h, employee_user):
    p = employee_user.employee_profile
    p.permissions = ["attendance.view"]
    p.save()
    for path in ("/api/v1/students/summary", "/api/v1/rooms/summary", "/api/v1/fees/summary"):
        assert client.get(path, headers=emp_h).status_code == 403
    assert client.get("/api/v1/students/summary").status_code == 401
