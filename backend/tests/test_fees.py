import os
from datetime import date, timedelta
from decimal import Decimal
from threading import Thread

import pytest

from fees.models import FeeStructure, Payment, StudentFee
from tests.conftest import make_student

TODAY = date.today()


def setup_fee(client, h, amount="1000.00", due=None):
    student = make_student(1)
    structure = FeeStructure.objects.create(name="Monthly fee", amount=amount, frequency="monthly")
    r = client.post("/api/v1/fees", headers=h, json={
        "student_id": student.id, "structure_id": structure.id, "due_date": str(due or TODAY + timedelta(days=10)),
    })
    assert r.status_code == 201, r.text
    return student, r.json()


def pay(client, h, fee_id, amount, key, **kw):
    body = {"fee_id": fee_id, "amount": amount, "payment_date": str(TODAY), "method": "cash", "idempotency_key": key}
    body.update(kw)
    return client.post("/api/v1/fees/payments", headers=h, json=body)


def test_fee_defaults_to_structure_amount_and_starts_pending(client, admin_h):
    _, fee = setup_fee(client, admin_h)
    assert fee["amount_due"] == "1000.00" and fee["balance"] == "1000.00" and fee["status"] == "pending"


def test_duplicate_fee_for_same_period_rejected(client, admin_h):
    student, fee = setup_fee(client, admin_h)
    r = client.post("/api/v1/fees", headers=admin_h, json={
        "student_id": student.id, "structure_id": fee["structure_id"], "due_date": fee["due_date"]})
    assert r.status_code == 409


def test_partial_then_full_payment_updates_status_and_balance(client, admin_h):
    _, fee = setup_fee(client, admin_h)
    r = pay(client, admin_h, fee["id"], "400.00", "key-partial-1")
    assert r.status_code == 201 and r.json()["receipt_number"].startswith("RCP-")
    assert client.get(f"/api/v1/fees/{fee['id']}", headers=admin_h).json()["status"] == "partial"
    assert client.get(f"/api/v1/fees/{fee['id']}", headers=admin_h).json()["balance"] == "600.00"
    assert pay(client, admin_h, fee["id"], "600.00", "key-partial-2").status_code == 201
    done = client.get(f"/api/v1/fees/{fee['id']}", headers=admin_h).json()
    assert done["status"] == "paid" and Decimal(done["balance"]) == 0


def test_payment_validation(client, admin_h):
    _, fee = setup_fee(client, admin_h)
    assert pay(client, admin_h, fee["id"], "0", "key-zero-001").status_code == 422
    assert pay(client, admin_h, fee["id"], "-5", "key-neg-001").status_code == 422
    assert pay(client, admin_h, fee["id"], "10.555", "key-dec-001").status_code == 422
    over = pay(client, admin_h, fee["id"], "1000.01", "key-over-001")
    assert over.status_code == 409 and over.json()["error"]["code"] == "overpayment"
    future = pay(client, admin_h, fee["id"], "10.00", "key-future-1", payment_date=str(TODAY + timedelta(days=2)))
    assert future.status_code == 400
    assert pay(client, admin_h, 9999, "10.00", "key-missing-1").status_code == 404
    assert Payment.objects.count() == 0


def test_resubmitting_same_idempotency_key_does_not_double_charge(client, admin_h):
    _, fee = setup_fee(client, admin_h)
    first = pay(client, admin_h, fee["id"], "300.00", "key-dup-12345")
    again = pay(client, admin_h, fee["id"], "300.00", "key-dup-12345")
    assert first.status_code == 201 and again.status_code == 200
    assert first.json()["id"] == again.json()["id"]
    assert Payment.objects.count() == 1
    clash = pay(client, admin_h, fee["id"], "301.00", "key-dup-12345")
    assert clash.status_code == 409 and clash.json()["error"]["code"] == "idempotency_conflict"


def test_duplicate_transaction_reference_rejected(client, admin_h):
    _, fee = setup_fee(client, admin_h)
    assert pay(client, admin_h, fee["id"], "100.00", "key-ref-0001", method="upi", transaction_reference="UPI-1").status_code == 201
    r = pay(client, admin_h, fee["id"], "100.00", "key-ref-0002", method="upi", transaction_reference="UPI-1")
    assert r.status_code == 409 and r.json()["error"]["code"] == "duplicate_reference"


def test_paid_fee_rejects_more_payments(client, admin_h):
    _, fee = setup_fee(client, admin_h)
    pay(client, admin_h, fee["id"], "1000.00", "key-full-0001")
    r = pay(client, admin_h, fee["id"], "1.00", "key-full-0002")
    assert r.status_code == 409 and r.json()["error"]["code"] == "fee_already_paid"


def test_pending_and_overdue_filters(client, admin_h):
    student, fee = setup_fee(client, admin_h)  # due in 10 days
    structure = FeeStructure.objects.create(name="Late fee", amount="500.00", frequency="one_time")
    old = StudentFee.objects.create(student=student, structure=structure, amount_due="500.00", due_date=TODAY - timedelta(days=5))
    paid = StudentFee.objects.create(student=student, structure=structure, amount_due="500.00", due_date=TODAY - timedelta(days=40))
    pay(client, admin_h, paid.id, "500.00", "key-paid-0001", payment_date=str(TODAY))
    pending = client.get("/api/v1/fees/pending", headers=admin_h).json()
    assert {f["id"] for f in pending["items"]} == {fee["id"], old.id}
    overdue = client.get("/api/v1/fees/pending?overdue_only=true", headers=admin_h).json()
    assert [f["id"] for f in overdue["items"]] == [old.id] and overdue["items"][0]["status"] == "overdue"
    assert client.get("/api/v1/fees?status=paid", headers=admin_h).json()["total"] == 1
    assert client.get("/api/v1/fees?status=pending", headers=admin_h).json()["total"] == 1


def test_receipt_and_history(client, admin_h, emp_h):
    _, fee = setup_fee(client, admin_h)
    p1 = pay(client, admin_h, fee["id"], "250.00", "key-rcpt-0001").json()
    p2 = pay(client, admin_h, fee["id"], "250.00", "key-rcpt-0002").json()
    receipt = client.get(f"/api/v1/fees/payments/{p2['id']}/receipt", headers=emp_h).json()
    assert receipt["total_paid"] == "500.00" and receipt["balance_after"] == "500.00" and receipt["structure_name"] == "Monthly fee"
    history = client.get(f"/api/v1/fees/payments?fee_id={fee['id']}", headers=emp_h).json()
    assert history["total"] == 2
    assert client.get("/api/v1/fees/payments/9999/receipt", headers=emp_h).status_code == 404


@pytest.mark.skipif(os.environ.get("DB_ENGINE", "mysql") == "sqlite", reason="Needs row-level locking (MySQL).")
def test_concurrent_payments_cannot_overpay(client, admin_h):
    _, fee = setup_fee(client, admin_h, amount="100.00")
    codes = []
    threads = [Thread(target=lambda i=i: codes.append(pay(client, admin_h, fee["id"], "100.00", f"key-race-{i:04d}").status_code)) for i in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert codes.count(201) == 1
    assert Payment.objects.filter(fee_id=fee["id"]).count() == 1
