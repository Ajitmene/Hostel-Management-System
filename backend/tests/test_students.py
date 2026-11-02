from tests.conftest import make_room, make_student, student_payload


def test_student_crud_and_validation(client, admin_h):
    r = client.post("/api/v1/students", headers=admin_h, json=student_payload(1))
    assert r.status_code == 201
    sid = r.json()["id"]
    assert client.get(f"/api/v1/students/{sid}", headers=admin_h).json()["full_name"] == "New Student 1"

    upd = student_payload(1, full_name="Renamed Student")
    assert client.put(f"/api/v1/students/{sid}", headers=admin_h, json=upd).json()["full_name"] == "Renamed Student"

    bad = client.post("/api/v1/students", headers=admin_h, json=student_payload(2, phone="abc", email="not-an-email"))
    assert bad.status_code == 422
    fields = {d["field"] for d in bad.json()["error"]["details"]}
    assert {"phone", "email"} <= fields


def test_duplicate_enrollment_and_email_rejected(client, admin_h):
    client.post("/api/v1/students", headers=admin_h, json=student_payload(1))
    r = client.post("/api/v1/students", headers=admin_h, json=student_payload(1))
    assert r.status_code == 409
    assert {d["field"] for d in r.json()["error"]["details"]} == {"enrollment_no", "email"}


def test_search_filter_and_pagination(client, admin_h):
    for i in range(1, 8):
        make_student(i, full_name=f"Person {i}" if i != 3 else "Zara Special")
    r = client.get("/api/v1/students?page_size=3&page=2", headers=admin_h).json()
    assert r["total"] == 7 and r["pages"] == 3 and len(r["items"]) == 3 and r["page"] == 2
    assert client.get("/api/v1/students?q=zara", headers=admin_h).json()["total"] == 1
    assert client.get("/api/v1/students?q=ENR-005", headers=admin_h).json()["total"] == 1
    assert client.get("/api/v1/students?ordering=-name", headers=admin_h).json()["items"][0]["full_name"] == "Zara Special"
    assert client.get("/api/v1/students?ordering=hack", headers=admin_h).status_code == 400
    assert client.get("/api/v1/students?page_size=1000", headers=admin_h).status_code == 422


def test_deactivating_student_ends_allocation_but_keeps_history(client, admin_h):
    student, room = make_student(1), make_room("101")
    assert client.post("/api/v1/rooms/allocations", headers=admin_h, json={"student_id": student.id, "room_id": room.id}).status_code == 201
    r = client.patch(f"/api/v1/students/{student.id}/status", headers=admin_h, json={"status": "inactive"})
    assert r.status_code == 200 and r.json()["room"] is None
    history = client.get(f"/api/v1/rooms/allocations?active_only=false&student_id={student.id}", headers=admin_h).json()
    assert history["total"] == 1 and history["items"][0]["is_active"] is False and history["items"][0]["end_date"]
    assert client.get(f"/api/v1/rooms/{room.id}", headers=admin_h).json()["occupancy"] == 0


def test_filter_students_by_room(client, admin_h):
    s1, s2, room = make_student(1), make_student(2), make_room("101")
    client.post("/api/v1/rooms/allocations", headers=admin_h, json={"student_id": s1.id, "room_id": room.id})
    r = client.get(f"/api/v1/students?room_id={room.id}", headers=admin_h).json()
    assert [s["id"] for s in r["items"]] == [s1.id] and r["items"][0]["room"]["room_number"] == "101"
