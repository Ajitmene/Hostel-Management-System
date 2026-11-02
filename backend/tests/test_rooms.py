import os
from threading import Thread

import pytest

from rooms.models import RoomAllocation
from tests.conftest import make_room, make_student


def alloc(client, h, student, room):
    return client.post("/api/v1/rooms/allocations", headers=h, json={"student_id": student.id, "room_id": room.id})


def test_allocation_and_capacity_validation(client, admin_h):
    room = make_room("101", capacity=2)
    s1, s2, s3 = make_student(1), make_student(2), make_student(3)
    assert alloc(client, admin_h, s1, room).status_code == 201
    assert alloc(client, admin_h, s2, room).status_code == 201
    r = alloc(client, admin_h, s3, room)
    assert r.status_code == 409 and r.json()["error"]["code"] == "room_full"
    detail = client.get(f"/api/v1/rooms/{room.id}", headers=admin_h).json()
    assert detail["occupancy"] == 2 and detail["status"] == "full" and len(detail["occupants"]) == 2


def test_student_cannot_have_two_active_rooms(client, admin_h):
    s, r1, r2 = make_student(1), make_room("101"), make_room("102")
    assert alloc(client, admin_h, s, r1).status_code == 201
    r = alloc(client, admin_h, s, r2)
    assert r.status_code == 409 and r.json()["error"]["code"] == "already_allocated"


def test_database_blocks_second_active_allocation_even_if_code_is_bypassed():
    import pytest
    from django.db import IntegrityError, transaction
    s, r1, r2 = make_student(1), make_room("101"), make_room("102")
    RoomAllocation.objects.create(student=s, room=r1, start_date="2026-07-01")
    with pytest.raises(IntegrityError), transaction.atomic():
        RoomAllocation.objects.create(student=s, room=r2, start_date="2026-07-02")


def test_inactive_student_and_closed_room_rejected(client, admin_h):
    s = make_student(1, status="inactive")
    assert alloc(client, admin_h, s, make_room("101")).json()["error"]["code"] == "student_not_active"
    s2 = make_student(2)
    assert alloc(client, admin_h, s2, make_room("102", is_active=False)).json()["error"]["code"] == "room_closed"


def test_transfer(client, admin_h):
    s, r1, r2 = make_student(1), make_room("101"), make_room("102", capacity=1)
    a = alloc(client, admin_h, s, r1).json()
    t = client.post(f"/api/v1/rooms/allocations/{a['id']}/transfer", headers=admin_h, json={"new_room_id": r2.id})
    assert t.status_code == 201 and t.json()["room_id"] == r2.id
    assert client.get(f"/api/v1/rooms/{r1.id}", headers=admin_h).json()["occupancy"] == 0
    assert client.get(f"/api/v1/rooms/{r2.id}", headers=admin_h).json()["occupancy"] == 1
    # ended allocation cannot be transferred again; same room rejected
    assert client.post(f"/api/v1/rooms/allocations/{a['id']}/transfer", headers=admin_h, json={"new_room_id": r1.id}).status_code == 409
    new_id = t.json()["id"]
    assert client.post(f"/api/v1/rooms/allocations/{new_id}/transfer", headers=admin_h, json={"new_room_id": r2.id}).status_code == 400


def test_transfer_into_full_room_fails_and_changes_nothing(client, admin_h):
    s1, s2, r1, r2 = make_student(1), make_student(2), make_room("101"), make_room("102", capacity=1)
    a1 = alloc(client, admin_h, s1, r1).json()
    alloc(client, admin_h, s2, r2)
    r = client.post(f"/api/v1/rooms/allocations/{a1['id']}/transfer", headers=admin_h, json={"new_room_id": r2.id})
    assert r.status_code == 409
    assert RoomAllocation.objects.get(pk=a1["id"]).is_active is True


def test_cannot_shrink_capacity_below_occupancy(client, admin_h):
    s, room = make_student(1), make_room("101", capacity=2)
    alloc(client, admin_h, s, room)
    body = {"room_number": "101", "room_type": "single", "block": "A", "floor": 1, "capacity": 1, "monthly_rate": "4000.00", "is_active": True}
    assert client.put(f"/api/v1/rooms/{room.id}", headers=admin_h, json=body).status_code == 200
    s2 = make_student(2)
    room2 = make_room("102", capacity=2)
    alloc(client, admin_h, s2, room2)
    alloc(client, admin_h, make_student(3), room2)
    body["room_number"] = "102"
    assert client.put(f"/api/v1/rooms/{room2.id}", headers=admin_h, json=body).json()["error"]["code"] == "capacity_below_occupancy"


def test_room_crud_and_listing(client, admin_h):
    body = {"room_number": "201", "room_type": "triple", "block": "B", "floor": 2, "capacity": 3, "monthly_rate": "3500.00"}
    assert client.post("/api/v1/rooms", headers=admin_h, json=body).status_code == 201
    assert client.post("/api/v1/rooms", headers=admin_h, json=body).status_code == 409
    assert client.post("/api/v1/rooms", headers=admin_h, json={**body, "room_number": "202", "capacity": 0}).status_code == 422
    assert client.get("/api/v1/rooms?block=B", headers=admin_h).json()["total"] == 1
    avail = client.get("/api/v1/rooms/available", headers=admin_h).json()
    assert len(avail) == 1 and avail[0]["available_beds"] == 3


@pytest.mark.skipif(
    os.environ.get("DB_ENGINE", "mysql") == "sqlite",
    reason="Needs row-level locking (MySQL). SQLite serializes writers and cannot exercise this.",
)
def test_concurrent_allocations_cannot_exceed_capacity(client, admin_h):
    """Capacity 1, five simultaneous requests: exactly one may succeed."""
    room = make_room("301", capacity=1)
    students = [make_student(i) for i in range(1, 6)]
    codes = []

    def go(student):
        codes.append(alloc(client, admin_h, student, room).status_code)

    threads = [Thread(target=go, args=(s,)) for s in students]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert codes.count(201) == 1
    assert RoomAllocation.objects.filter(room=room, is_active=True).count() == 1
